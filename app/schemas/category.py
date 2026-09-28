from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ServiceCategoryBase(BaseModel):
    name: str = Field(..., min_length=2)
    icon_name: str
    description: str
    diagnostic_fee: float = Field(..., ge=0)
    estimated_arrival_min: int = Field(default=12, ge=1)
    popular_problems: List[str] = Field(default_factory=list)
    is_active: bool = True
    display_order: int = 1


class ServiceCategoryCreate(ServiceCategoryBase):
    id: str = Field(..., min_length=2, pattern="^[a-z0-9-]+$")


class ServiceCategoryUpdate(BaseModel):
    name: Optional[str] = None
    icon_name: Optional[str] = None
    description: Optional[str] = None
    diagnostic_fee: Optional[float] = None
    estimated_arrival_min: Optional[int] = None
    popular_problems: Optional[List[str]] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class ServiceCategoryResponse(ServiceCategoryBase):
    id: str
    active_workers_count: int

    model_config = ConfigDict(from_attributes=True)
