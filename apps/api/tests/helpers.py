"""Shared test helpers for Aiden.ai integration tests."""

from httpx import AsyncClient


async def bootstrap_and_login(
    async_client: AsyncClient,
    admin_email: str = "admin@test.com",
    tenant_name: str = "Test Tenant",
) -> tuple[dict, str]:
    """Helper to bootstrap tenant/workspace and get admin token.

    Args:
        async_client: The test HTTP client
        admin_email: Email for the admin user
        tenant_name: Name for the tenant

    Returns:
        Tuple of (bootstrap response data, JWT token)
    """
    bootstrap_response = await async_client.post(
        "/tenants",
        json={
            "name": tenant_name,
            "primary_jurisdiction": "UAE",
            "data_residency_policy": "UAE",
            "bootstrap": {
                "admin_user": {
                    "email": admin_email,
                    "full_name": "Test Admin",
                    "password": "Testpass123",
                },
                "workspace": {"name": f"{tenant_name} Workspace"},
            },
        },
    )
    assert bootstrap_response.status_code == 201, f"Bootstrap failed: {bootstrap_response.text}"
    data = bootstrap_response.json()

    # Login to get token
    login_response = await async_client.post(
        "/auth/dev-login",
        json={
            "tenant_id": data["tenant_id"],
            "workspace_id": data["workspace_id"],
            "email": admin_email,
        },
    )
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    token = login_response.cookies.get("access_token")
    assert token, "Expected access_token cookie from dev-login"

    return data, token
