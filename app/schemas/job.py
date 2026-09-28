from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.quote import QuoteResponse
from app.schemas.payment import PaymentResponse
from app.schemas.rating import RatingResponse


class TimelineEventResponse(BaseModel):
    id: str
    job_id: str
    status: str
    title: str
    description: str
    created_at: datetime

    class Config:
        from_attributes = True


class JobCreate(BaseModel):
    category_id: str
    problem_type: str = Field(..., min_length=2)
    description: str = Field(..., min_length=5)
    customer_address: str = Field(..., min_length=5)
    customer_lat: Optional[float] = 12.9716
    customer_lng: Optional[float] = 77.5946
    urgency: str = Field(default="NORMAL", pattern="^(NORMAL|URGENT|EMERGENCY)$")
    photos: List[str] = Field(default_factory=list)


class JobStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        pattern="^(ACCEPTED|EN_ROUTE|ARRIVED|DIAGNOSING|QUOTE_CREATED|QUOTE_APPROVED|REPAIRING|PAYMENT_PENDING|COMPLETED|CANCELLED)$"
    )
    notes: Optional[str] = None
    before_photos: Optional[List[str]] = None
    after_photos: Optional[List[str]] = None
    parts_receipts: Optional[List[str]] = None


class JobCancelRequest(BaseModel):
    reason: str = Field(..., min_length=5)


class WorkerSummary(BaseModel):
    id: str
    name: str
    phone: Optional[str] = None
    avatar: Optional[str] = None
    rating: float
    category: str
    distance_km: Optional[float] = None
    eta_minutes: Optional[int] = None


class ServiceJobResponse(BaseModel):
    id: str
    customer_id: str
    customer_name: str
    customer_phone: Optional[str] = None
    customer_address: str
    customer_lat: float
    customer_lng: float
    category_id: str
    category_name: str
    problem_type: str
    description: str
    photos: List[str]
    urgency: str
    status: str
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None

    # Worker info
    worker_id: Optional[str] = None
    worker_name: Optional[str] = None
    worker_phone: Optional[str] = None
    worker_avatar: Optional[str] = None
    worker_rating: Optional[float] = None
    worker_category: Optional[str] = None
    worker_distance_km: Optional[float] = None
    worker_eta_minutes: Optional[int] = None

    # Diagnosis & Execution Evidence
    diagnosis_notes: Optional[str] = None
    before_photos: List[str] = []
    after_photos: List[str] = []
    parts_receipts: List[str] = []
    worker_completion_notes: Optional[str] = None
    cancellation_reason: Optional[str] = None
    is_sos_triggered: bool = False

    # Embedded relationships
    timeline: List[TimelineEventResponse] = []
    quote: Optional[QuoteResponse] = None
    payment: Optional[PaymentResponse] = None
    rating: Optional[RatingResponse] = None

    model_config = ConfigDict(from_attributes=True)
