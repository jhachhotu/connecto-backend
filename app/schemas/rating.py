from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RatingCreate(BaseModel):
    job_id: str
    overall: float = Field(..., ge=1.0, le=5.0)
    skill: float = Field(default=5.0, ge=1.0, le=5.0)
    punctuality: float = Field(default=5.0, ge=1.0, le=5.0)
    communication: float = Field(default=5.0, ge=1.0, le=5.0)
    pricing_transparency: float = Field(default=5.0, ge=1.0, le=5.0)
    review_text: Optional[str] = None


class RatingResponse(BaseModel):
    id: str
    job_id: str
    customer_id: str
    worker_id: str
    overall: float
    skill: float
    punctuality: float
    communication: float
    pricing_transparency: float
    review_text: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WorkerRatingSummary(BaseModel):
    worker_id: str
    worker_name: str
    average_rating: float
    total_reviews: int
    skill_avg: float
    punctuality_avg: float
    communication_avg: float
    pricing_avg: float
