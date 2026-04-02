"""Tenant service layer."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Tenant
from src.schemas import TenantCreate


class TenantService:
    """Service for tenant operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant(self, data: TenantCreate) -> Tenant:
        """Create a new tenant."""
        tenant = Tenant(
            name=data.name,
            primary_jurisdiction=data.primary_jurisdiction,
            data_residency_policy=data.data_residency_policy,
        )
        self.db.add(tenant)
        await self.db.commit()
        await self.db.refresh(tenant)
        return tenant

    async def get_tenant_by_id(self, tenant_id: str) -> Tenant | None:
        """Get a tenant by ID."""
        result = await self.db.execute(select(Tenant).where(Tenant.id == tenant_id))
        return result.scalar_one_or_none()

    async def list_tenants(self) -> list[Tenant]:
        """List all tenants (for development only)."""
        result = await self.db.execute(select(Tenant).order_by(Tenant.created_at))
        return list(result.scalars().all())
