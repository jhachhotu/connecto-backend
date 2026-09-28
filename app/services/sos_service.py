from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ServiceJob, TimelineEvent
from app.models.sos import SOSIncident
from app.models.user import User


class SOSService:
    @staticmethod
    async def trigger_sos(
        db: AsyncSession,
        user: User,
        location: str,
        contact_number: str,
        job_id: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> SOSIncident:
        worker_name = "Quick Reaction Fleet"

        # If linked to a job, fetch details and flag job
        if job_id:
            job_stmt = select(ServiceJob).where(ServiceJob.id == job_id)
            j_res = await db.execute(job_stmt)
            job = j_res.scalar_one_or_none()
            if job:
                job.is_sos_triggered = True
                if job.worker_id:
                    w_stmt = select(User).where(User.id == job.worker_id)
                    w_res = await db.execute(w_stmt)
                    w_user = w_res.scalar_one_or_none()
                    if w_user:
                        worker_name = w_user.full_name

                # Add timeline record
                timeline = TimelineEvent(
                    job_id=job.id,
                    status=job.status,
                    title="EMERGENCY SOS TRIGGERED",
                    description=f"Distress alert broadcast by {user.full_name} at {location}."
                )
                db.add(timeline)

        incident = SOSIncident(
            job_id=job_id,
            triggered_by_user_id=user.id,
            customer_name=user.full_name,
            worker_name=worker_name,
            contact_number=contact_number,
            location=location,
            latitude=latitude or 12.9716,
            longitude=longitude or 77.5946,
            urgency="CRITICAL",
            status="TRIGGERED",
        )
        db.add(incident)
        await db.commit()
        await db.refresh(incident)
        return incident

    @staticmethod
    async def acknowledge_sos(
        db: AsyncSession,
        sos_id: str,
        notes: Optional[str] = None
    ) -> SOSIncident:
        stmt = select(SOSIncident).where(SOSIncident.id == sos_id)
        res = await db.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise HTTPException(status_code=404, detail="SOS Incident not found")

        incident.status = "ACKNOWLEDGED"
        incident.acknowledged_at = datetime.now(timezone.utc)
        if notes:
            incident.resolution_notes = notes
        await db.commit()
        await db.refresh(incident)
        return incident

    @staticmethod
    async def resolve_sos(
        db: AsyncSession,
        sos_id: str,
        resolution_notes: str
    ) -> SOSIncident:
        stmt = select(SOSIncident).where(SOSIncident.id == sos_id)
        res = await db.execute(stmt)
        incident = res.scalar_one_or_none()
        if not incident:
            raise HTTPException(status_code=404, detail="SOS Incident not found")

        incident.status = "RESOLVED"
        incident.resolved_at = datetime.now(timezone.utc)
        incident.resolution_notes = resolution_notes

        # Unflag job if linked
        if incident.job_id:
            job_stmt = select(ServiceJob).where(ServiceJob.id == incident.job_id)
            j_res = await db.execute(job_stmt)
            job = j_res.scalar_one_or_none()
            if job:
                job.is_sos_triggered = False

        await db.commit()
        await db.refresh(incident)
        return incident
