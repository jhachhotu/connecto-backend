from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    Text,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class JobRating(Base):
    __tablename__ = "job_ratings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    job_id = Column(String(50), ForeignKey("service_jobs.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    customer_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    worker_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    
    overall = Column(Float, nullable=False)
    skill = Column(Float, nullable=False, default=5.0)
    punctuality = Column(Float, nullable=False, default=5.0)
    communication = Column(Float, nullable=False, default=5.0)
    pricing_transparency = Column(Float, nullable=False, default=5.0)
    
    review_text = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    job = relationship("ServiceJob", back_populates="rating")
    customer = relationship("User", foreign_keys=[customer_id], back_populates="ratings_given")
    worker = relationship("User", foreign_keys=[worker_id], back_populates="ratings_received")
