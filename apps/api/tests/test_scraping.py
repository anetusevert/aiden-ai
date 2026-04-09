"""Tests for scraping operator access and job detail payloads."""

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from src.models.scraping_job import ScrapingJob
from src.models.scraping_source import ScrapingSource


@pytest.mark.integration
class TestScrapingOperatorAccess:
    """Workspace admins should be able to use the scraping console."""

    @pytest.mark.asyncio
    async def test_workspace_admin_can_list_scraping_sources(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ) -> None:
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Scraping Access Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {
                        "email": "admin@scraping-access.test",
                        "full_name": "Scraping Admin",
                        "password": "Testpass123",
                    },
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@scraping-access.test",
            },
        )
        cookies = {"access_token": login.cookies["access_token"]}

        response = await async_client.get(
            "/operator/scraping/sources",
            cookies=cookies,
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_job_detail_includes_run_log_for_workspace_admin(
        self,
        async_client: AsyncClient,
        clean_db: AsyncSession,
    ) -> None:
        bootstrap = await async_client.post(
            "/tenants",
            json={
                "name": "Scraping Detail Tenant",
                "primary_jurisdiction": "UAE",
                "data_residency_policy": "UAE",
                "bootstrap": {
                    "admin_user": {
                        "email": "admin@scraping-detail.test",
                        "full_name": "Scraping Detail Admin",
                        "password": "Testpass123",
                    },
                    "workspace": {"name": "Main"},
                },
            },
        )
        data = bootstrap.json()

        login = await async_client.post(
            "/auth/dev-login",
            json={
                "tenant_id": data["tenant_id"],
                "workspace_id": data["workspace_id"],
                "email": "admin@scraping-detail.test",
            },
        )
        cookies = {"access_token": login.cookies["access_token"]}

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
