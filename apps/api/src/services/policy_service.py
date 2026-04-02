"""Policy service for managing policy profiles and resolving policies.

This service handles:
- CRUD operations for policy profiles
- Attaching policy profiles to workspaces
- Resolving the effective policy for a given request context
"""

import logging
from typing import Any

from pydantic import ValidationError
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.dependencies.auth import RequestContext
from src.models.policy_profile import PolicyProfile
from src.models.workspace import Workspace
from src.schemas.policy import (
    PolicyConfig,
    PolicyProfileCreate,
    PolicyProfileUpdate,
    ResolvedPolicy,
)

logger = logging.getLogger(__name__)


class PolicyProfileNotFoundError(Exception):
    """Raised when a policy profile is not found."""

    pass


class PolicyProfileNameExistsError(Exception):
    """Raised when a policy profile name already exists in the tenant."""

    pass


class PolicyProfileNotInTenantError(Exception):
    """Raised when trying to attach a policy profile from another tenant."""

    pass


class WorkspaceNotFoundError(Exception):
    """Raised when a workspace is not found."""

    pass


# Built-in safe default policy (deny by default - minimal allowlist)
BUILTIN_DEFAULT_POLICY = PolicyConfig(
    allowed_workflows=[],  # No workflows allowed by default
    allowed_input_languages=["en"],  # English only
    allowed_output_languages=["en"],  # English only
    allowed_jurisdictions=["UAE"],  # UAE only (safe default)
    feature_flags={
        "law_firm_mode": False,
        "advanced_analytics": False,
    },
)


