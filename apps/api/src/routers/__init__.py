"""API routers for Aiden.ai."""

from src.routers.admin_settings import router as admin_settings_router
from src.routers.agent import router as agent_router
from src.routers.audit import router as audit_router
from src.routers.auth import router as auth_router
from src.routers.cases import router as cases_router
from src.routers.clients import router as clients_router
from src.routers.conversations import router as conversations_router
from src.routers.conversations import conversation_ws
from src.routers.documents import router as documents_router
from src.routers.exports import router as exports_router
from src.routers.global_legal import router as global_legal_router
from src.routers.global_legal import search_router as global_legal_search_router
from src.routers.global_legal import viewer_router as global_legal_viewer_router
from src.routers.global_legal_import import router as global_legal_import_router
from src.routers.operator import router as operator_router
from src.routers.organizations import router as organizations_router
from src.routers.policy import policy_resolve_router
from src.routers.policy import router as policy_router
from src.routers.policy import workspace_policy_router
from src.routers.scraping import router as scraping_router
from src.routers.search import admin_router as search_admin_router
from src.routers.search import router as search_router
from src.routers.soul import router as soul_router
from src.routers.tenants import router as tenants_router
from src.routers.twins import router as twins_router
from src.routers.voice import voice_ws
from src.routers.workflows import router as workflows_router
from src.routers.news import router as news_router
from src.routers.office import router as office_router
from src.routers.workspaces import router as workspaces_router
from src.routers.seed import router as seed_router
from src.routers.wiki import router as wiki_router
from src.routers.wopi import router as wopi_router

__all__ = [
    "admin_settings_router",
    "agent_router",
    "audit_router",
    "auth_router",
    "cases_router",
    "clients_router",
    "conversations_router",
    "conversation_ws",
    "documents_router",
    "exports_router",
    "global_legal_router",
    "global_legal_search_router",
    "global_legal_viewer_router",
    "global_legal_import_router",
    "tenants_router",
    "twins_router",
    "workspaces_router",
    "policy_router",
    "workspace_policy_router",
    "policy_resolve_router",
    "scraping_router",
    "search_router",
    "search_admin_router",
    "workflows_router",
    "operator_router",
    "organizations_router",
    "soul_router",
    "news_router",
    "office_router",
    "voice_ws",
    "seed_router",
    "wiki_router",
    "wopi_router",
]
