import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class DisputeRecord(Base):
    __tablename__ = "dispute_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(50), ForeignKey("service_jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    raised_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    reason = Column(Text, nullable=False)
    status = Column(String(30), default="PENDING", nullable=False, index=True)  # PENDING, UNDER_REVIEW, RESOLVED, REFUNDED, DISMISSED
    resolution_notes = Column(Text, nullable=True)
    refund_amount = Column(Float, default=0.0, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    job = relationship("ServiceJob", back_populates="dispute")
    raised_by = relationship("User", foreign_keys=[raised_by_user_id])
