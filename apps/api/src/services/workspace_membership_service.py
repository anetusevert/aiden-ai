"""Workspace Membership service layer."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.models import User, Workspace, WorkspaceMembership
from src.utils.passwords import hash_password, normalize_email
from src.schemas import WorkspaceMembershipCreate


class MembershipServiceError(Exception):
    """Base exception for membership service errors."""

    pass


class DuplicateMembershipError(MembershipServiceError):
    """Raised when user is already a member of workspace."""

    pass


class UserNotFoundError(MembershipServiceError):
    """Raised when user is not found in tenant."""

    pass


class MembershipNotFoundError(MembershipServiceError):
    """Raised when membership is not found."""

    pass


class LastAdminError(MembershipServiceError):
    """Raised when trying to remove/demote the last admin."""

    pass


class CrossTenantEmailError(MembershipServiceError):
    """Email already registered to another organisation."""

    pass


class InitialPasswordRequiredError(MembershipServiceError):
    """New users need an initial password for invite."""

    pass


class WorkspaceMembershipService:
    """Service for workspace membership operations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_membership(
        self,
        workspace: Workspace,
        data: WorkspaceMembershipCreate,
    ) -> WorkspaceMembership:
        """Create a new membership in a workspace.
        
        The user must belong to the same tenant as the workspace.
        """
        # Verify user exists and belongs to the same tenant
        user_result = await self.db.execute(
            select(User).where(
                User.id == data.user_id,
                User.tenant_id == workspace.tenant_id,
            )
        )
        user = user_result.scalar_one_or_none()
        if not user:
            raise UserNotFoundError("User not found in tenant")

        membership = WorkspaceMembership(
            tenant_id=workspace.tenant_id,
            workspace_id=workspace.id,
            user_id=data.user_id,
            role=data.role,
        )
        self.db.add(membership)
        try:
            await self.db.commit()
            await self.db.refresh(membership)
            return membership
        except IntegrityError:
            await self.db.rollback()
            raise DuplicateMembershipError("User is already a member of this workspace")

    async def invite_member_by_email(
        self,
        workspace: Workspace,
        email: str,
        role: str,
        full_name: str | None = None,
        initial_password: str | None = None,
    ) -> tuple[WorkspaceMembership, User, bool]:
        """Invite a member by email, creating user if needed.
        
        Returns:
            Tuple of (membership, user, user_created)
            - user_created: True if a new user was created, False if existing
        """
        en = normalize_email(email)
        user_result = await self.db.execute(
            select(User).where(User.email_normalized == en)
        )
        user = user_result.scalar_one_or_none()
        user_created = False

        if user and user.tenant_id != workspace.tenant_id:
            raise CrossTenantEmailError(
                "This email is already registered to another organisation"
            )

        if not user:
            if not initial_password:
                raise InitialPasswordRequiredError(
                    "initial_password is required when creating a new user"
                )
            user = User(
                tenant_id=workspace.tenant_id,
                email=email,
                full_name=full_name,
                password_hash=hash_password(initial_password),
                default_workspace_id=workspace.id,
            )
            self.db.add(user)
            await self.db.flush()  # Get user ID
            user_created = True
        
        # Check if already a member
        existing = await self.db.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace.id,
                WorkspaceMembership.user_id == user.id,
            )
        )
        if existing.scalar_one_or_none():
            raise DuplicateMembershipError(
                f"User {email} is already a member of this workspace"
            )
        
        # Create membership
        membership = WorkspaceMembership(
            tenant_id=workspace.tenant_id,
            workspace_id=workspace.id,
            user_id=user.id,
            role=role,
        )
        self.db.add(membership)
        await self.db.commit()
        await self.db.refresh(membership)
        await self.db.refresh(user)
        
        return membership, user, user_created

    async def get_membership(
        self, workspace_id: str, user_id: str
    ) -> WorkspaceMembership | None:
        """Get a specific membership."""
        result = await self.db.execute(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_membership_by_id(
        self, membership_id: str, workspace_id: str, tenant_id: str
    ) -> WorkspaceMembership | None:
        """Get a membership by its ID, scoped to workspace and tenant."""
        result = await self.db.execute(
            select(WorkspaceMembership)
            .options(joinedload(WorkspaceMembership.user))
            .where(
                WorkspaceMembership.id == membership_id,
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.tenant_id == tenant_id,
            )
        )
        return result.unique().scalar_one_or_none()

    async def list_memberships(
        self, workspace_id: str, tenant_id: str
    ) -> list[WorkspaceMembership]:
        """List all memberships for a workspace, scoped to tenant."""
        result = await self.db.execute(
            select(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.tenant_id == tenant_id,
            )
            .order_by(WorkspaceMembership.created_at)
        )
        return list(result.scalars().all())

    async def list_memberships_with_users(
        self, workspace_id: str, tenant_id: str
    ) -> list[WorkspaceMembership]:
        """List all memberships with user details eagerly loaded."""
        result = await self.db.execute(
            select(WorkspaceMembership)
            .options(joinedload(WorkspaceMembership.user))
            .where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.tenant_id == tenant_id,
            )
            .order_by(WorkspaceMembership.created_at)
        )
        return list(result.unique().scalars().all())

    async def count_admins(self, workspace_id: str, tenant_id: str) -> int:
        """Count the number of admins in a workspace."""
        result = await self.db.execute(
            select(func.count(WorkspaceMembership.id)).where(
                WorkspaceMembership.workspace_id == workspace_id,
                WorkspaceMembership.tenant_id == tenant_id,
                WorkspaceMembership.role == "ADMIN",
            )
        )
        return result.scalar() or 0

    async def update_membership_role(
        self,
        membership_id: str,
        workspace_id: str,
        tenant_id: str,
        new_role: str,
    ) -> WorkspaceMembership:
        """Update a membership's role.
        
        Raises LastAdminError if this would leave the workspace without admins.
        """
        membership = await self.get_membership_by_id(
            membership_id, workspace_id, tenant_id
        )
        if not membership:
            raise MembershipNotFoundError("Membership not found")
        
        # Check if demoting the last admin
        if membership.role == "ADMIN" and new_role != "ADMIN":
            admin_count = await self.count_admins(workspace_id, tenant_id)
            if admin_count <= 1:
                raise LastAdminError(
                    "Cannot change role: this is the last admin in the workspace"
                )
        
        membership.role = new_role
        await self.db.commit()
        await self.db.refresh(membership)
        return membership

    async def remove_membership(
        self,
        membership_id: str,
        workspace_id: str,
        tenant_id: str,
    ) -> WorkspaceMembership:
        """Remove a membership from workspace.
        
        Raises LastAdminError if this would leave the workspace without admins.
        Returns the deleted membership for audit logging.
        """
        membership = await self.get_membership_by_id(
            membership_id, workspace_id, tenant_id
        )
        if not membership:
            raise MembershipNotFoundError("Membership not found")
        
        # Check if removing the last admin
        if membership.role == "ADMIN":
            admin_count = await self.count_admins(workspace_id, tenant_id)
            if admin_count <= 1:
                raise LastAdminError(
                    "Cannot remove: this is the last admin in the workspace"
                )
        
        await self.db.delete(membership)
        await self.db.commit()
        return membership
