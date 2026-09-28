from datetime import datetime
from typing import Any, Dict, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


# ──────────────────────────────────────────────────────────────────────────────
# Razorpay Payment Method Enum
# ──────────────────────────────────────────────────────────────────────────────
# Razorpay supports: upi, card, netbanking, wallet, emi, paylater
# We expose the four most common ones. "CASH" is kept for offline jobs.
RAZORPAY_METHODS = Literal["UPI", "CARD", "NET_BANKING", "WALLET", "CASH"]


# ──────────────────────────────────────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────────────────────────────────────

class RazorpayOrderCreate(BaseModel):
    """
    POST /payments/create-order

    The frontend sends only the job_id. The backend fetches the approved quote
    and calls Razorpay API to generate an order. The response feeds directly
    into the Razorpay Checkout JS / React Native SDK options object.
    """
    job_id: str = Field(..., description="The ServiceJob ID to initiate payment for.")


class RazorpayVerifyRequest(BaseModel):
    """
    POST /payments/verify

    After the Razorpay SDK completes payment on the frontend, it returns three
    tokens. The frontend must forward all three here for HMAC-SHA256 verification.

    For CASH payments: supply method='CASH' and leave the razorpay_* fields empty.
    The service will skip signature check and directly mark the payment settled.
    """
    job_id: str
    method: RAZORPAY_METHODS = Field(
        default="UPI",
        description="Payment method used: UPI, CARD, NET_BANKING, WALLET, or CASH.",
    )

    # Razorpay Checkout callback fields
    razorpay_order_id: Optional[str] = Field(
        default=None,
        description="order_id returned by Razorpay Checkout (starts with 'order_').",
    )
    razorpay_payment_id: Optional[str] = Field(
        default=None,
        description="payment_id returned by Razorpay Checkout (starts with 'pay_').",
    )
    razorpay_signature: Optional[str] = Field(
        default=None,
        description="HMAC-SHA256 signature string returned by Razorpay Checkout.",
    )

    @model_validator(mode="after")
    def require_razorpay_fields_for_non_cash(self) -> "RazorpayVerifyRequest":
        if self.method != "CASH":
            missing = [
                f for f in ("razorpay_order_id", "razorpay_payment_id", "razorpay_signature")
                if not getattr(self, f)
            ]
            if missing:
                raise ValueError(
                    f"razorpay_order_id, razorpay_payment_id, and razorpay_signature "
                    f"are required for method={self.method}. Missing: {missing}"
                )
        return self


# ──────────────────────────────────────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────────────────────────────────────

class RazorpayOrderResponse(BaseModel):
    """
    Response from POST /payments/create-order.
    Feed this directly into Razorpay Checkout options.
    """
    order_id: str
    amount: float                   # INR (human-readable)
    amount_paise: int               # INR × 100 (Razorpay unit)
    currency: str = "INR"
    key_id: str                     # RAZORPAY_KEY_ID — safe to expose to frontend
    job_id: str
    description: str
    breakdown: Dict[str, Any]
    prefill: Dict[str, Any] = {}    # Caller can merge name/email/phone
    theme: Dict[str, str] = {"color": "#6C63FF"}


class PaymentResponse(BaseModel):
    """
    Persisted Payment record — returned from verify and GET /{job_id}.
    """
    id: str
    job_id: str
    customer_id: str
    worker_id: Optional[str] = None
    amount: float
    currency: str
    status: str
    method: str
    gateway: str
    gateway_order_id: Optional[str] = None
    gateway_payment_id: Optional[str] = None
    invoice_number: str
    breakdown: Dict[str, Any]
    paid_at: Optional[datetime] = None
    escrow_released_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkerPayoutResponse(BaseModel):
    """
    Worker payout record — returned from GET /payments/payouts/worker.
    """
    id: str
    worker_id: str
    amount: float
    status: str
    payout_method: str
    reference_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
