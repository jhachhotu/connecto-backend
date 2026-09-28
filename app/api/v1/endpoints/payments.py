"""
Razorpay-exclusive payments router for Connecto.

Endpoints:
  POST /payments/create-order       — Generate Razorpay order for approved quote
  POST /payments/verify             — HMAC-SHA256 verify + release escrow to worker
  GET  /payments/payouts/worker     — Technician earnings ledger
  GET  /payments/{job_id}           — Payment details + invoice
  POST /payments/webhook            — Razorpay server-to-server webhook (no auth)

IMPORTANT: Static routes (/create-order, /verify, /payouts/worker, /webhook)
are declared BEFORE the parameterized /{job_id} route to prevent Starlette
from shadowing them with the path parameter.
"""

from typing import Any, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_active_worker, get_current_user
from app.core.database import get_db
from app.models.job import ServiceJob
from app.models.payment import Payment, WorkerPayout
from app.models.user import User
from app.schemas.payment import (
    PaymentResponse,
    RazorpayOrderCreate,
    RazorpayOrderResponse,
    RazorpayVerifyRequest,
    WorkerPayoutResponse,
)
from app.services.payment_service import PaymentService

router = APIRouter()


# ──────────────────────────────────────────────────────────────────────────────
# POST /create-order
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/create-order",
    response_model=RazorpayOrderResponse,
    summary="Create Razorpay order",
    description=(
        "Creates a Razorpay payment order for the job's approved quote total. "
        "The response object maps 1:1 to the Razorpay Checkout JS SDK `options` object. "
        "The quote **must be approved** by the customer before calling this endpoint."
    ),
)
async def create_payment_order(
    payload: RazorpayOrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = (
        select(ServiceJob)
        .options(selectinload(ServiceJob.quote))
        .where(ServiceJob.id == payload.job_id)
    )
    job = (await db.execute(stmt)).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    # Only the job's customer or an admin can initiate payment
    if current_user.role != "admin" and job.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to initiate payment for this job.",
        )

    order_data = await PaymentService.create_razorpay_order(db=db, job=job)
    return order_data


# ──────────────────────────────────────────────────────────────────────────────
# POST /verify
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/verify",
    response_model=PaymentResponse,
    summary="Verify Razorpay payment & release escrow",
    description=(
        "Validates the HMAC-SHA256 signature returned by the Razorpay Checkout SDK. "
        "On success: marks payment as RELEASED_TO_WORKER, credits worker earnings, "
        "creates a payout record, and transitions the job to COMPLETED."
    ),
)
async def verify_payment(
    payload: RazorpayVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = (
        select(ServiceJob)
        .options(selectinload(ServiceJob.quote))
        .where(ServiceJob.id == payload.job_id)
    )
    job = (await db.execute(stmt)).scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found.")

    if current_user.role != "admin" and job.customer_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not authorized to verify payment for this job.",
        )

    # CASH payment — skip Razorpay fields entirely
    order_id = payload.razorpay_order_id or f"order_cash_{job.id}"
    payment_id = payload.razorpay_payment_id or f"pay_cash_{job.id}"
    signature = payload.razorpay_signature or ""

    payment = await PaymentService.verify_and_settle(
        db=db,
        job=job,
        method=payload.method,
        razorpay_order_id=order_id,
        razorpay_payment_id=payment_id,
        razorpay_signature=signature,
    )
    return payment


# ──────────────────────────────────────────────────────────────────────────────
# GET /payouts/worker
# (MUST be before /{job_id} — static route takes precedence)
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/payouts/worker",
    response_model=List[WorkerPayoutResponse],
    summary="Worker earnings ledger",
    description="Returns the authenticated technician's full payout history, latest first.",
)
async def get_worker_payout_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_worker),
) -> Any:
    stmt = (
        select(WorkerPayout)
        .where(WorkerPayout.worker_id == current_user.id)
        .order_by(WorkerPayout.created_at.desc())
    )
    payouts = (await db.execute(stmt)).scalars().all()
    return payouts


# ──────────────────────────────────────────────────────────────────────────────
# GET /{job_id}
# ──────────────────────────────────────────────────────────────────────────────

@router.get(
    "/{job_id}",
    response_model=PaymentResponse,
    summary="Payment details & invoice",
    description="Retrieve full payment record, invoice number, breakdown, and settlement status.",
)
async def get_payment_details(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Any:
    stmt = select(Payment).where(Payment.job_id == job_id)
    payment = (await db.execute(stmt)).scalar_one_or_none()

    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment record not found for this job.",
        )
    return payment


# ──────────────────────────────────────────────────────────────────────────────
# POST /webhook  (no auth — Razorpay calls this server-to-server)
# ──────────────────────────────────────────────────────────────────────────────

@router.post(
    "/webhook",
    summary="Razorpay webhook handler",
    description=(
        "Receives Razorpay server-to-server event callbacks. "
        "Validates `X-Razorpay-Signature` header using RAZORPAY_WEBHOOK_SECRET. "
        "Handles: payment.captured, payment.failed, refund.created. "
        "Always returns HTTP 200 to acknowledge receipt (Razorpay retries on 5xx)."
    ),
)
async def razorpay_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
    x_razorpay_signature: Optional[str] = Header(default=None, alias="X-Razorpay-Signature"),
) -> Any:
    body = await request.body()
    result = await PaymentService.handle_webhook(
        db=db,
        body=body,
        signature_header=x_razorpay_signature,
    )
    return result
