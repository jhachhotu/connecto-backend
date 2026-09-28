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


def generate_sos_id() -> str:
    short_num = str(uuid.uuid4().int)[:4]
    return f"SOS-{short_num}"


class SOSIncident(Base):
    __tablename__ = "sos_incidents"

    id = Column(String(50), primary_key=True, default=generate_sos_id, index=True)
    job_id = Column(String(50), ForeignKey("service_jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    triggered_by_user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)

    customer_name = Column(String(150), nullable=False)
    worker_name = Column(String(150), nullable=False, default="Assigned Dispatcher")
    contact_number = Column(String(30), nullable=False)
    location = Column(String(300), nullable=False)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    urgency = Column(String(20), default="CRITICAL", nullable=False)
    status = Column(String(30), default="TRIGGERED", nullable=False, index=True)  # TRIGGERED, ACKNOWLEDGED, IN_PROGRESS, RESOLVED
    resolution_notes = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    triggered_by = relationship("User", foreign_keys=[triggered_by_user_id])
    job = relationship("ServiceJob")
