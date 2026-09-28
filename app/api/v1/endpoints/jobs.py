from datetime import datetime, timezone
from typing import Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.models.job import ServiceJob, TimelineEvent
from app.models.category import ServiceCategory
from app.models.user import User, WorkerProfile
from app.schemas.job import (
    JobCreate,
    JobStatusUpdate,
    JobCancelRequest,
    ServiceJobResponse,
)
from app.api.deps import (
    get_current_user,
    get_current_active_worker,
)
from app.services.dispatch_service import DispatchService

router = APIRouter()


async def fetch_full_job_by_id(db: AsyncSession, job_id: str) -> Optional[ServiceJob]:
    stmt = (
        select(ServiceJob)
        .options(
            selectinload(ServiceJob.customer),
            selectinload(ServiceJob.worker),
            selectinload(ServiceJob.timeline),
            selectinload(ServiceJob.quote),
            selectinload(ServiceJob.payment),
            selectinload(ServiceJob.rating),
        )
        .where(ServiceJob.id == job_id)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


def serialize_job(job: ServiceJob) -> ServiceJobResponse:
    return ServiceJobResponse(
        id=job.id,
        customer_id=job.customer_id,
        customer_name=job.customer.full_name if job.customer else "Valued Customer",
        customer_phone=job.customer.phone if job.customer else None,
        customer_address=job.customer_address,
        customer_lat=job.customer_lat,
        customer_lng=job.customer_lng,
        category_id=job.category_id,
        category_name=job.category_name,
        problem_type=job.problem_type,
        description=job.description,
        photos=job.photos or [],
        urgency=job.urgency,
        status=job.status,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
        worker_id=job.worker_id,
        worker_name=job.worker.full_name if job.worker else None,
        worker_phone=job.worker.phone if job.worker else None,
        worker_avatar=job.worker.avatar if job.worker else None,
        worker_rating=job.worker.rating if job.worker else None,
        worker_category=job.category_name if job.worker else None,
        worker_distance_km=job.worker_distance_km,
        worker_eta_minutes=job.worker_eta_minutes,
        diagnosis_notes=job.diagnosis_notes,
        before_photos=job.before_photos or [],
        after_photos=job.after_photos or [],
        parts_receipts=job.parts_receipts or [],
        worker_completion_notes=job.worker_completion_notes,
        cancellation_reason=job.cancellation_reason,
        is_sos_triggered=job.is_sos_triggered,
        timeline=job.timeline,
        quote=job.quote,
        payment=job.payment,
        rating=job.rating,
    )


@router.post("/", response_model=ServiceJobResponse, status_code=status.HTTP_201_CREATED)
async def create_job_request(
    payload: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Create a new hyperlocal service request.
    Automatically searches and matches nearby technician or sets status to SEARCHING.
    """
    cat_stmt = select(ServiceCategory).where(ServiceCategory.id == payload.category_id)
    cat_res = await db.execute(cat_stmt)
    category = cat_res.scalar_one_or_none()
    if not category:
        raise HTTPException(status_code=404, detail="Service category not found")

    job = ServiceJob(
        customer_id=current_user.id,
        category_id=category.id,
        category_name=category.name,
        problem_type=payload.problem_type,
        description=payload.description,
        photos=payload.photos,
        urgency=payload.urgency,
        status="SEARCHING",
        customer_address=payload.customer_address,
        customer_lat=payload.customer_lat or 12.9716,
        customer_lng=payload.customer_lng or 77.5946,
    )
    db.add(job)
    await db.flush()

    # Create initial timeline entry
    timeline_entry = TimelineEvent(
        job_id=job.id,
        status="SEARCHING",
        title="Emergency Request Dispatched",
        description=f"Scanning hyperlocal grid for verified {category.name} specialists within 5 km."
    )
    db.add(timeline_entry)
    await db.commit()

    # Attempt automatic worker matching
    await DispatchService.auto_match_and_assign_job(db, job)

    full_job = await fetch_full_job_by_id(db, job.id)
    return serialize_job(full_job)


@router.get("/active", response_model=Optional[ServiceJobResponse])
async def get_active_job(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Fetch the currently active in-flight job for the logged-in customer or technician.
    """
    active_statuses = [
        "SEARCHING",
        "ACCEPTED",
        "EN_ROUTE",
        "ARRIVED",
        "DIAGNOSING",
        "QUOTE_CREATED",
        "QUOTE_APPROVED",
        "REPAIRING",
        "PAYMENT_PENDING",
        "PAYMENT_PROCESSING"
    ]

    stmt = (
        select(ServiceJob)
        .options(
            selectinload(ServiceJob.customer),
            selectinload(ServiceJob.worker),
            selectinload(ServiceJob.timeline),
            selectinload(ServiceJob.quote),
            selectinload(ServiceJob.payment),
            selectinload(ServiceJob.rating),
        )
        .where(
            and_(
                ServiceJob.status.in_(active_statuses),
                or_(
                    ServiceJob.customer_id == current_user.id,
                    ServiceJob.worker_id == current_user.id,
                )
            )
        )
        .order_by(ServiceJob.created_at.desc())
    )
    res = await db.execute(stmt)
    job = res.scalar_one_or_none()
    if not job:
        return None
    return serialize_job(job)


@router.get("/{job_id}", response_model=ServiceJobResponse)
async def get_job_by_id(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Retrieve full job state including quote, timeline, payment, and rating.
    """
    job = await fetch_full_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Service request not found")

    # Access control: only customer, assigned worker, or admin
    if current_user.role != "admin" and job.customer_id != current_user.id and job.worker_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied for this job")

    return serialize_job(job)


@router.get("/", response_model=List[ServiceJobResponse])
async def list_jobs(
    status_filter: Optional[str] = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    List jobs filtered according to user role:
    - Customer sees their bookings
    - Worker sees assigned jobs
    - Admin sees all jobs across the network
    """
    stmt = (
        select(ServiceJob)
        .options(
            selectinload(ServiceJob.customer),
            selectinload(ServiceJob.worker),
            selectinload(ServiceJob.timeline),
            selectinload(ServiceJob.quote),
            selectinload(ServiceJob.payment),
            selectinload(ServiceJob.rating),
        )
    )

    if current_user.role == "customer":
        stmt = stmt.where(ServiceJob.customer_id == current_user.id)
    elif current_user.role == "worker":
        stmt = stmt.where(ServiceJob.worker_id == current_user.id)

    if status_filter:
        stmt = stmt.where(ServiceJob.status == status_filter)

    stmt = stmt.order_by(ServiceJob.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    jobs = res.scalars().all()

    return [serialize_job(j) for j in jobs]


@router.post("/{job_id}/accept", response_model=ServiceJobResponse)
async def worker_accept_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_worker)
) -> Any:
    """
    Technician accepts an open SEARCHING dispatch request.
    """
    job = await fetch_full_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status != "SEARCHING":
        raise HTTPException(status_code=400, detail="Job is no longer open for acceptance")

    job.worker_id = current_user.id
    job.status = "ACCEPTED"
    job.worker_distance_km = 1.2
    job.worker_eta_minutes = 8

    # Update worker profile active job
    w_stmt = select(WorkerProfile).where(WorkerProfile.user_id == current_user.id)
    w_res = await db.execute(w_stmt)
    w_profile = w_res.scalar_one_or_none()
    if w_profile:
        w_profile.current_active_job_id = job.id

    timeline = TimelineEvent(
        job_id=job.id,
        status="ACCEPTED",
        title="Technician Accepted",
        description=f"{current_user.full_name} accepted the callout. Preparing toolkit."
    )
    db.add(timeline)
    await db.commit()

    full_job = await fetch_full_job_by_id(db, job.id)
    return serialize_job(full_job)


@router.put("/{job_id}/status", response_model=ServiceJobResponse)
async def update_job_status(
    job_id: str,
    payload: JobStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_worker)
) -> Any:
    """
    Transition job status through its operational phases:
    EN_ROUTE -> ARRIVED -> DIAGNOSING -> REPAIRING -> COMPLETED
    """
    job = await fetch_full_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = payload.status

    if payload.notes:
        if payload.status == "DIAGNOSING":
            job.diagnosis_notes = payload.notes
        elif payload.status == "COMPLETED":
            job.worker_completion_notes = payload.notes
            job.completed_at = datetime.now(timezone.utc)

    if payload.before_photos:
        job.before_photos = payload.before_photos
    if payload.after_photos:
        job.after_photos = payload.after_photos
    if payload.parts_receipts:
        job.parts_receipts = payload.parts_receipts

    title_map = {
        "EN_ROUTE": "Technician En Route",
        "ARRIVED": "Technician Arrived On Site",
        "DIAGNOSING": "Diagnosis Underway",
        "QUOTE_APPROVED": "Quote Approved by Customer",
        "REPAIRING": "Repair Work In Progress",
        "PAYMENT_PENDING": "Repair Completed - Awaiting Payment",
        "COMPLETED": "Job Finished Successfully",
    }

    timeline = TimelineEvent(
        job_id=job.id,
        status=payload.status,
        title=title_map.get(payload.status, f"Status updated to {payload.status}"),
        description=payload.notes or f"Job transitioned to {payload.status} stage."
    )
    db.add(timeline)
    await db.commit()

    full_job = await fetch_full_job_by_id(db, job.id)
    return serialize_job(full_job)


@router.post("/{job_id}/cancel", response_model=ServiceJobResponse)
async def cancel_job(
    job_id: str,
    payload: JobCancelRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Cancel an active job request.
    """
    job = await fetch_full_job_by_id(db, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in ["COMPLETED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail="Cannot cancel a finished job")

    job.status = "CANCELLED"
    job.cancellation_reason = payload.reason

    if job.worker_id:
        w_stmt = select(WorkerProfile).where(WorkerProfile.user_id == job.worker_id)
        w_res = await db.execute(w_stmt)
        w_profile = w_res.scalar_one_or_none()
        if w_profile and w_profile.current_active_job_id == job.id:
            w_profile.current_active_job_id = None

    timeline = TimelineEvent(
        job_id=job.id,
        status="CANCELLED",
        title="Job Cancelled",
        description=f"Cancelled by {current_user.full_name}: {payload.reason}"
    )
    db.add(timeline)
    await db.commit()

    full_job = await fetch_full_job_by_id(db, job.id)
    return serialize_job(full_job)
