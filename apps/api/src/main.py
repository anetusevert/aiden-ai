"""HeyAmin API - FastAPI application."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.middleware import RequestIdMiddleware
from src.routers import (
    admin_settings_router,
    agent_router,
    audit_router,
    auth_router,
    cases_router,
    clients_router,
    conversation_ws,
    conversations_router,
    documents_router,
    exports_router,
    global_legal_import_router,
    global_legal_router,
    news_router,
    office_router,
    operator_router,
    organizations_router,
    global_legal_search_router,
    global_legal_viewer_router,
    policy_resolve_router,
    policy_router,
    scraping_router,
    search_admin_router,
    search_router,
    seed_router,
    soul_router,
    tenants_router,
    twins_router,
    voice_ws,
    wiki_router,
    workflows_router,
    workspace_policy_router,
    workspaces_router,
    wopi_router,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan context manager.

    Runs on application startup and shutdown.

    Startup tasks:
    - Platform admin bootstrap (if PLATFORM_ADMIN_EMAIL is set)
    """
    # === STARTUP ===
    logger.info(
        "Application starting",
        extra={
            "environment": settings.environment,
            "platform_admin_email_configured": bool(settings.platform_admin_email),
        },
    )

    # Platform admin bootstrap
    if settings.platform_admin_email:
        try:
            from src.database import async_session_maker
            from src.services.platform_admin_bootstrap import bootstrap_platform_admin

            async with async_session_maker() as db:
                result = await bootstrap_platform_admin(db)
                logger.info(
                    f"Platform admin bootstrap: {result['action']}",
                    extra=result,
                )
        except Exception as e:
            # Log but don't crash - bootstrap is non-critical
            logger.error(
                f"Platform admin bootstrap failed: {e}",
                exc_info=True,
            )

    # Scraping sources bootstrap
    try:
        from src.database import async_session_maker as _asm
        from src.services.scraping_bootstrap import bootstrap_scraping_sources

        async with _asm() as _sdb:
            scraping_result = await bootstrap_scraping_sources(_sdb)
            logger.info(
                "Scraping sources bootstrap: %s",
                scraping_result.get("action", "unknown"),
                extra=scraping_result,
            )
    except Exception as e:
        logger.error("Scraping sources bootstrap failed: %s", e, exc_info=True)

    # Start Amin background scheduler (dream cycles + scraping)
    from src.services.agent.scheduler import AminScheduler

    amin_scheduler = AminScheduler()
    await amin_scheduler.start()

    yield

    # === SHUTDOWN ===
    await amin_scheduler.stop()
    logger.info("Application shutting down")


app = FastAPI(
    title="HeyAmin API",
    description="AI-powered application backend",
    version="0.1.0",
    root_path=settings.api_root_path,
    lifespan=lifespan,
)

# Request ID middleware (must be added before other middleware)
app.add_middleware(RequestIdMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_origin_regex=settings.effective_cors_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(admin_settings_router)
app.include_router(agent_router)
app.include_router(auth_router)
app.include_router(operator_router)
app.include_router(tenants_router)
app.include_router(workspaces_router)
app.include_router(audit_router)
app.include_router(policy_router)
app.include_router(workspace_policy_router)
app.include_router(policy_resolve_router)
app.include_router(documents_router)
app.include_router(search_router)
app.include_router(search_admin_router)
app.include_router(workflows_router)
app.include_router(exports_router)
app.include_router(global_legal_router)
app.include_router(global_legal_search_router)
app.include_router(global_legal_viewer_router)
app.include_router(global_legal_import_router)
app.include_router(conversations_router)
app.include_router(twins_router)
app.include_router(soul_router)
app.include_router(organizations_router)
app.include_router(scraping_router)
app.include_router(news_router)
app.include_router(office_router)
app.include_router(clients_router)
app.include_router(cases_router)
app.include_router(seed_router)
app.include_router(wiki_router)
app.include_router(wopi_router)

# WebSocket route for streaming Amin responses
app.websocket("/ws/conversations/{conversation_id}")(conversation_ws)

# WebSocket route for voice (OpenAI Realtime proxy)
app.websocket("/ws/voice/{conversation_id}")(voice_ws)
app.websocket("/ws/voice")(voice_ws)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint.

    Returns status and environment for monitoring/debugging.
    """
    return {"status": "ok", "environment": settings.environment}


@app.get("/llm/status")
async def llm_status():
    """LLM provider status endpoint (dev only).

    Returns the active LLM provider configuration for diagnostics.
    Only available in dev environment.

    Response includes:
    - provider: Active provider name ("stub" or "openai")
    - model: Active model name
    - configured_provider: What LLM_PROVIDER is set to
    - api_key_set: Whether LLM_API_KEY is set (boolean, not the actual key)
    - environment: Current environment
    - is_fallback: Whether we fell back from OpenAI to Stub
    """
    from fastapi import HTTPException

    from src.llm.providers import get_llm_status

    # Only available in dev environment
    if settings.environment != "dev":
        raise HTTPException(
            status_code=404,
            detail="This endpoint is only available in dev environment",
        )

    return get_llm_status()


@app.get("/cors-check")
async def cors_check():
    """Diagnostic endpoint for verifying CORS configuration.

    No auth required. Curl with an Origin header to see if the
    response includes Access-Control-Allow-Origin:

        curl -i https://<api>/cors-check -H "Origin: https://<web>"
    """
    regex = settings.effective_cors_origin_regex
    return {
        "environment": settings.environment,
        "allow_origins": settings.cors_origins,
        "allow_origin_regex": regex,
        "hint": "Check the response headers for Access-Control-Allow-Origin",
    }


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"message": "Welcome to HeyAmin API"}
