"""
Razorpay-exclusive payment service for Connecto.

Flow:
  1. Customer approves quote  →  POST /payments/create-order
     → Creates a Razorpay order (real or simulated) + Payment DB row
     → Returns { order_id, amount, currency, key_id, job_id, breakdown }

  2. Frontend renders Razorpay Checkout SDK, user pays.
     Razorpay returns: razorpay_order_id, razorpay_payment_id, razorpay_signature

  3. POST /payments/verify
     → HMAC-SHA256 signature check (production keys) or bypass (test keys)
     → Sets payment status = RELEASED_TO_WORKER
     → Adds worker earnings, creates payout record, closes job

  4. POST /payments/webhook
     → Validates X-Razorpay-Signature header using RAZORPAY_WEBHOOK_SECRET
     → Handles payment.captured event as an idempotent ledger reconciliation

Payout note:
  Net worker cut = total amount - platform_fee - tax
  This is recorded in WorkerPayout and added to WorkerProfile earnings.
"""

import hmac
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import settings
from app.models.job import ServiceJob, TimelineEvent
from app.models.payment import Payment, WorkerPayout
from app.models.user import WorkerProfile


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _is_live_razorpay() -> bool:
    """Return True when real (non-stub) Razorpay credentials are configured."""
    key = settings.RAZORPAY_KEY_ID
    secret = settings.RAZORPAY_KEY_SECRET
    return (
        bool(key)
        and not key.startswith("rzp_test_sample")
        and bool(secret)
        and not secret.startswith("rzp_test_sample")
    )


