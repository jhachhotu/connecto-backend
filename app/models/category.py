from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, DateTime, Float, Integer, String

from app.core.database import Base


class ServiceCategory(Base):
    __tablename__ = "service_categories"

    id = Column(String(50), primary_key=True, index=True)  # e.g., 'car-breakdown', 'bike-scooter'
    name = Column(String(100), nullable=False)
    icon_name = Column(String(50), nullable=False)
    description = Column(String(300), nullable=False)
    diagnostic_fee = Column(Float, nullable=False, default=149.0)
    estimated_arrival_min = Column(Integer, nullable=False, default=12)
    popular_problems = Column(JSON, default=list, nullable=False)
    active_workers_count = Column(Integer, default=18, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    display_order = Column(Integer, default=1, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
