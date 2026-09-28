from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Float,
    Boolean,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Quote(Base):
    __tablename__ = "quotes"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(50), ForeignKey("service_jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    
    diagnostic_fee = Column(Float, nullable=False, default=149.0)
    labour = Column(Float, nullable=False, default=250.0)
    parts = Column(Float, nullable=False, default=0.0)
    platform_fee = Column(Float, nullable=False, default=49.0)
    tax = Column(Float, nullable=False, default=22.4)
    total = Column(Float, nullable=False, default=470.4)
    
    parts_description = Column(Text, nullable=True)
    is_approved = Column(Boolean, default=False, nullable=False)
    rejection_reason = Column(String(300), nullable=True)
    approved_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("ServiceJob", back_populates="quote")
