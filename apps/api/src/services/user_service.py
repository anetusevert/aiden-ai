"""User service layer."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import User
from src.schemas import UserCreate
from src.utils.passwords import hash_password


class UserServiceError(Exception):
    """Base exception for user service errors."""

    pass


class DuplicateUserError(UserServiceError):
    """Raised when user email already exists in tenant."""

    pass


class UserService:
    """Service for user operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_user(self, tenant_id: str, data: UserCreate) -> User:
        """Create a new user within a tenant."""
        pwd_hash = hash_password(data.password) if data.password else None
        user = User(
            tenant_id=tenant_id,
            email=data.email,
            full_name=data.full_name,
            password_hash=pwd_hash,
        )
        self.db.add(user)
        try:
            await self.db.commit()
            await self.db.refresh(user)
            return user
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateUserError(
                f"User with email '{data.email}' already exists in tenant"
            )

    async def get_user_by_id(self, user_id: str, tenant_id: str) -> User | None:
        """Get a user by ID, scoped to tenant."""
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str, tenant_id: str) -> User | None:
        """Get a user by email, scoped to tenant."""
        from src.utils.passwords import normalize_email

        en = normalize_email(email)
        result = await self.db.execute(
            select(User).where(
                User.email_normalized == en,
                User.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_users(self, tenant_id: str) -> list[User]:
        """List all users for a tenant."""
        result = await self.db.execute(
            select(User).where(User.tenant_id == tenant_id).order_by(User.created_at)
        )
        return list(result.scalars().all())
