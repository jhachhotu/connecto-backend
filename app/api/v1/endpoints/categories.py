from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.models.category import ServiceCategory
from app.models.user import User
from app.schemas.category import (
    ServiceCategoryCreate,
    ServiceCategoryUpdate,
    ServiceCategoryResponse,
)
from app.api.deps import get_current_admin

router = APIRouter()


@router.get("/", response_model=List[ServiceCategoryResponse])
async def list_categories(
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    List all active service categories ordered by display order.
    """
    stmt = (
        select(ServiceCategory)
        .where(ServiceCategory.is_active == True)
        .order_by(ServiceCategory.display_order.asc())
    )
    res = await db.execute(stmt)
    categories = res.scalars().all()
    return categories


@router.get("/{category_id}", response_model=ServiceCategoryResponse)
async def get_category(
    category_id: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get category details by id.
    """
    stmt = select(ServiceCategory).where(ServiceCategory.id == category_id)
    res = await db.execute(stmt)
    cat = res.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Service category not found")
    return cat


@router.post("/", response_model=ServiceCategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: ServiceCategoryCreate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Any:
    """
    Admin: Register a new trade or service category.
    """
    stmt = select(ServiceCategory).where(ServiceCategory.id == payload.id)
    res = await db.execute(stmt)
    if res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Category ID already exists")

    category = ServiceCategory(
        id=payload.id,
        name=payload.name,
        icon_name=payload.icon_name,
        description=payload.description,
        diagnostic_fee=payload.diagnostic_fee,
        estimated_arrival_min=payload.estimated_arrival_min,
        popular_problems=payload.popular_problems,
        is_active=payload.is_active,
        display_order=payload.display_order,
    )
    db.add(category)
    await db.commit()
    await db.refresh(category)
    return category


@router.put("/{category_id}", response_model=ServiceCategoryResponse)
async def update_category(
    category_id: str,
    payload: ServiceCategoryUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Any:
    """
    Admin: Update diagnostic fee, arrival estimate, or status of a trade.
    """
    stmt = select(ServiceCategory).where(ServiceCategory.id == category_id)
    res = await db.execute(stmt)
    cat = res.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Service category not found")

    if payload.name is not None:
        cat.name = payload.name
    if payload.icon_name is not None:
        cat.icon_name = payload.icon_name
    if payload.description is not None:
        cat.description = payload.description
    if payload.diagnostic_fee is not None:
        cat.diagnostic_fee = payload.diagnostic_fee
    if payload.estimated_arrival_min is not None:
        cat.estimated_arrival_min = payload.estimated_arrival_min
    if payload.popular_problems is not None:
        cat.popular_problems = payload.popular_problems
    if payload.is_active is not None:
        cat.is_active = payload.is_active
    if payload.display_order is not None:
        cat.display_order = payload.display_order

    await db.commit()
    await db.refresh(cat)
    return cat
