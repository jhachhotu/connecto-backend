from datetime import datetime, timezone
import uuid
from sqlalchemy import (
    Column,
    String,
    Boolean,
    Float,
    Integer,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(30), unique=True, index=True, nullable=True)
    hashed_password = Column(String(255), nullable=True)  # Nullable for OAuth users
    full_name = Column(String(150), nullable=False)
    role = Column(String(20), default="customer", nullable=False)  # 'customer', 'worker', 'admin'
    avatar = Column(String(500), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    address = Column(String(300), nullable=True)
    rating = Column(Float, default=5.0, nullable=False)
    total_orders = Column(Integer, default=0, nullable=False)
    google_id = Column(String(100), unique=True, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    worker_profile = relationship("WorkerProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    customer_jobs = relationship("ServiceJob", foreign_keys="ServiceJob.customer_id", back_populates="customer")
    worker_jobs = relationship("ServiceJob", foreign_keys="ServiceJob.worker_id", back_populates="worker")
    ratings_given = relationship("JobRating", foreign_keys="JobRating.customer_id", back_populates="customer")
    ratings_received = relationship("JobRating", foreign_keys="JobRating.worker_id", back_populates="worker")


class WorkerProfile(Base):
    __tablename__ = "worker_profiles"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    category_id = Column(String(100), nullable=False, default="car-breakdown")
    skills = Column(JSON, default=list, nullable=False)  # List of skill strings
    experience_years = Column(Integer, default=3, nullable=False)
    is_online = Column(Boolean, default=True, nullable=False, index=True)
    verification_status = Column(String(30), default="VERIFIED", nullable=False)  # NOT_STARTED, SUBMITTED, UNDER_REVIEW, VERIFIED, REJECTED
    
    # KYC & Verified Passport
    aadhaar_verified = Column(Boolean, default=True, nullable=False)
    police_cleared = Column(Boolean, default=True, nullable=False)
    skill_audited = Column(Boolean, default=True, nullable=False)
    badge_title = Column(String(100), default="Master Craftsman")

    # Geolocation for Hyperlocal Matching
    latitude = Column(Float, default=12.9716, nullable=False)
    longitude = Column(Float, default=77.5946, nullable=False)
    current_area = Column(String(200), default="Indiranagar Sector 4, Bengaluru")

    # Metrics
    acceptance_rate = Column(Float, default=98.5, nullable=False)
    completion_rate = Column(Float, default=99.0, nullable=False)
    completed_jobs = Column(Integer, default=427, nullable=False)
    reviews_count = Column(Integer, default=312, nullable=False)
    rating = Column(Float, default=4.88, nullable=False)

    # Earnings Ledger
    today_earnings = Column(Float, default=1450.0, nullable=False)
    week_earnings = Column(Float, default=8920.0, nullable=False)
    month_earnings = Column(Float, default=34200.0, nullable=False)
    current_active_job_id = Column(String(50), nullable=True)

    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    user = relationship("User", back_populates="worker_profile")