class PolicyService:
    """Service for managing policy profiles and resolving policies."""

    def __init__(self, db: AsyncSession):
        """Initialize the policy service.

        Args:
            db: Async database session
        """
        self.db = db

    # =========================================================================
    # Policy Profile CRUD
    # =========================================================================

    async def create_policy_profile(
        self,
        tenant_id: str,
        data: PolicyProfileCreate,
    ) -> PolicyProfile:
        """Create a new policy profile.

        Args:
            tenant_id: The tenant ID to create the profile for
            data: Policy profile creation data

        Returns:
            The created PolicyProfile

        Raises:
            PolicyProfileNameExistsError: If name already exists in tenant
        """
        # Check for duplicate name
        existing = await self.db.execute(
            select(PolicyProfile).where(
                and_(
                    PolicyProfile.tenant_id == tenant_id,
                    PolicyProfile.name == data.name,
                )
            )
        )
        if existing.scalar_one_or_none():
            raise PolicyProfileNameExistsError(
                f"Policy profile '{data.name}' already exists in tenant"
            )

        # If setting as default, unset any existing default
        if data.is_default:
            await self._unset_tenant_default(tenant_id)

        # Create the profile
        policy_profile = PolicyProfile(
            tenant_id=tenant_id,
            name=data.name,
            description=data.description,
            config=data.config.model_dump(),
            is_default=data.is_default,
        )
        self.db.add(policy_profile)
        await self.db.commit()
        await self.db.refresh(policy_profile)
        return policy_profile

    async def get_policy_profile(
        self,
        tenant_id: str,
        policy_id: str,
    ) -> PolicyProfile:
        """Get a policy profile by ID.

        Args:
            tenant_id: The tenant ID
            policy_id: The policy profile ID

        Returns:
            The PolicyProfile

        Raises:
            PolicyProfileNotFoundError: If not found or not in tenant
        """
        result = await self.db.execute(
            select(PolicyProfile).where(
                and_(
                    PolicyProfile.id == policy_id,
                    PolicyProfile.tenant_id == tenant_id,
                )
            )
        )
        profile = result.scalar_one_or_none()
        if not profile:
            raise PolicyProfileNotFoundError(
                f"Policy profile '{policy_id}' not found"
            )
        return profile

    async def list_policy_profiles(
        self,
        tenant_id: str,
    ) -> list[PolicyProfile]:
        """List all policy profiles for a tenant.

        Args:
            tenant_id: The tenant ID

        Returns:
            List of PolicyProfile objects
        """
        result = await self.db.execute(
            select(PolicyProfile)
            .where(PolicyProfile.tenant_id == tenant_id)
            .order_by(PolicyProfile.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_policy_profile(
        self,
        tenant_id: str,
        policy_id: str,
        data: PolicyProfileUpdate,
    ) -> PolicyProfile:
        """Update a policy profile.

        Args:
            tenant_id: The tenant ID
            policy_id: The policy profile ID
            data: Update data

        Returns:
            The updated PolicyProfile

        Raises:
            PolicyProfileNotFoundError: If not found
            PolicyProfileNameExistsError: If new name conflicts
        """
        profile = await self.get_policy_profile(tenant_id, policy_id)

        # Check name uniqueness if changing
        if data.name is not None and data.name != profile.name:
            existing = await self.db.execute(
                select(PolicyProfile).where(
                    and_(
                        PolicyProfile.tenant_id == tenant_id,
                        PolicyProfile.name == data.name,
                        PolicyProfile.id != policy_id,
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise PolicyProfileNameExistsError(
                    f"Policy profile '{data.name}' already exists in tenant"
                )
            profile.name = data.name

        if data.description is not None:
            profile.description = data.description

        if data.config is not None:
            profile.config = data.config.model_dump()

        if data.is_default is not None:
            if data.is_default and not profile.is_default:
                # Setting as new default, unset existing
                await self._unset_tenant_default(tenant_id)
            profile.is_default = data.is_default

        await self.db.commit()
        await self.db.refresh(profile)
        return profile

    async def _unset_tenant_default(self, tenant_id: str) -> None:
        """Unset any existing default policy profile for the tenant."""
        result = await self.db.execute(
            select(PolicyProfile).where(
                and_(
                    PolicyProfile.tenant_id == tenant_id,
                    PolicyProfile.is_default == True,  # noqa: E712
                )
            )
        )
        for profile in result.scalars().all():
            profile.is_default = False

    # =========================================================================
    # Workspace Policy Attachment
    # =========================================================================

    async def attach_policy_to_workspace(
        self,
        tenant_id: str,
        workspace_id: str,
        policy_profile_id: str,
    ) -> Workspace:
        """Attach a policy profile to a workspace.

        Args:
            tenant_id: The tenant ID
            workspace_id: The workspace ID
            policy_profile_id: The policy profile ID to attach

        Returns:
            The updated Workspace

        Raises:
            WorkspaceNotFoundError: If workspace not found
            PolicyProfileNotFoundError: If policy profile not found
            PolicyProfileNotInTenantError: If policy profile not in tenant
        """
        # Verify workspace exists and belongs to tenant
        ws_result = await self.db.execute(
            select(Workspace).where(
                and_(
                    Workspace.id == workspace_id,
                    Workspace.tenant_id == tenant_id,
                )
            )
        )
        workspace = ws_result.scalar_one_or_none()
        if not workspace:
            raise WorkspaceNotFoundError(f"Workspace '{workspace_id}' not found")

        # Verify policy profile exists and belongs to tenant
        pp_result = await self.db.execute(
            select(PolicyProfile).where(PolicyProfile.id == policy_profile_id)
        )
        policy_profile = pp_result.scalar_one_or_none()
        if not policy_profile:
            raise PolicyProfileNotFoundError(
                f"Policy profile '{policy_profile_id}' not found"
            )
        if policy_profile.tenant_id != tenant_id:
            raise PolicyProfileNotInTenantError(
                "Policy profile does not belong to this tenant"
            )

        # Attach
        workspace.policy_profile_id = policy_profile_id
        await self.db.commit()
        await self.db.refresh(workspace)
        return workspace

    # =========================================================================
    # Policy Resolution
    # =========================================================================

    async def resolve(
        self,
        ctx: RequestContext,
        workflow_name: str | None = None,
    ) -> ResolvedPolicy:
        """Resolve the effective policy for a given request context.

        Resolution order:
        1. If workspace has policy_profile_id set -> use that
        2. Else if tenant has a default policy (is_default=True) -> use that
        3. Else use safe built-in default policy (deny by default)

        Args:
            ctx: The request context with tenant/workspace info
            workflow_name: Optional workflow name to check against allowlist

        Returns:
            ResolvedPolicy with effective configuration and workflow decision
        """
        policy_profile: PolicyProfile | None = None
        source: str = "builtin_default"
        policy_config: PolicyConfig = BUILTIN_DEFAULT_POLICY
        profile_name: str = "Built-in Default (Restrictive)"
        profile_id: str | None = None

        # Step 1: Check workspace-level policy
        if ctx.workspace and ctx.workspace.policy_profile_id:
            result = await self.db.execute(
                select(PolicyProfile).where(
                    PolicyProfile.id == ctx.workspace.policy_profile_id
                )
            )
            policy_profile = result.scalar_one_or_none()
            if policy_profile:
                source = "workspace"

        # Step 2: Fall back to tenant default
        if not policy_profile:
            result = await self.db.execute(
                select(PolicyProfile).where(
                    and_(
                        PolicyProfile.tenant_id == ctx.tenant.id,
                        PolicyProfile.is_default == True,  # noqa: E712
                    )
                )
            )
            policy_profile = result.scalar_one_or_none()
            if policy_profile:
                source = "tenant_default"

        # Parse config if we found a profile
        if policy_profile:
            profile_id = policy_profile.id
            profile_name = policy_profile.name
            try:
                policy_config = PolicyConfig.model_validate(policy_profile.config)
            except ValidationError as e:
                logger.warning(
                    f"Invalid policy config in profile {policy_profile.id}: {e}"
                )
                # Fall back to builtin on validation error
                policy_config = BUILTIN_DEFAULT_POLICY
                source = "builtin_default"
                profile_name = "Built-in Default (Config Error)"
                profile_id = None

        # Step 3: Check workflow allowlist
        workflow_allowed = True
        workflow_denied_reason: str | None = None

        if workflow_name is not None:
            if workflow_name not in policy_config.allowed_workflows:
                workflow_allowed = False
                workflow_denied_reason = (
                    f"Workflow '{workflow_name}' is not in the allowed workflows list. "
                    f"Allowed: {policy_config.allowed_workflows}"
                )

        return ResolvedPolicy(
            policy_profile_id=profile_id,
            policy_profile_name=profile_name,
            source=source,  # type: ignore[arg-type]
            config=policy_config,
            workflow_allowed=workflow_allowed,
            workflow_denied_reason=workflow_denied_reason,
        )

    async def get_tenant_default_profile(
        self,
        tenant_id: str,
    ) -> PolicyProfile | None:
        """Get the default policy profile for a tenant.

        Args:
            tenant_id: The tenant ID

        Returns:
            The default PolicyProfile or None
        """
        result = await self.db.execute(
            select(PolicyProfile).where(
                and_(
                    PolicyProfile.tenant_id == tenant_id,
                    PolicyProfile.is_default == True,  # noqa: E712
                )
            )
        )
        return result.scalar_one_or_none()
