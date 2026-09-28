from typing import Any, List

from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user
from app.core.database import get_db
from app.models.sos import SOSIncident
from app.models.user import User
from app.schemas.sos import SOSCreate, SOSResponse, SOSStatusUpdate
from app.services.sos_service import SOSService

router = APIRouter()


@router.post("/trigger", response_model=SOSResponse, status_code=status.HTTP_201_CREATED)
async def trigger_emergency_sos(
    payload: SOSCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    1-Tap Emergency SOS broadcast.
    Immediately creates a critical incident and triggers response dispatch.
    """
    incident = await SOSService.trigger_sos(
        db=db,
        user=current_user,
        location=payload.location,
        contact_number=payload.contact_number,
        job_id=payload.job_id,
        latitude=payload.latitude,
        longitude=payload.longitude,
    )
    return incident


@router.get("/", response_model=List[SOSResponse])
async def list_sos_incidents(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Any:
    """
    Admin Operations Console: Stream and review all emergency distress calls.
    """
    stmt = select(SOSIncident).order_by(SOSIncident.created_at.desc())
    res = await db.execute(stmt)
    incidents = res.scalars().all()
    return incidents


@router.post("/{sos_id}/acknowledge", response_model=SOSResponse)
async def acknowledge_sos(
    sos_id: str,
    payload: SOSStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Any:
    """
    Admin marks the distress call as acknowledged and coordinates with field responders.
    """
    incident = await SOSService.acknowledge_sos(
        db=db,
        sos_id=sos_id,
        notes=payload.resolution_notes
    )
    return incident


@router.post("/{sos_id}/resolve", response_model=SOSResponse)
async def resolve_sos(
    sos_id: str,
    payload: SOSStatusUpdate,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(get_current_admin)
) -> Any:
    """
    Admin marks emergency resolved after safety confirmation.
    """
    incident = await SOSService.resolve_sos(
        db=db,
        sos_id=sos_id,
        resolution_notes=payload.resolution_notes or "Emergency resolved successfully on-site."
    )
    return incident
