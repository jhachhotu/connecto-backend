from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_invoice_num() -> str:
    short_num = str(uuid.uuid4().int)[:6]
    return f"INV-{short_num}"


class Payment(Base):
    __tablename__ = "payments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(50), ForeignKey("service_jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    
    # Status: PENDING, HELD_IN_ESCROW, RELEASED_TO_WORKER, REFUNDED, FAILED
    status = Column(String(30), default="PENDING", nullable=False, index=True)
    method = Column(String(30), default="UPI", nullable=False)  # UPI, CARD, NET_BANKING, CASH
    gateway = Column(String(30), default="RAZORPAY", nullable=False)  # RAZORPAY, CASH
    
    # Gateway Identifiers
    gateway_order_id = Column(String(100), nullable=True, index=True)
    gateway_payment_id = Column(String(100), nullable=True, index=True)
    gateway_signature = Column(String(255), nullable=True)
    invoice_number = Column(String(50), default=generate_invoice_num, unique=True, nullable=False)
    
    breakdown = Column(JSON, default=dict, nullable=False)  # diagnosticFee, labour, parts, platformFee, tax
    
    paid_at = Column(DateTime(timezone=True), nullable=True)
    escrow_released_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("ServiceJob", back_populates="payment")


class WorkerPayout(Base):
    __tablename__ = "worker_payouts"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    status = Column(String(30), default="COMPLETED", nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    payout_method = Column(String(50), default="UPI_INSTANT", nullable=False)
    reference_id = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
