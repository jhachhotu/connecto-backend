from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_job_id() -> str:
    # Human-friendly short code like JOB-4921
    short_num = str(uuid.uuid4().int)[:4]
    return f"JOB-{short_num}"


class ServiceJob(Base):
    __tablename__ = "service_jobs"

    id = Column(String(50), primary_key=True, default=generate_job_id, index=True)
    customer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    category_id = Column(String(50), ForeignKey("service_categories.id"), nullable=False)
    
    # Request Details
    category_name = Column(String(100), nullable=False)
    problem_type = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    photos = Column(JSON, default=list, nullable=False)
    urgency = Column(String(20), default="NORMAL", nullable=False)  # NORMAL, URGENT, EMERGENCY
    
    # State Machine
    status = Column(
        String(30),
        default="SEARCHING",
        nullable=False,
        index=True
    )  # SEARCHING, ACCEPTED, EN_ROUTE, ARRIVED, DIAGNOSING, QUOTE_CREATED, QUOTE_APPROVED, REPAIRING, PAYMENT_PENDING, PAYMENT_PROCESSING, COMPLETED, CANCELLED, DISPUTED
    
    # Location
    customer_address = Column(String(300), nullable=False)
    customer_lat = Column(Float, default=12.9716, nullable=False)
    customer_lng = Column(Float, default=77.5946, nullable=False)
    worker_distance_km = Column(Float, nullable=True)
    worker_eta_minutes = Column(Integer, nullable=True)

    # Diagnosis & Execution Evidence
    diagnosis_notes = Column(Text, nullable=True)
    before_photos = Column(JSON, default=list, nullable=False)
    after_photos = Column(JSON, default=list, nullable=False)
    parts_receipts = Column(JSON, default=list, nullable=False)
    worker_completion_notes = Column(Text, nullable=True)
    cancellation_reason = Column(String(300), nullable=True)
    is_sos_triggered = Column(Boolean, default=False, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    customer = relationship("User", foreign_keys=[customer_id], back_populates="customer_jobs")
    worker = relationship("User", foreign_keys=[worker_id], back_populates="worker_jobs")
    category = relationship("ServiceCategory")
    timeline = relationship("TimelineEvent", back_populates="job", cascade="all, delete-orphan", order_by="TimelineEvent.created_at")
    quote = relationship("Quote", back_populates="job", uselist=False, cascade="all, delete-orphan")
    payment = relationship("Payment", back_populates="job", uselist=False, cascade="all, delete-orphan")
    rating = relationship("JobRating", back_populates="job", uselist=False, cascade="all, delete-orphan")
    dispute = relationship("DisputeRecord", back_populates="job", uselist=False, cascade="all, delete-orphan")


class TimelineEvent(Base):
    __tablename__ = "timeline_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(50), ForeignKey("service_jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    status = Column(String(30), nullable=False)
    title = Column(String(150), nullable=False)
    description = Column(String(300), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("ServiceJob", back_populates="timeline")
