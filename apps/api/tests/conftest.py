"""Pytest configuration and fixtures."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.config import settings
from src.database import Base, get_db
from src.main import app
from src.models import (
    AuditLog,
    Document,
    DocumentChunk,
    DocumentChunkEmbedding,
    DocumentText,
    DocumentVersion,
    PolicyProfile,
    RefreshSession,
    Tenant,
    User,
    Workspace,
    WorkspaceMembership,
)

# Test database URL - use the test database
TEST_DATABASE_URL = settings.test_database_url.replace(
    "postgresql://", "postgresql+asyncpg://"
)

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Test session factory
TestSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_database() -> AsyncGenerator[None, None]:
    """Create test database tables once per session."""
    # Create the test database if it doesn't exist
    # Connect to default postgres database first
    admin_url = settings.database_url.replace(
        "postgresql://", "postgresql+asyncpg://"
    ).replace("/aiden", "/postgres")
    admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")

    async with admin_engine.connect() as conn:
        # Check if test database exists
        result = await conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'aiden_test'")
        )
        exists = result.scalar()
        if not exists:
            await conn.execute(text("CREATE DATABASE aiden_test"))

    await admin_engine.dispose()

    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Drop all tables after tests
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await test_engine.dispose()


@pytest.fixture
async def db_session(
    setup_database: None,
) -> AsyncGenerator[AsyncSession, None]:
    """Provide a clean database session for each test."""
    async with TestSessionLocal() as session:
        yield session
        # Rollback any uncommitted changes
        await session.rollback()


@pytest.fixture
async def clean_db(db_session: AsyncSession) -> AsyncGenerator[AsyncSession, None]:
    """Clean database before each test and provide session."""
    # Clean all tables in reverse order of dependencies
    await db_session.execute(text("DELETE FROM audit_logs"))
    await db_session.execute(text("DELETE FROM document_chunk_embeddings"))
    await db_session.execute(text("DELETE FROM document_chunks"))
    await db_session.execute(text("DELETE FROM document_texts"))
    await db_session.execute(text("DELETE FROM document_versions"))
    await db_session.execute(text("DELETE FROM documents"))
    # Clean global legal corpus tables
    await db_session.execute(text("DELETE FROM legal_chunk_embeddings"))
    await db_session.execute(text("DELETE FROM legal_chunks"))
    await db_session.execute(text("DELETE FROM legal_texts"))
    await db_session.execute(text("DELETE FROM legal_instrument_versions"))
    await db_session.execute(text("DELETE FROM legal_instruments"))
    await db_session.execute(text("DELETE FROM workspace_memberships"))
    await db_session.execute(text("DELETE FROM refresh_sessions"))
    # Set policy_profile_id to NULL before deleting policy_profiles
    await db_session.execute(text("UPDATE workspaces SET policy_profile_id = NULL"))
    await db_session.execute(text("DELETE FROM policy_profiles"))
    await db_session.execute(text("DELETE FROM users"))
    await db_session.execute(text("DELETE FROM workspaces"))
    await db_session.execute(text("DELETE FROM tenants"))
    await db_session.commit()
    yield db_session


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override database dependency for tests."""
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture
def client() -> TestClient:
    """Create a test client for the FastAPI app."""
    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(setup_database: None) -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client."""
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


# Fixture factories for test data


@pytest.fixture
async def tenant_factory(clean_db: AsyncSession) -> Any:
    """Factory for creating tenants."""

    async def create_tenant(
        name: str = "Test Tenant",
        primary_jurisdiction: str = "UAE",
        data_residency_policy: str = "UAE",
    ) -> Tenant:
        tenant = Tenant(
            name=name,
            primary_jurisdiction=primary_jurisdiction,
            data_residency_policy=data_residency_policy,
        )
        clean_db.add(tenant)
        await clean_db.commit()
        await clean_db.refresh(tenant)
        return tenant

    return create_tenant


@pytest.fixture
async def workspace_factory(clean_db: AsyncSession) -> Any:
    """Factory for creating workspaces."""

    async def create_workspace(
        tenant: Tenant,
        name: str = "Test Workspace",
        workspace_type: str = "IN_HOUSE",
        jurisdiction_profile: str = "UAE_DEFAULT",
        default_language: str = "en",
    ) -> Workspace:
        workspace = Workspace(
            tenant_id=tenant.id,
            name=name,
            workspace_type=workspace_type,
            jurisdiction_profile=jurisdiction_profile,
            default_language=default_language,
        )
        clean_db.add(workspace)
        await clean_db.commit()
        await clean_db.refresh(workspace)
        return workspace

    return create_workspace


@pytest.fixture
async def user_factory(clean_db: AsyncSession) -> Any:
    """Factory for creating users."""

    async def create_user(
        tenant: Tenant,
        email: str = "test@example.com",
        full_name: str | None = "Test User",
    ) -> User:
        user = User(
            tenant_id=tenant.id,
            email=email,
            full_name=full_name,
        )
        clean_db.add(user)
        await clean_db.commit()
        await clean_db.refresh(user)
        return user

    return create_user


@pytest.fixture
async def membership_factory(clean_db: AsyncSession) -> Any:
    """Factory for creating workspace memberships."""

    async def create_membership(
        workspace: Workspace,
        user: User,
        role: str = "ADMIN",
    ) -> WorkspaceMembership:
        membership = WorkspaceMembership(
            tenant_id=workspace.tenant_id,
            workspace_id=workspace.id,
            user_id=user.id,
            role=role,
        )
        clean_db.add(membership)
        await clean_db.commit()
        await clean_db.refresh(membership)
        return membership

    return create_membership


@pytest.fixture
async def policy_profile_factory(clean_db: AsyncSession) -> Any:
    """Factory for creating policy profiles."""

    async def create_policy_profile(
        tenant: Tenant,
        name: str = "Test Policy",
        description: str | None = None,
        config: dict | None = None,
        is_default: bool = False,
    ) -> PolicyProfile:
        if config is None:
            config = {
                "allowed_workflows": ["CONTRACT_REVIEW_V1"],
                "allowed_input_languages": ["en", "ar"],
                "allowed_output_languages": ["en"],
                "allowed_jurisdictions": ["UAE", "DIFC"],
                "feature_flags": {"law_firm_mode": False},
                "retrieval": {"max_chunks": 12},
                "generation": {"require_citations": True},
            }
        policy_profile = PolicyProfile(
            tenant_id=tenant.id,
            name=name,
            description=description,
            config=config,
            is_default=is_default,
        )
        clean_db.add(policy_profile)
        await clean_db.commit()
        await clean_db.refresh(policy_profile)
        return policy_profile

    return create_policy_profile
