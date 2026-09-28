import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.api import api_router
from app.core.config import settings
from app.core.database import AsyncSessionLocal, Base, engine
from app.db.init_db import init_database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: Create tables and seed initial catalog upon startup.
    """
    logger.info("Initializing Connecto database and schemas...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSessionLocal() as session:
            await init_database(session)
        logger.info("Connecto database initialized and seeded successfully.")
    except Exception as e:
        logger.warning(f"Database initialization note: {e}")
        logger.info("Proceeding with app launch; ensure Supabase pooler connection is accessible.")

    yield

    logger.info("Shutting down Connecto API server...")
    await engine.dispose()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Hyperlocal On-Demand Emergency Services API (FastAPI + Supabase PostgreSQL + OAuth2/JWT + Payments)",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan,
)

# CORS Middleware setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Global unhandled error on {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred. Please contact Connecto support."},
    )


# Health check endpoints
@app.get("/health", tags=["Health"])
@app.get("/", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "database_pooler": "Supabase PgBouncer (Transaction mode)" if settings.SUPABASE_TRANSACTION_POOLER else "Direct Postgres",
        "docs": "/docs",
    }


# Mount API V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
