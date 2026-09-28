import math
from typing import List, Optional, Tuple

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import ServiceJob, TimelineEvent
from app.models.user import User, WorkerProfile


def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle distance between two points on the Earth in kilometers."""
    r = 6371.0  # Earth's radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(r * c, 2)


class DispatchService:
    @staticmethod
    async def find_nearby_workers(
        db: AsyncSession,
        category_id: str,
        lat: float,
        lng: float,
        radius_km: float = 15.0,
        limit: int = 5
    ) -> List[Tuple[User, WorkerProfile, float, int]]:
        """
        Find online verified workers within radius_km, sorted by distance & rating.
        Returns list of tuples: (User, WorkerProfile, distance_km, eta_minutes)
        """
        stmt = (
            select(User, WorkerProfile)
            .join(WorkerProfile, User.id == WorkerProfile.user_id)
            .where(
                and_(
                    User.is_active.is_(True),
                    WorkerProfile.is_online.is_(True),
                    WorkerProfile.category_id == category_id,
                    WorkerProfile.verification_status == "VERIFIED",
                )
            )
        )
        result = await db.execute(stmt)
        candidates = result.all()

        scored_workers = []
        for user, profile in candidates:
            dist = calculate_haversine_distance(lat, lng, profile.latitude, profile.longitude)
            if dist <= radius_km:
                # Estimate travel time based on avg city speed (25 km/h) + 3 min prep
                eta = max(5, int((dist / 25.0) * 60) + 3)
                scored_workers.append((user, profile, dist, eta))

        # Sort primarily by distance, secondarily by worker rating desc
        scored_workers.sort(key=lambda item: (item[2], -item[1].rating))
        return scored_workers[:limit]

    @staticmethod
    async def auto_match_and_assign_job(
        db: AsyncSession,
        job: ServiceJob
    ) -> Optional[User]:
        """
        Find the best available technician and assign to the job.
        Transitions job status from SEARCHING to ACCEPTED.
        """
        workers = await DispatchService.find_nearby_workers(
            db,
            category_id=job.category_id,
            lat=job.customer_lat,
            lng=job.customer_lng,
            radius_km=20.0,
            limit=1
        )

        if not workers:
            return None

        matched_user, matched_profile, dist, eta = workers[0]

        job.worker_id = matched_user.id
        job.worker_distance_km = dist
        job.worker_eta_minutes = eta
        job.status = "ACCEPTED"
        matched_profile.current_active_job_id = job.id

        # Add timeline event
        timeline_entry = TimelineEvent(
            job_id=job.id,
            status="ACCEPTED",
            title="Technician Assigned & En Route",
            description=f"{matched_user.full_name} accepted the request. Estimated arrival in ~{eta} mins ({dist} km away)."
        )
        db.add(timeline_entry)

        await db.commit()
        await db.refresh(job)
        return matched_user
