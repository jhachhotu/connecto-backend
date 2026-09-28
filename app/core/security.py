from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Union
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.security import OAuth2PasswordBearer
import httpx
from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_STR}/auth/login"
)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against a stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate bcrypt hash from plain text password."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any],
    role: str = "customer",
    expires_delta: Optional[timedelta] = None,
    extra_claims: Optional[Dict[str, Any]] = None
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": str(subject),
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        to_encode.update(extra_claims)
        
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(
    subject: Union[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """Create a long-lived signed JWT refresh token."""
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(subject),
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate signature and expiry of a JWT token."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise ValueError(f"Invalid token: {str(e)}")


async def verify_google_oauth_token(id_token: str) -> Dict[str, Any]:
    """
    Verify Google OAuth2 ID Token either directly or via Google tokeninfo API endpoint.
    Returns user info (email, name, picture, sub).
    """
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(
                "https://oauth2.googleapis.com/tokeninfo",
                params={"id_token": id_token}
            )
            if resp.status_code != 200:
                raise ValueError("Invalid Google OAuth2 ID token")
            token_data = resp.json()

            # Optional audience check if client id is configured
            if settings.GOOGLE_CLIENT_ID and token_data.get("aud") != settings.GOOGLE_CLIENT_ID:
                raise ValueError("Google Token audience does not match configured client id")

            return {
                "google_id": token_data.get("sub"),
                "email": token_data.get("email"),
                "email_verified": token_data.get("email_verified") == "true" or token_data.get("email_verified") is True,
                "name": token_data.get("name", "Google User"),
                "avatar": token_data.get("picture", ""),
            }
        except httpx.RequestError as e:
            raise ValueError(f"Could not connect to Google OAuth service: {str(e)}")