def _verify_razorpay_signature(order_id: str, payment_id: str, signature: str) -> bool:
    """
    HMAC-SHA256 verification of Razorpay payment callback.
    Message = "<order_id>|<payment_id>"
    """
    msg = f"{order_id}|{payment_id}".encode("utf-8")
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode("utf-8"),
        msg,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _verify_razorpay_webhook_signature(body: bytes, signature: str) -> bool:
    """
    Verify the X-Razorpay-Signature header for server-to-server webhooks.
    Uses RAZORPAY_WEBHOOK_SECRET (separate from key secret).
    """
    expected = hmac.new(
        settings.RAZORPAY_WEBHOOK_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def _build_breakdown(quote) -> Dict[str, Any]:
    return {
        "diagnosticFee": quote.diagnostic_fee,
        "labour": quote.labour,
        "parts": quote.parts,
        "platformFee": quote.platform_fee,
        "tax": quote.tax,
        "total": quote.total,
    }


# ──────────────────────────────────────────────────────────────────────────────
# PaymentService
# ──────────────────────────────────────────────────────────────────────────────

class PaymentService:

    @staticmethod
    async def create_razorpay_order(
        db: AsyncSession,
        job: ServiceJob,
    ) -> Dict[str, Any]:
        """
        Create a Razorpay order for the job's approved quote total.

        - If real Razorpay credentials exist → calls Razorpay API to get an order_id.
        - Otherwise (test / CI / sandbox) → generates a deterministic fake order_id.

        Always persists/updates a Payment row in PENDING state.

        Returns the payload the mobile/web frontend needs to initialise
        Razorpay Checkout JS SDK or React Native SDK.
        """
        if not job.quote:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot initiate payment: no approved quote exists for this job.",
            )

        if not job.quote.is_approved:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot initiate payment: customer has not approved the quote yet.",
            )

        amount_inr = job.quote.total
        amount_paise = int(amount_inr * 100)  # Razorpay expects paise (smallest unit)
        breakdown = _build_breakdown(job.quote)

        # ── Create / fetch Razorpay order ─────────────────────────────────────
        gateway_order_id = f"order_{uuid.uuid4().hex[:14]}"  # stub fallback

        if _is_live_razorpay():
            try:
                import razorpay  # type: ignore[import]
                client = razorpay.Client(
                    auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET)
                )
                rp_order = client.order.create(
                    data={
                        "amount": amount_paise,
                        "currency": "INR",
                        "receipt": job.id,
                        "notes": {
                            "job_id": job.id,
                            "category": job.category_name,
                            "platform": "Connecto",
                        },
                    }
                )
                gateway_order_id = rp_order["id"]
            except Exception as exc:
                # Log but don't crash — fallback to stub order so dev/test still works
                import logging
                logging.getLogger(__name__).warning(
                    "Razorpay order creation failed (falling back to stub): %s", exc
                )

        # ── Persist Payment row ───────────────────────────────────────────────
        stmt = select(Payment).where(Payment.job_id == job.id)
        existing = (await db.execute(stmt)).scalar_one_or_none()

        if existing:
            existing.gateway_order_id = gateway_order_id
            existing.amount = amount_inr
            existing.breakdown = breakdown
            existing.status = "PENDING"
        else:
            payment = Payment(
                job_id=job.id,
                customer_id=job.customer_id,
                worker_id=job.worker_id,
                amount=amount_inr,
                currency="INR",
                status="PENDING",
                method="UPI",          # will be updated at verify time
                gateway="RAZORPAY",
                gateway_order_id=gateway_order_id,
                breakdown=breakdown,
            )
            db.add(payment)

        # Mark job status
        job.status = "PAYMENT_PENDING"
        await db.commit()

        return {
            "order_id": gateway_order_id,
            "amount": amount_inr,
            "amount_paise": amount_paise,
            "currency": "INR",
            "key_id": settings.RAZORPAY_KEY_ID,
            "job_id": job.id,
            "description": f"Connecto — {job.category_name}",
            "breakdown": breakdown,
            # Convenience flags for frontend Checkout config
            "prefill": {},   # caller can merge customer name/email/phone
            "theme": {"color": "#6C63FF"},
        }

    @staticmethod
    async def verify_and_settle(
        db: AsyncSession,
        job: ServiceJob,
        method: str,
        razorpay_order_id: str,
        razorpay_payment_id: str,
        razorpay_signature: str,
    ) -> Payment:
        """
        Step 2 — Verify Razorpay payment and release escrow to worker.

        1. HMAC-SHA256 signature validation (skipped for stub keys so CI/test flow works).
        2. Mark payment RELEASED_TO_WORKER.
        3. Add net earnings to WorkerProfile + create WorkerPayout record.
        4. Transition job → COMPLETED.
        5. Append COMPLETED TimelineEvent.
        """
        stmt = select(Payment).where(Payment.job_id == job.id)
        payment = (await db.execute(stmt)).scalar_one_or_none()

        if not payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment order record not found. Call /create-order first.",
            )

        if payment.status in ("RELEASED_TO_WORKER", "REFUNDED"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment already in terminal state: {payment.status}",
            )

        # ── Signature verification ────────────────────────────────────────────
        if _is_live_razorpay():
            if not _verify_razorpay_signature(
                razorpay_order_id, razorpay_payment_id, razorpay_signature
            ):
                payment.status = "FAILED"
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Razorpay signature verification failed. "
                        "The payment may have been tampered with."
                    ),
                )

        now = datetime.now(timezone.utc)

        # ── Update Payment record ─────────────────────────────────────────────
        payment.status = "RELEASED_TO_WORKER"
        payment.method = method
        payment.gateway = "RAZORPAY"
        payment.gateway_order_id = razorpay_order_id
        payment.gateway_payment_id = razorpay_payment_id
        payment.gateway_signature = razorpay_signature
        payment.paid_at = now
        payment.escrow_released_at = now

        # ── Close the job ─────────────────────────────────────────────────────
        job.status = "COMPLETED"
        job.completed_at = now

        # ── Worker earnings settlement ────────────────────────────────────────
        if job.worker_id:
            wp_stmt = select(WorkerProfile).where(WorkerProfile.user_id == job.worker_id)
            worker_profile = (await db.execute(wp_stmt)).scalar_one_or_none()

            if worker_profile:
                breakdown = payment.breakdown or {}
                platform_fee = breakdown.get("platformFee", 49.0)
                tax = breakdown.get("tax", 0.0)
                # Net worker cut = total collected - platform fee - GST
                net_worker = max(0.0, payment.amount - platform_fee - tax)

                worker_profile.today_earnings += net_worker
                worker_profile.week_earnings += net_worker
                worker_profile.month_earnings += net_worker
                worker_profile.completed_jobs += 1
                worker_profile.current_active_job_id = None

                payout = WorkerPayout(
                    worker_id=job.worker_id,
                    amount=net_worker,
                    status="COMPLETED",
                    payout_method="UPI_INSTANT",
                    reference_id=razorpay_payment_id,
                )
                db.add(payout)

        # ── Timeline event ────────────────────────────────────────────────────
        db.add(
            TimelineEvent(
                job_id=job.id,
                status="COMPLETED",
                title="Payment Verified & Job Completed",
                description=(
                    f"₹{payment.amount} collected via Razorpay ({method}). "
                    f"Payment ID: {razorpay_payment_id}. "
                    "Escrow released to technician instantly."
                ),
            )
        )

        await db.commit()
        await db.refresh(payment)
        await db.refresh(job)
        return payment

    @staticmethod
    async def handle_webhook(
        db: AsyncSession,
        body: bytes,
        signature_header: Optional[str],
    ) -> Dict[str, Any]:
        """
        Handle Razorpay server-to-server webhook.

        Supported events:
          - payment.captured  → Idempotent reconciliation if verify was already called.
          - payment.failed    → Mark payment FAILED.
          - refund.created    → Mark payment REFUNDED.

        Always returns {"status": "ok"} to acknowledge receipt (Razorpay retries on 5xx).
        """
        # ── Webhook signature check (only in production) ──────────────────────
        if _is_live_razorpay():
            if not signature_header:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Missing X-Razorpay-Signature header.",
                )
            if not _verify_razorpay_webhook_signature(body, signature_header):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Razorpay webhook signature verification failed.",
                )

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid JSON in webhook body.",
            )

        event = payload.get("event", "")
        entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
        rp_payment_id = entity.get("id")
        rp_order_id = entity.get("order_id")

        if not rp_order_id:
            return {"status": "ok", "note": "no order_id in payload, skipped"}

        # Locate payment by gateway_order_id
        stmt = select(Payment).where(Payment.gateway_order_id == rp_order_id)
        payment = (await db.execute(stmt)).scalar_one_or_none()

        if not payment:
            return {"status": "ok", "note": "unknown order_id, skipped"}

        now = datetime.now(timezone.utc)

        if event == "payment.captured":
            # Idempotent — only update if still PENDING
            if payment.status == "PENDING":
                payment.gateway_payment_id = rp_payment_id
                payment.status = "HELD_IN_ESCROW"
                payment.paid_at = now
                await db.commit()

        elif event == "payment.failed":
            if payment.status not in ("RELEASED_TO_WORKER", "REFUNDED"):
                payment.status = "FAILED"
                await db.commit()

        elif event == "refund.created":
            payment.status = "REFUNDED"
            await db.commit()

        return {"status": "ok", "event": event}
