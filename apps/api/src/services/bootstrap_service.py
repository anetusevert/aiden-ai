"""Bootstrap service for creating tenants with initial setup."""

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Organization,
    OrganizationMembership,
    Tenant,
    User,
    Workspace,
    WorkspaceMembership,
)
from src.schemas.tenant import (
    BootstrapResponse,
    TenantCreateWithBootstrap,
)
from src.utils.passwords import hash_password


class BootstrapError(Exception):
    """Base exception for bootstrap errors."""

    pass


class TenantExistsError(BootstrapError):
    """Raised when tenant already exists."""

    pass


class BootstrapService:
    """Service for bootstrapping tenants with initial setup.

    Creates tenant + workspace + user + admin membership in a single transaction.
    Ensures atomicity - if any part fails, the entire operation is rolled back.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_tenant_with_bootstrap(
        self, data: TenantCreateWithBootstrap
    ) -> BootstrapResponse:
        """Create a tenant with optional bootstrap (workspace + admin user + membership).

        If bootstrap payload is provided, creates:
        1. Tenant
        2. First workspace
        3. First admin user
        4. Membership linking admin user to workspace with ADMIN role

        All operations run in a single transaction for atomicity.
        """
        try:
            # Create tenant
            tenant = Tenant(
                name=data.name,
                primary_jurisdiction=data.primary_jurisdiction,
                data_residency_policy=data.data_residency_policy,
            )
            self.db.add(tenant)
            await self.db.flush()  # Get tenant ID without committing

            workspace_id = None
            workspace_name = None
            admin_user_id = None
            admin_user_email = None

            # If bootstrap payload provided, create all related entities
            if data.bootstrap:
                # Create workspace
                workspace = Workspace(
                    tenant_id=tenant.id,
                    name=data.bootstrap.workspace.name,
                    workspace_type=data.bootstrap.workspace.workspace_type,
                    jurisdiction_profile=data.bootstrap.workspace.jurisdiction_profile,
                    default_language=data.bootstrap.workspace.default_language,
                )
                self.db.add(workspace)
                await self.db.flush()

                # Create admin user
                admin_user = User(
                    tenant_id=tenant.id,
                    email=data.bootstrap.admin_user.email,
                    full_name=data.bootstrap.admin_user.full_name,
                    password_hash=hash_password(data.bootstrap.admin_user.password),
                    default_workspace_id=None,
                )
                self.db.add(admin_user)
                await self.db.flush()

                admin_user.default_workspace_id = workspace.id

                # Create admin membership
                membership = WorkspaceMembership(
                    tenant_id=tenant.id,
                    workspace_id=workspace.id,
                    user_id=admin_user.id,
                    role="ADMIN",
                )
                self.db.add(membership)
                await self.db.flush()

                default_org = Organization(
                    tenant_id=tenant.id,
                    workspace_id=workspace.id,
                    name=workspace.name,
                    description="Default organization created during tenant bootstrap",
                    master_user_id=admin_user.id,
                )
                self.db.add(default_org)
                await self.db.flush()

                default_org_membership = OrganizationMembership(
                    organization_id=default_org.id,
                    user_id=admin_user.id,
                    role="MASTER",
                )
                self.db.add(default_org_membership)
                await self.db.flush()

                workspace_id = workspace.id
                workspace_name = workspace.name
                admin_user_id = admin_user.id
                admin_user_email = admin_user.email

            # Commit the entire transaction
            await self.db.commit()
            await self.db.refresh(tenant)

            return BootstrapResponse(
                tenant_id=tenant.id,
                tenant_name=tenant.name,
                workspace_id=workspace_id,
                workspace_name=workspace_name,
                admin_user_id=admin_user_id,
                admin_user_email=admin_user_email,
                created_at=tenant.created_at,
            )

        except IntegrityError as e:
            await self.db.rollback()
            error_msg = str(e.orig) if e.orig else str(e)
            # Check for common constraint violations
            if "uq_users_tenant_email" in error_msg:
                raise TenantExistsError(
                    f"User with email '{data.bootstrap.admin_user.email}' already exists"
                ) from e
            if "uq_workspaces_tenant_name" in error_msg:
                raise TenantExistsError(
                    f"Workspace with name '{data.bootstrap.workspace.name}' already exists"
                ) from e
            # Generic error
            raise TenantExistsError(
                "Failed to create tenant - a conflict occurred"
            ) from e
