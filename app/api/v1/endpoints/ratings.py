from typing import Any, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.core.database import get_db
from app.models.job import ServiceJob, TimelineEvent
from app.models.rating import JobRating
from app.models.user import User, WorkerProfile
from app.schemas.rating import RatingCreate, RatingResponse, WorkerRatingSummary
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/", response_model=RatingResponse, status_code=status.HTTP_201_CREATED)
async def submit_rating(
    payload: RatingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Customer rates the assigned technician across skill, punctuality, and transparency.
    Automatically recalculates the worker's average rating in their verified passport.
    """
    job_stmt = select(ServiceJob).where(ServiceJob.id == payload.job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if not job.worker_id:
        raise HTTPException(status_code=400, detail="Cannot rate a job with no assigned worker")

    # Check for existing rating
    existing_stmt = select(JobRating).where(JobRating.job_id == payload.job_id)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="This job has already been rated")

    rating = JobRating(
        job_id=payload.job_id,
        customer_id=current_user.id,
        worker_id=job.worker_id,
        overall=payload.overall,
        skill=payload.skill,
        punctuality=payload.punctuality,
        communication=payload.communication,
        pricing_transparency=payload.pricing_transparency,
        review_text=payload.review_text,
    )
    db.add(rating)

    # Recalculate worker averages
    worker_ratings_stmt = select(func.avg(JobRating.overall), func.count(JobRating.id)).where(JobRating.worker_id == job.worker_id)
    w_ratings_res = await db.execute(worker_ratings_stmt)
    avg_score, total_count = w_ratings_res.one()

    new_count = (total_count or 0) + 1
    new_avg = round((((avg_score or 4.8) * (total_count or 0)) + payload.overall) / new_count, 2)

    w_profile_stmt = select(WorkerProfile).where(WorkerProfile.user_id == job.worker_id)
    w_profile_res = await db.execute(w_profile_stmt)
    w_profile = w_profile_res.scalar_one_or_none()
    if w_profile:
        w_profile.rating = new_avg
        w_profile.reviews_count = new_count

    w_user_stmt = select(User).where(User.id == job.worker_id)
    w_user_res = await db.execute(w_user_stmt)
    w_user = w_user_res.scalar_one_or_none()
    if w_user:
        w_user.rating = new_avg

    timeline = TimelineEvent(
        job_id=job.id,
        status="COMPLETED",
        title="Customer Rating Submitted",
        description=f"Received {payload.overall}★ rating from customer."
    )
    db.add(timeline)

    await db.commit()
    await db.refresh(rating)
    return rating


@router.get("/worker/{worker_id}", response_model=WorkerRatingSummary)
async def get_worker_ratings_summary(
    worker_id: str,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Get detailed breakdown of ratings and review averages for a worker's verified passport.
    """
    w_stmt = select(User).where(User.id == worker_id)
    w_res = await db.execute(w_stmt)
    worker = w_res.scalar_one_or_none()
    if not worker:
        raise HTTPException(status_code=404, detail="Technician not found")

    stats_stmt = select(
        func.avg(JobRating.overall),
        func.count(JobRating.id),
        func.avg(JobRating.skill),
        func.avg(JobRating.punctuality),
        func.avg(JobRating.communication),
        func.avg(JobRating.pricing_transparency),
    ).where(JobRating.worker_id == worker_id)
    
    stats_res = await db.execute(stats_stmt)
    overall, count, skill, punct, comm, pricing = stats_res.one()

    return WorkerRatingSummary(
        worker_id=worker.id,
        worker_name=worker.full_name,
        average_rating=round(overall or 4.88, 2),
        total_reviews=count or 0,
        skill_avg=round(skill or 4.9, 2),
        punctuality_avg=round(punct or 4.8, 2),
        communication_avg=round(comm or 4.85, 2),
        pricing_avg=round(pricing or 4.95, 2),
    )
