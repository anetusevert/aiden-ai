"""Workspace service layer."""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Workspace
from src.schemas import WorkspaceCreate


class WorkspaceServiceError(Exception):
    """Base exception for workspace service errors."""

    pass


class DuplicateWorkspaceError(WorkspaceServiceError):
    """Raised when workspace name already exists in tenant."""

    pass


class WorkspaceService:
    """Service for workspace operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_workspace(
        self, tenant_id: str, data: WorkspaceCreate
    ) -> Workspace:
        """Create a new workspace within a tenant."""
        workspace = Workspace(
            tenant_id=tenant_id,
            name=data.name,
            workspace_type=data.workspace_type,
            jurisdiction_profile=data.jurisdiction_profile,
            default_language=data.default_language,
        )
        self.db.add(workspace)
        try:
            await self.db.commit()
            await self.db.refresh(workspace)
            return workspace
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateWorkspaceError(
                f"Workspace with name '{data.name}' already exists in tenant"
            )

    async def get_workspace_by_id(
        self, workspace_id: str, tenant_id: str
    ) -> Workspace | None:
        """Get a workspace by ID, scoped to tenant."""
        result = await self.db.execute(
            select(Workspace).where(
                Workspace.id == workspace_id,
                Workspace.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_workspaces(self, tenant_id: str) -> list[Workspace]:
        """List all workspaces for a tenant."""
        result = await self.db.execute(
            select(Workspace)
            .where(Workspace.tenant_id == tenant_id)
            .order_by(Workspace.created_at)
        )
        return list(result.scalars().all())
