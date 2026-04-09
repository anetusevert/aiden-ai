"""Tests for scraping operator access and job lifecycle behavior."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.scraping_job import ScrapingJob
from src.models.scraping_source import ScrapingSource


@pytest.fixture
async def platform_admin_with_workspace(
    clean_db: AsyncSession,
    tenant_factory,
    user_factory,
    workspace_factory,
    membership_factory,
):
    tenant = await tenant_factory(name="Scraping Platform Tenant")
    workspace = await workspace_factory(tenant, name="Control Center")
    user = await user_factory(tenant, email="platform-admin@scraping.test")
    user.is_platform_admin = True
    await clean_db.commit()
    await membership_factory(workspace, user, role="ADMIN")
    await clean_db.refresh(user)
    return tenant, workspace, user


@pytest.fixture
async def workspace_admin_with_workspace(
    clean_db: AsyncSession,
    tenant_factory,
    user_factory,
    workspace_factory,
    membership_factory,
):
    tenant = await tenant_factory(name="Scraping Workspace Tenant")
    workspace = await workspace_factory(tenant, name="Workspace Admin")
    user = await user_factory(tenant, email="workspace-admin@scraping.test")
    await clean_db.commit()
    await membership_factory(workspace, user, role="ADMIN")
    await clean_db.refresh(user)
    return tenant, workspace, user


async def login_cookies(
    async_client: AsyncClient,
    tenant_id: str,
    workspace_id: str,
    email: str,
) -> dict[str, str]:
    response = await async_client.post(
        "/auth/dev-login",
        json={
            "tenant_id": tenant_id,
            "workspace_id": workspace_id,
            "email": email,
        },
    )
    assert response.status_code == 200
    return {"access_token": response.cookies["access_token"]}


@pytest.mark.integration
class TestScrapingOperatorAccess:
    """Scraping control-center APIs are platform-admin only."""

    @pytest.mark.asyncio
    async def test_platform_admin_can_list_scraping_sources(
        self,
        async_client: AsyncClient,
        platform_admin_with_workspace,
    ) -> None:
        tenant, workspace, user = platform_admin_with_workspace
        cookies = await login_cookies(
            async_client,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            email=user.email,
        )

        response = await async_client.get(
            "/operator/scraping/sources",
            cookies=cookies,
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_workspace_admin_is_forbidden_from_scraping_operator(
        self,
        async_client: AsyncClient,
        workspace_admin_with_workspace,
    ) -> None:
        tenant, workspace, user = workspace_admin_with_workspace
        cookies = await login_cookies(
            async_client,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            email=user.email,
        )

        response = await async_client.get("/operator/scraping/sources", cookies=cookies)

        assert response.status_code == 403
        payload = response.json()
        assert payload["detail"]["error_code"] == "platform_admin_required"

    @pytest.mark.asyncio
    async def test_job_detail_includes_run_log_for_platform_admin(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
        platform_admin_with_workspace,
    ) -> None:
        tenant, workspace, user = platform_admin_with_workspace
        cookies = await login_cookies(
            async_client,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            email=user.email,
        )
        source = ScrapingSource(
            connector_name="ksa_boe",
            display_name="KSA Bureau of Experts",
            jurisdiction="KSA",
            source_url="https://laws.boe.gov.sa",
            enabled=True,
            harvest_limit=25,
        )
        clean_db.add(source)
        await clean_db.flush()

        job = ScrapingJob(
            source_id=source.id,
            connector_name=source.connector_name,
            status="completed",
            triggered_by="manual",
            items_listed=2,
            items_upserted=1,
            items_failed=1,
            run_log=[
                {"source_url": "https://example.test/ok", "result": "ok"},
                {
                    "url": "https://example.test/fail",
                    "status": "error",
                    "error": "Parser failed",
                },
            ],
        )
        clean_db.add(job)
        await clean_db.commit()
        await clean_db.refresh(job)

        response = await async_client.get(
            f"/operator/scraping/jobs/{job.id}",
            cookies=cookies,
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == job.id
        assert payload["run_log"][0]["source_url"] == "https://example.test/ok"
        assert payload["run_log"][0]["result"] == "ok"
        assert payload["run_log"][1]["result"] == "error"
        assert payload["run_log"][1]["error"] == "Parser failed"

    @pytest.mark.asyncio
    async def test_trigger_rejects_when_pending_job_exists(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
        platform_admin_with_workspace,
    ) -> None:
        tenant, workspace, user = platform_admin_with_workspace
        cookies = await login_cookies(
            async_client,
            tenant_id=tenant.id,
            workspace_id=workspace.id,
            email=user.email,
        )

        source = ScrapingSource(
            connector_name="ksa_boe",
            display_name="KSA Bureau of Experts",
            jurisdiction="KSA",
            source_url="https://laws.boe.gov.sa",
            enabled=True,
            harvest_limit=25,
        )
        clean_db.add(source)
        await clean_db.flush()

        job = ScrapingJob(
            source_id=source.id,
            connector_name=source.connector_name,
            status="pending",
            triggered_by="manual",
        )
        clean_db.add(job)
        await clean_db.commit()

        response = await async_client.post(
            f"/operator/scraping/sources/{source.id}/trigger",
            cookies=cookies,
        )

        assert response.status_code == 409
        assert "queued or running" in response.json()["detail"]
