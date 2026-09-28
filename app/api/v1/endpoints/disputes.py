from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.database import get_db
from app.models.dispute import DisputeRecord
from app.models.job import ServiceJob, TimelineEvent
from app.models.payment import Payment
from app.models.user import User
from app.schemas.dispute import DisputeCreate, DisputeResolveRequest, DisputeResponse

router = APIRouter()


@router.post("/", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
async def raise_dispute(
    payload: DisputeCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Customer or worker raises a formal dispute regarding a service job.
    Freezes job state and alerts Admin Operations.
    """
    job_stmt = select(ServiceJob).where(ServiceJob.id == payload.job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    existing_stmt = select(DisputeRecord).where(DisputeRecord.job_id == payload.job_id)
    existing_res = await db.execute(existing_stmt)
    if existing_res.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="A dispute has already been filed for this job")

    dispute = DisputeRecord(
        job_id=payload.job_id,
        raised_by_user_id=current_user.id,
        reason=payload.reason,
        status="PENDING",
    )
    db.add(dispute)

    job.status = "DISPUTED"

    timeline = TimelineEvent(
        job_id=job.id,
        status="DISPUTED",
        title="Dispute Lodged",
        description=f"Formal dispute initiated: {payload.reason}"
    )
    db.add(timeline)

    await db.commit()
    await db.refresh(dispute)
    return dispute


@router.get("/", response_model=List[DisputeResponse])
async def list_disputes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    List disputes:
    - Admin views all disputes across the platform
    - User views disputes they filed
    """
    stmt = select(DisputeRecord)
    if current_user.role != "admin":
        stmt = stmt.where(DisputeRecord.raised_by_user_id == current_user.id)

    stmt = stmt.order_by(DisputeRecord.created_at.desc())
    res = await db.execute(stmt)
    disputes = res.scalars().all()
    return disputes


@router.post("/{dispute_id}/resolve", response_model=DisputeResponse)
async def resolve_dispute(
    dispute_id: str,
    payload: DisputeResolveRequest,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Any:
    """
    Admin Operations resolves a dispute and can issue an escrow refund.
    """
    stmt = select(DisputeRecord).where(DisputeRecord.id == dispute_id)
    res = await db.execute(stmt)
    dispute = res.scalar_one_or_none()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute record not found")

    dispute.status = payload.status
    dispute.resolution_notes = payload.resolution_notes
    dispute.refund_amount = payload.refund_amount or 0.0
    dispute.resolved_at = datetime.now(timezone.utc)

    # If refunded, update payment status
    if payload.status == "REFUNDED" and payload.refund_amount and payload.refund_amount > 0:
        pay_stmt = select(Payment).where(Payment.job_id == dispute.job_id)
        pay_res = await db.execute(pay_stmt)
        payment = pay_res.scalar_one_or_none()
        if payment:
            payment.status = "REFUNDED"

    # Add timeline note to job
    timeline = TimelineEvent(
        job_id=dispute.job_id,
        status="COMPLETED" if payload.status != "REFUNDED" else "CANCELLED",
        title=f"Dispute {payload.status.capitalize()}",
        description=f"Admin Resolution: {payload.resolution_notes}"
    )
    db.add(timeline)

    await db.commit()
    await db.refresh(dispute)
    return dispute
