from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class QuoteCreate(BaseModel):
    diagnostic_fee: float = Field(..., ge=0)
    labour: float = Field(..., ge=0)
    parts: float = Field(default=0.0, ge=0)
    platform_fee: float = Field(default=49.0, ge=0)
    tax: float = Field(default=0.0, ge=0)
    parts_description: Optional[str] = None


class QuoteReviewRequest(BaseModel):
    is_approved: bool
    rejection_reason: Optional[str] = None


class QuoteResponse(BaseModel):
    id: str
    job_id: str
    diagnostic_fee: float
    labour: float
    parts: float
    platform_fee: float
    tax: float
    total: float
    parts_description: Optional[str] = None
    is_approved: bool
    rejection_reason: Optional[str] = None
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
