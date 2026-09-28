from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_worker, get_current_user
from app.core.database import get_db
from app.models.job import ServiceJob, TimelineEvent
from app.models.quote import Quote
from app.models.user import User
from app.schemas.quote import QuoteCreate, QuoteResponse, QuoteReviewRequest

router = APIRouter()


@router.post("/{job_id}", response_model=QuoteResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_quote(
    job_id: str,
    payload: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_worker)
) -> Any:
    """
    Technician creates/submits transparent itemized quote for customer approval.
    Calculates total = diagnostic_fee + labour + parts + platform_fee + tax.
    """
    job_stmt = select(ServiceJob).where(ServiceJob.id == job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Calculate total and tax if tax not supplied (5% GST standard)
    subtotal = payload.diagnostic_fee + payload.labour + payload.parts + payload.platform_fee
    tax = payload.tax if payload.tax > 0 else round(subtotal * 0.05, 2)
    total = round(subtotal + tax, 2)

    stmt = select(Quote).where(Quote.job_id == job_id)
    res = await db.execute(stmt)
    quote = res.scalar_one_or_none()

    if not quote:
        quote = Quote(
            job_id=job_id,
            diagnostic_fee=payload.diagnostic_fee,
            labour=payload.labour,
            parts=payload.parts,
            platform_fee=payload.platform_fee,
            tax=tax,
            total=total,
            parts_description=payload.parts_description,
            is_approved=False,
        )
        db.add(quote)
    else:
        quote.diagnostic_fee = payload.diagnostic_fee
        quote.labour = payload.labour
        quote.parts = payload.parts
        quote.platform_fee = payload.platform_fee
        quote.tax = tax
        quote.total = total
        quote.parts_description = payload.parts_description
        quote.is_approved = False
        quote.rejection_reason = None

    # Transition job to QUOTE_CREATED
    job.status = "QUOTE_CREATED"

    timeline = TimelineEvent(
        job_id=job.id,
        status="QUOTE_CREATED",
        title="Estimate Prepared by Technician",
        description=f"Transparent itemized quote of ₹{total} submitted. Awaiting customer authorization."
    )
    db.add(timeline)

    await db.commit()
    await db.refresh(quote)
    return quote


@router.post("/{job_id}/review", response_model=QuoteResponse)
async def review_quote(
    job_id: str,
    payload: QuoteReviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Customer authorizes or declines the technician's itemized quote.
    """
    job_stmt = select(ServiceJob).where(ServiceJob.id == job_id)
    job_res = await db.execute(job_stmt)
    job = job_res.scalar_one_or_none()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    quote_stmt = select(Quote).where(Quote.job_id == job_id)
    quote_res = await db.execute(quote_stmt)
    quote = quote_res.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found for this job")

    if payload.is_approved:
        quote.is_approved = True
        quote.approved_at = datetime.now(timezone.utc)
        quote.rejection_reason = None
        job.status = "QUOTE_APPROVED"

        timeline = TimelineEvent(
            job_id=job.id,
            status="QUOTE_APPROVED",
            title="Quote Authorized",
            description=f"Customer accepted quote of ₹{quote.total}. Repair work authorized to proceed."
        )
        db.add(timeline)
    else:
        quote.is_approved = False
        quote.rejection_reason = payload.rejection_reason or "Customer declined quote terms"
        job.status = "DIAGNOSING"

        timeline = TimelineEvent(
            job_id=job.id,
            status="DIAGNOSING",
            title="Quote Revision Requested",
            description=f"Customer rejected quote: {quote.rejection_reason}"
        )
        db.add(timeline)

    await db.commit()
    await db.refresh(quote)
    return quote


@router.get("/{job_id}", response_model=QuoteResponse)
async def get_quote_by_job_id(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Fetch quote for a specific job.
    """
    stmt = select(Quote).where(Quote.job_id == job_id)
    res = await db.execute(stmt)
    quote = res.scalar_one_or_none()
    if not quote:
        raise HTTPException(status_code=404, detail="Quote not found")
    return quote
