import json
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Connecto Hyperlocal Services API"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"

    # Security & JWT
    SECRET_KEY: str = "super-secret-jwt-key-replace-in-production-min-32-chars-long"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # CORS
    BACKEND_CORS_ORIGINS: Union[List[str], str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "*"
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, str) and v.startswith("["):
            return json.loads(v)
        elif isinstance(v, list):
            return v
        return ["*"]

    # Database & Supabase Pooler
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/connecto"
    SYNC_DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/connecto"
    SUPABASE_TRANSACTION_POOLER: bool = True
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 300

    @field_validator("DATABASE_URL", mode="before")
    def format_async_database_url(cls, v: str) -> str:
        """
        Normalize postgres connection string for SQLAlchemy asyncpg engine.
        Supabase provides 'postgres://' or 'postgresql://' URLs.
        Asyncpg requires 'postgresql+asyncpg://'.
        """
        if not v:
            return "postgresql+asyncpg://postgres:postgres@localhost:5432/connecto"
        url = str(v)
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+asyncpg://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    # Google OAuth2
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""

    # Payment Gateway — Razorpay (sole gateway for INR payments)
    # Update these with your actual Razorpay credentials
    RAZORPAY_KEY_ID: str = "rzp_test_samplekey123"
    RAZORPAY_KEY_SECRET: str = "rzp_test_samplesecret456"
    RAZORPAY_WEBHOOK_SECRET: str = "rzp_webhook_secret_789"

    # Emergency Dispatch
    SMS_GATEWAY_API_KEY: str = ""
    EMERGENCY_DISPATCH_PHONE: str = "+911122334455"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()
