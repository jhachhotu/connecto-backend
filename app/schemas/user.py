from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class WorkerProfileResponse(BaseModel):
    id: str
    user_id: str
    category_id: str
    skills: List[str]
    experience_years: int
    is_online: bool
    verification_status: str
    aadhaar_verified: bool
    police_cleared: bool
    skill_audited: bool
    badge_title: str
    latitude: float
    longitude: float
    current_area: str
    acceptance_rate: float
    completion_rate: float
    completed_jobs: int
    reviews_count: int
    rating: float
    today_earnings: float
    week_earnings: float
    month_earnings: float
    current_active_job_id: Optional[str] = None
    distance_km: Optional[float] = None
    eta_minutes: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: str
    email: EmailStr
    phone: Optional[str] = None
    full_name: str
    role: str
    avatar: Optional[str] = None
    is_active: bool
    is_verified: bool
    address: Optional[str] = None
    rating: float
    total_orders: int
    created_at: datetime
    worker_profile: Optional[WorkerProfileResponse] = None

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    avatar: Optional[str] = None


class WorkerProfileUpdate(BaseModel):
    is_online: Optional[bool] = None
    skills: Optional[List[str]] = None
    current_area: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    category_id: Optional[str] = None


class LocationPing(BaseModel):
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    current_area: Optional[str] = None
