from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import decode_token
from app.models.user import User
from app.schemas.auth import (
    Token,
    LoginRequest,
    RegisterRequest,
    GoogleAuthRequest,
    RefreshTokenRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import AuthService
from app.api.deps import get_current_user

router = APIRouter()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Register a new user account as either 'customer' or 'worker'.
    Returns JWT access and refresh tokens.
    """
    user = await AuthService.register_user(db, payload)
    access_token, refresh_token = AuthService.generate_token_pair(user)

    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar=user.avatar,
    )


@router.post("/login", response_model=Token)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Authenticate via email and password (JSON payload).
    """
    user = await AuthService.authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=400, detail="User account is deactivated")

    access_token, refresh_token = AuthService.generate_token_pair(user)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar=user.avatar,
    )


@router.post("/login/oauth", response_model=Token)
async def login_oauth_form(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Standard OAuth2 password form for Swagger UI authorization dialog.
    """
    user = await AuthService.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token, refresh_token = AuthService.generate_token_pair(user)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar=user.avatar,
    )


@router.post("/google", response_model=Token)
async def google_auth(
    payload: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Authenticate using Google OAuth2 ID Token.
    Validates token against Google's API, then provisions or retrieves the user.
    """
    try:
        user = await AuthService.authenticate_google_user(
            db=db,
            id_token=payload.id_token,
            role=payload.role or "customer"
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    access_token, refresh_token = AuthService.generate_token_pair(user)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar=user.avatar,
    )


@router.post("/refresh", response_model=Token)
async def refresh_access_token(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
) -> Any:
    """
    Exchange a valid refresh token for a fresh access token.
    """
    try:
        token_data = decode_token(payload.refresh_token)
        if token_data.get("type") != "refresh":
            raise HTTPException(status_code=400, detail="Invalid token type")
        user_id = token_data.get("sub")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))

    stmt = select(User).where(User.id == user_id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="User account not found or deactivated")

    access_token, refresh_token = AuthService.generate_token_pair(user)
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=user.role,
        avatar=user.avatar,
    )


@router.get("/me", response_model=UserResponse)
async def read_current_user(
    current_user: User = Depends(get_current_user)
) -> Any:
    """
    Get profile information of currently authenticated user.
    """
    return current_user
