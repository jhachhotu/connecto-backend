from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from app.models.user import User, WorkerProfile
from app.schemas.auth import RegisterRequest
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    verify_google_oauth_token,
)


class AuthService:
    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        stmt = select(User).where(User.email == email.lower())
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()
        if not user or not user.hashed_password:
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user

    @staticmethod
    async def register_user(
        db: AsyncSession,
        payload: RegisterRequest
    ) -> User:
        # Check existing email
        stmt = select(User).where(User.email == payload.email.lower())
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A user with this email already exists"
            )

        # Check existing phone if supplied
        if payload.phone:
            stmt_phone = select(User).where(User.phone == payload.phone)
            res_phone = await db.execute(stmt_phone)
            if res_phone.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A user with this phone number already exists"
                )

        hashed_pw = get_password_hash(payload.password)
        user = User(
            email=payload.email.lower(),
            hashed_password=hashed_pw,
            full_name=payload.full_name,
            phone=payload.phone,
            role=payload.role,
            avatar=payload.avatar or f"https://api.dicebear.com/7.x/initials/svg?seed={payload.full_name}",
            is_active=True,
            is_verified=True,
        )
        db.add(user)
        await db.flush()

        # If role is worker, create associated WorkerProfile
        if payload.role == "worker":
            profile = WorkerProfile(
                user_id=user.id,
                category_id=payload.category_id or "car-breakdown",
                experience_years=payload.experience_years or 3,
                is_online=True,
                verification_status="VERIFIED",
                aadhaar_verified=True,
                police_cleared=True,
                skill_audited=True,
                badge_title="Certified Technician",
            )
            db.add(profile)

        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def authenticate_google_user(
        db: AsyncSession,
        id_token: str,
        role: str = "customer"
    ) -> User:
        token_info = await verify_google_oauth_token(id_token)
        google_id = token_info["google_id"]
        email = token_info["email"].lower()

        # 1. Lookup by google_id
        stmt = select(User).where(User.google_id == google_id)
        res = await db.execute(stmt)
        user = res.scalar_one_or_none()

        if not user:
            # 2. Lookup by email
            stmt_email = select(User).where(User.email == email)
            res_email = await db.execute(stmt_email)
            user = res_email.scalar_one_or_none()

            if user:
                # Link google_id
                user.google_id = google_id
                if not user.avatar and token_info.get("avatar"):
                    user.avatar = token_info["avatar"]
            else:
                # Register new user via OAuth
                user = User(
                    email=email,
                    google_id=google_id,
                    full_name=token_info.get("name", "Google User"),
                    role=role,
                    avatar=token_info.get("avatar") or f"https://api.dicebear.com/7.x/initials/svg?seed={token_info.get('name')}",
                    is_active=True,
                    is_verified=token_info.get("email_verified", True),
                )
                db.add(user)
                await db.flush()

                if role == "worker":
                    profile = WorkerProfile(
                        user_id=user.id,
                        category_id="car-breakdown",
                        experience_years=2,
                        is_online=True,
                        verification_status="VERIFIED",
                    )
                    db.add(profile)

            await db.commit()
            await db.refresh(user)

        return user

    @staticmethod
    def generate_token_pair(user: User) -> Tuple[str, str]:
        access_token = create_access_token(
            subject=user.id,
            role=user.role,
            extra_claims={"email": user.email, "name": user.full_name}
        )
        refresh_token = create_refresh_token(subject=user.id)
        return access_token, refresh_token
