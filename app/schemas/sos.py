from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class SOSCreate(BaseModel):
    job_id: Optional[str] = None
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    contact_number: str


class SOSStatusUpdate(BaseModel):
    status: str = Field(..., pattern="^(ACKNOWLEDGED|IN_PROGRESS|RESOLVED)$")
    resolution_notes: Optional[str] = None


class SOSResponse(BaseModel):
    id: str
    job_id: Optional[str] = None
    triggered_by_user_id: str
    customer_name: str
    worker_name: str
    contact_number: str
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    urgency: str
    status: str
    resolution_notes: Optional[str] = None
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
