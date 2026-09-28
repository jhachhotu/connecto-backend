from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    users,
    categories,
    jobs,
    quotes,
    payments,
    ratings,
    disputes,
    sos,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication & OAuth2"])
api_router.include_router(users.router, prefix="/users", tags=["Users & Verified Worker Passport"])
api_router.include_router(categories.router, prefix="/categories", tags=["Service Categories & Catalog"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["Hyperlocal Jobs & Dispatch"])
api_router.include_router(quotes.router, prefix="/quotes", tags=["Transparent Quotes & Diagnoses"])
api_router.include_router(payments.router, prefix="/payments", tags=["Payments, Escrow & Settlements"])
api_router.include_router(ratings.router, prefix="/ratings", tags=["Ratings & Reviews"])
api_router.include_router(disputes.router, prefix="/disputes", tags=["Disputes & Resolution"])
api_router.include_router(sos.router, prefix="/sos", tags=["Emergency SOS Operations"])
