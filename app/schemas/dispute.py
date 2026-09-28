from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class DisputeCreate(BaseModel):
    job_id: str
    reason: str = Field(..., min_length=10)


class DisputeResolveRequest(BaseModel):
    status: str = Field(..., pattern="^(RESOLVED|REFUNDED|DISMISSED)$")
    resolution_notes: str
    refund_amount: Optional[float] = 0.0


class DisputeResponse(BaseModel):
    id: str
    job_id: str
    raised_by_user_id: str
    reason: str
    status: str
    resolution_notes: Optional[str] = None
    refund_amount: float
    created_at: datetime
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
