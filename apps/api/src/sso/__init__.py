"""SSO (Single Sign-On) integration boundary.

This module provides the interface for enterprise SSO integration.
Currently a placeholder for future OIDC/SAML implementation.

FUTURE INTEGRATION NOTES
========================

When implementing enterprise SSO:

1. Configuration (add to config.py):
   - SSO_ENABLED: bool = False
   - SSO_PROVIDER: str = "oidc"  # or "saml"
   - SSO_ISSUER_URL: str = ""
   - SSO_CLIENT_ID: str = ""
   - SSO_CLIENT_SECRET: str = ""
   - SSO_REDIRECT_URI: str = ""

2. Endpoints to add:
   - GET /auth/sso/login - Redirect to IdP
   - GET /auth/sso/callback - Handle IdP response
   - POST /auth/sso/logout - OIDC logout

3. User provisioning strategy:
   - JIT (Just-In-Time): Create users on first SSO login
   - SCIM: Sync users from IdP directory
   - Manual: Require pre-created users

4. Tenant/workspace mapping:
   - Option A: Tenant per IdP (single-tenant mode)
   - Option B: Multi-tenant with tenant claim in IdP token
   - Option C: Domain-based tenant lookup

5. Role mapping:
   - Map IdP groups/roles to Aiden ADMIN/EDITOR/VIEWER
   - Store mappings in tenant configuration

Example future interface:
```python
from abc import ABC, abstractmethod

class SSOProvider(ABC):
    @abstractmethod
    async def get_authorization_url(self, state: str) -> str:
        '''Get IdP authorization URL for redirect.'''
        pass

    @abstractmethod
    async def exchange_code(self, code: str) -> SSOUserInfo:
        '''Exchange authorization code for user info.'''
        pass

    @abstractmethod
    async def validate_token(self, token: str) -> SSOUserInfo:
        '''Validate IdP token and extract user info.'''
        pass

class OIDCProvider(SSOProvider):
    '''OpenID Connect provider implementation.'''
    pass

class SAMLProvider(SSOProvider):
    '''SAML 2.0 provider implementation.'''
    pass
```
"""

from dataclasses import dataclass


@dataclass
class SSOUserInfo:
    """User information returned from SSO provider.

    This structure represents the normalized user data
    extracted from IdP tokens (OIDC id_token or SAML assertion).
    """

    # Core identity
    sub: str  # Subject identifier from IdP
    email: str
    email_verified: bool = False

    # Profile info
    name: str | None = None
    given_name: str | None = None
    family_name: str | None = None

    # Tenant mapping (if provided by IdP)
    tenant_id: str | None = None

    # Roles/groups from IdP (for role mapping)
    groups: list[str] | None = None
    roles: list[str] | None = None


@dataclass
class SSOConfig:
    """Configuration for SSO provider.

    Placeholder for future SSO configuration.
    """

    enabled: bool = False
    provider: str = "oidc"  # "oidc" or "saml"
    issuer_url: str = ""
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = ""

    # Role mapping
    admin_groups: list[str] | None = None
    editor_groups: list[str] | None = None
    viewer_groups: list[str] | None = None


# Placeholder function for future SSO validation
async def validate_sso_token(token: str) -> SSOUserInfo:
    """Validate SSO token and return user info.

    NOT IMPLEMENTED - Placeholder for future SSO integration.

    Raises:
        NotImplementedError: SSO is not yet implemented
    """
    raise NotImplementedError(
        "SSO integration is not yet implemented. "
        "Use JWT auth (/auth/dev-login) for development."
    )


def is_sso_enabled() -> bool:
    """Check if SSO is enabled.

    Returns False until SSO is implemented.
    """
    return False
