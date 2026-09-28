from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import (
    get_current_active_worker,
    get_current_admin,
    get_current_user,
)
from app.core.database import get_db
from app.models.user import User, WorkerProfile
from app.schemas.user import (
    LocationPing,
    UserResponse,
    UserUpdate,
    WorkerProfileResponse,
    WorkerProfileUpdate,
)
from app.services.dispatch_service import DispatchService

router = APIRouter()


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Update profile details for the authenticated user.
    """
    if payload.full_name is not None:
        current_user.full_name = payload.full_name
    if payload.phone is not None:
        current_user.phone = payload.phone
    if payload.address is not None:
        current_user.address = payload.address
    if payload.avatar is not None:
        current_user.avatar = payload.avatar

    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.put("/worker/profile", response_model=WorkerProfileResponse)
async def update_worker_profile(
    payload: WorkerProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_worker)
) -> Any:
    """
    Update worker profile, toggle online/offline availability, or update skills.
    """
    stmt = select(WorkerProfile).where(WorkerProfile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    if payload.is_online is not None:
        profile.is_online = payload.is_online
    if payload.skills is not None:
        profile.skills = payload.skills
    if payload.current_area is not None:
        profile.current_area = payload.current_area
    if payload.latitude is not None:
        profile.latitude = payload.latitude
    if payload.longitude is not None:
        profile.longitude = payload.longitude
    if payload.category_id is not None:
        profile.category_id = payload.category_id

    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/worker/location", status_code=status.HTTP_200_OK)
async def update_worker_location(
    payload: LocationPing,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_worker)
) -> Any:
    """
    Worker app broadcasts live GPS coordinates every 15-30 seconds.
    """
    stmt = select(WorkerProfile).where(WorkerProfile.user_id == current_user.id)
    res = await db.execute(stmt)
    profile = res.scalar_one_or_none()
    if not profile:
        raise HTTPException(status_code=404, detail="Worker profile not found")

    profile.latitude = payload.latitude
    profile.longitude = payload.longitude
    if payload.current_area:
        profile.current_area = payload.current_area

    await db.commit()
    return {"status": "ok", "latitude": profile.latitude, "longitude": profile.longitude}


@router.get("/workers/nearby", response_model=List[WorkerProfileResponse])
async def get_nearby_workers(
    category_id: str = Query(..., description="Service category ID"),
    lat: float = Query(12.9716, description="Customer latitude"),
    lng: float = Query(77.5946, description="Customer longitude"),
    radius_km: float = Query(15.0, description="Search radius in kilometers"),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Public proximity query returning verified nearby technicians for the requested trade.
    """
    workers = await DispatchService.find_nearby_workers(
        db=db,
        category_id=category_id,
        lat=lat,
        lng=lng,
        radius_km=radius_km,
        limit=10
    )

    results = []
    for user, profile, dist, eta in workers:
        p_dict = {
            "id": profile.id,
            "user_id": profile.user_id,
            "category_id": profile.category_id,
            "skills": profile.skills,
            "experience_years": profile.experience_years,
            "is_online": profile.is_online,
            "verification_status": profile.verification_status,
            "aadhaar_verified": profile.aadhaar_verified,
            "police_cleared": profile.police_cleared,
            "skill_audited": profile.skill_audited,
            "badge_title": profile.badge_title,
            "latitude": profile.latitude,
            "longitude": profile.longitude,
            "current_area": profile.current_area,
            "acceptance_rate": profile.acceptance_rate,
            "completion_rate": profile.completion_rate,
            "completed_jobs": profile.completed_jobs,
            "reviews_count": profile.reviews_count,
            "rating": profile.rating,
            "today_earnings": profile.today_earnings,
            "week_earnings": profile.week_earnings,
            "month_earnings": profile.month_earnings,
            "current_active_job_id": profile.current_active_job_id,
            "distance_km": dist,
            "eta_minutes": eta,
        }
        results.append(WorkerProfileResponse(**p_dict))

    return results


@router.get("/workers", response_model=List[UserResponse])
async def list_all_workers(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Any:
    """
    Admin endpoint to view all technicians and their verification status.
    """
    stmt = (
        select(User)
        .options(selectinload(User.worker_profile))
        .where(User.role == "worker")
    )
    res = await db.execute(stmt)
    workers = res.scalars().all()
    return workers
