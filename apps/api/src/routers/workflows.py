"""Workflow endpoints for Aiden.ai.

This module contains endpoints for executing AI-powered workflows
with policy enforcement, citation validation, and audit logging.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.database import get_db
from src.dependencies import RequestContext, require_editor, require_viewer
from src.dependencies.policy import require_workflow_allowed
from src.llm import LLMProvider, get_llm_provider
from src.middleware.request_id import get_request_id
from src.schemas.clause_redlines import (
    ClauseRedlinesRequest,
    ClauseRedlinesResponse,
)
from src.schemas.contract_review import (
    ContractReviewRequest,
    ContractReviewResponse,
)
from src.schemas.policy import ResolvedPolicy
from src.schemas.research import (
    LegalResearchRequest,
    LegalResearchResponse,
    ResearchFilters,
)
from src.services import log_audit_event
from src.services.clause_redlines_service import (
    WORKFLOW_NAME as CLAUSE_REDLINES_WORKFLOW,
    ClauseRedlinesService,
)
from src.services.contract_review_service import (
    WORKFLOW_NAME as CONTRACT_REVIEW_WORKFLOW,
    ContractReviewService,
)
from src.services.research_service import WORKFLOW_NAME, ResearchService
from src.utils.hashing import hash_question

router = APIRouter(prefix="/workflows", tags=["workflows"])


# =============================================================================
# Legal Research Workflow
# =============================================================================


@router.post(
    "/legal-research",
    response_model=LegalResearchResponse,
    summary="Execute legal research workflow",
    description="""
Research a legal question using your document workspace.

This workflow:
1. Retrieves relevant document chunks from your workspace
2. Generates a cited answer using an LLM
3. Returns the answer with structured citations

**Policy enforcement**: Requires LEGAL_RESEARCH_V1 to be in the workspace's allowed_workflows.

**Role required**: VIEWER or higher (read-only access is sufficient).

**Citations**: The answer includes inline citations [1], [2], etc. that map to the evidence chunks.

**Insufficient sources**: If fewer than 3 relevant chunks are found, returns a message indicating
insufficient sources rather than attempting to generate an unreliable answer.
""",
)
async def legal_research(
    request: Request,
    body: LegalResearchRequest,
    ctx: Annotated[RequestContext, Depends(require_viewer())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> LegalResearchResponse:
    """Execute legal research workflow with cited answers.

    This endpoint:
    1. Enforces policy (LEGAL_RESEARCH_V1 must be allowed)
    2. Retrieves relevant chunks from the document vault
    3. Generates a cited answer using an LLM
    4. Validates citations and returns structured response

    The answer includes inline citations [1], [2], etc. that map to
    the returned evidence chunks.
    """
    request_id = get_request_id(request)

    try:
        # Policy enforcement
        resolved_policy = await require_workflow_allowed(ctx, WORKFLOW_NAME, db)

        # Validate jurisdiction filter against policy
        if body.filters and body.filters.jurisdiction:
            allowed_jurisdictions = resolved_policy.config.allowed_jurisdictions
            if (
                allowed_jurisdictions
                and body.filters.jurisdiction not in allowed_jurisdictions
            ):
                await log_audit_event(
                    db=db,
                    ctx=ctx,
                    action="workflow.run.fail",
                    status="fail",
                    resource_type="workflow",
                    meta={
                        "workflow_name": WORKFLOW_NAME,
                        "reason": "jurisdiction_not_allowed",
                        "requested_jurisdiction": body.filters.jurisdiction,
                        "question_hash": hash_question(body.question),
                    },
                    request=request,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Jurisdiction '{body.filters.jurisdiction}' is not allowed by policy. "
                    f"Allowed: {allowed_jurisdictions}",
                )

        # Validate language filter against policy
        if body.filters and body.filters.language:
            allowed_languages = resolved_policy.config.allowed_input_languages
            if allowed_languages and body.filters.language not in allowed_languages:
                await log_audit_event(
                    db=db,
                    ctx=ctx,
                    action="workflow.run.fail",
                    status="fail",
                    resource_type="workflow",
                    meta={
                        "workflow_name": WORKFLOW_NAME,
                        "reason": "language_not_allowed",
                        "requested_language": body.filters.language,
                        "question_hash": hash_question(body.question),
                    },
                    request=request,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Language '{body.filters.language}' is not allowed by policy. "
                    f"Allowed: {allowed_languages}",
                )

        # Validate output language against policy
        allowed_output_languages = resolved_policy.config.allowed_output_languages
        if (
            allowed_output_languages
            and body.output_language not in allowed_output_languages
        ):
            await log_audit_event(
                db=db,
                ctx=ctx,
                action="workflow.run.fail",
                status="fail",
                resource_type="workflow",
                meta={
                    "workflow_name": WORKFLOW_NAME,
                    "reason": "output_language_not_allowed",
                    "requested_output_language": body.output_language,
                    "question_hash": hash_question(body.question),
                },
                request=request,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Output language '{body.output_language}' is not allowed by policy. "
                f"Allowed: {allowed_output_languages}",
            )

        # Execute research
        service = ResearchService(db)
        response = await service.answer_question(
            ctx,
            body.question,
            limit=body.limit,
            filters=body.filters,
            output_language=body.output_language,
            request_id=request_id,
            evidence_scope=body.evidence_scope,
        )

        # Audit log success
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workflow.run.success",
            status="success",
            resource_type="workflow",
            meta={
                "workflow_name": WORKFLOW_NAME,
                "result_status": response.meta.status.value,
                "chunk_count": response.meta.chunk_count,
                "model": response.meta.model,
                "provider": response.meta.provider,
                "question_hash": hash_question(body.question),
                "output_language": body.output_language,
                "insufficient_sources": response.insufficient_sources,
                # Strict citation enforcement fields
                "removed_paragraph_count": response.meta.removed_paragraph_count,
                "strict_citations_failed": response.meta.strict_citations_failed,
                "citation_count_used": response.meta.citation_count_used,
                # Prompt/model fingerprinting
                "prompt_hash": response.meta.prompt_hash,
                "llm_provider": response.meta.llm_provider,
                "llm_model": response.meta.llm_model,
                # Evidence scope and counts
                "evidence_scope": response.meta.evidence_scope,
                "workspace_evidence_count": response.meta.workspace_evidence_count,
                "global_evidence_count": response.meta.global_evidence_count,
                # Policy metadata
                "policy_jurisdictions_count": response.meta.policy_jurisdictions_count,
                "policy_languages_count": response.meta.policy_languages_count,
                "policy_denied_reason": response.meta.policy_denied_reason,
            },
            request=request,
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (policy violations, etc.)
        raise

    except Exception as e:
        # Log failure and re-raise
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workflow.run.fail",
            status="fail",
            resource_type="workflow",
            meta={
                "workflow_name": WORKFLOW_NAME,
                "error": str(e)[:200],
                "question_hash": hash_question(body.question),
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Research workflow failed: {str(e)}",
        )


# =============================================================================
# Contract Review Workflow
# =============================================================================


@router.post(
    "/contract-review",
    response_model=ContractReviewResponse,
    summary="Execute contract review workflow",
    description="""
Review a specific contract document and produce structured findings.

This workflow:
1. Retrieves chunks from the specified document version
2. Ranks chunks by clause-likelihood (deterministic)
3. Generates structured findings (risks + recommendations) using an LLM
4. Returns findings with citations to contract excerpts

**Policy enforcement**: Requires CONTRACT_REVIEW_V1 to be in the workspace's allowed_workflows.

**Role required**: EDITOR or higher (review is an analysis action).

**Citations**: Every finding includes citations [1], [2], etc. that map to evidence chunks.
Findings without valid citations are automatically removed.

**Review modes**:
- `quick`: Up to 20 chunks, faster review
- `standard`: Up to 40 chunks (default)
- `deep`: Up to 80 chunks, comprehensive review
""",
)
async def contract_review(
    request: Request,
    body: ContractReviewRequest,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ContractReviewResponse:
    """Execute contract review workflow with structured findings.

    This endpoint:
    1. Enforces policy (CONTRACT_REVIEW_V1 must be allowed)
    2. Verifies document/version belongs to workspace
    3. Retrieves and ranks relevant chunks from the document
    4. Generates structured findings using an LLM
    5. Validates citations and returns structured response
    """
    request_id = get_request_id(request)

    try:
        # Policy enforcement
        resolved_policy = await require_workflow_allowed(
            ctx, CONTRACT_REVIEW_WORKFLOW, db
        )

        # Validate output language against policy
        allowed_output_languages = resolved_policy.config.allowed_output_languages
        if (
            allowed_output_languages
            and body.output_language not in allowed_output_languages
        ):
            await log_audit_event(
                db=db,
                ctx=ctx,
                action="workflow.run.fail",
                status="fail",
                resource_type="workflow",
                meta={
                    "workflow_name": CONTRACT_REVIEW_WORKFLOW,
                    "reason": "output_language_not_allowed",
                    "requested_output_language": body.output_language,
                    "document_id": body.document_id,
                    "version_id": body.version_id,
                },
                request=request,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Output language '{body.output_language}' is not allowed by policy. "
                f"Allowed: {allowed_output_languages}",
            )

        # Execute review
        service = ContractReviewService(db)
        response = await service.review_contract(
            ctx,
            body.document_id,
            body.version_id,
            review_mode=body.review_mode,
            focus_areas=body.focus_areas,
            output_language=body.output_language,
            playbook_hint=body.playbook_hint,
            request_id=request_id,
            evidence_scope=body.evidence_scope,
        )

        # Audit log success
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workflow.run.success",
            status="success",
            resource_type="workflow",
            meta={
                "workflow_name": CONTRACT_REVIEW_WORKFLOW,
                "result_status": response.meta.status.value,
                "document_id": body.document_id,
                "version_id": body.version_id,
                "evidence_chunk_count": response.meta.evidence_chunk_count,
                "model": response.meta.model,
                "provider": response.meta.provider,
                "review_mode": body.review_mode,
                "output_language": body.output_language,
                "findings_count": len(response.findings),
                "insufficient_sources": response.insufficient_sources,
                # Strict citation enforcement fields
                "removed_findings_count": response.meta.removed_findings_count,
                "strict_citations_failed": response.meta.strict_citations_failed,
                # Prompt/model fingerprinting
                "prompt_hash": response.meta.prompt_hash,
                "llm_provider": response.meta.llm_provider,
                "llm_model": response.meta.llm_model,
                # Evidence scope and counts
                "evidence_scope": response.meta.evidence_scope,
                "workspace_evidence_count": response.meta.workspace_evidence_count,
                "global_evidence_count": response.meta.global_evidence_count,
                # Policy metadata
                "policy_jurisdictions_count": response.meta.policy_jurisdictions_count,
                "policy_languages_count": response.meta.policy_languages_count,
                "policy_denied_reason": response.meta.policy_denied_reason,
            },
            request=request,
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (policy violations, etc.)
        raise

    except ValueError as e:
        # Document/version not found or access denied
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workflow.run.fail",
            status="fail",
            resource_type="workflow",
            meta={
                "workflow_name": CONTRACT_REVIEW_WORKFLOW,
                "error": str(e)[:200],
                "document_id": body.document_id,
                "version_id": body.version_id,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        # Log failure and re-raise
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workflow.run.fail",
            status="fail",
            resource_type="workflow",
            meta={
                "workflow_name": CONTRACT_REVIEW_WORKFLOW,
                "error": str(e)[:200],
                "document_id": body.document_id,
                "version_id": body.version_id,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Contract review workflow failed: {str(e)}",
        )


# =============================================================================
# Clause Redlines Workflow
# =============================================================================


@router.post(
    "/clause-redlines",
    response_model=ClauseRedlinesResponse,
    summary="Execute clause redlines workflow",
    description="""
Generate clause-centric redline suggestions for a contract document.

This workflow:
1. Detects key clause types in the document (heuristic, deterministic)
2. Loads recommended clause templates from the clause library for the jurisdiction
3. Generates suggested redlines using an LLM with strict citation requirements
4. Returns structured results with citations to contract excerpts

**Policy enforcement**: Requires CLAUSE_REDLINES_V1 to be in the workspace's allowed_workflows.

**Role required**: EDITOR or higher (analysis action).

**Strict citation rules**:
- Any claim about what the contract says MUST be cited [1], [2], etc.
- Recommended clause text (templates) may be uncited but clearly labeled
- Items with uncited contract claims are downgraded to "insufficient_evidence"

**Clause types analyzed**:
- governing_law, termination, liability, indemnity
- confidentiality, payment, ip, force_majeure

**Jurisdictions supported**: UAE, DIFC, ADGM, KSA
""",
)
async def clause_redlines(
    request: Request,
    body: ClauseRedlinesRequest,
    ctx: Annotated[RequestContext, Depends(require_editor())],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ClauseRedlinesResponse:
    """Execute clause redlines workflow with structured suggestions.

    This endpoint:
    1. Enforces policy (CLAUSE_REDLINES_V1 must be allowed)
    2. Verifies document/version belongs to workspace
    3. Detects clauses using heuristic keyword matching
    4. Generates redline suggestions using an LLM
    5. Validates citations and returns structured response
    """
    request_id = get_request_id(request)

    try:
        # Policy enforcement
        resolved_policy = await require_workflow_allowed(
            ctx, CLAUSE_REDLINES_WORKFLOW, db
        )

        # Validate output language against policy
        allowed_output_languages = resolved_policy.config.allowed_output_languages
        if (
            allowed_output_languages
            and body.output_language not in allowed_output_languages
        ):
            await log_audit_event(
                db=db,
                ctx=ctx,
                action="workflow.run.fail",
                status="fail",
                resource_type="workflow",
                meta={
                    "workflow_name": CLAUSE_REDLINES_WORKFLOW,
                    "reason": "output_language_not_allowed",
                    "requested_output_language": body.output_language,
                    "document_id": body.document_id,
                    "version_id": body.version_id,
                },
                request=request,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Output language '{body.output_language}' is not allowed by policy. "
                f"Allowed: {allowed_output_languages}",
            )

        # Validate jurisdiction against policy if specified
        if body.jurisdiction:
            allowed_jurisdictions = resolved_policy.config.allowed_jurisdictions
            if allowed_jurisdictions and body.jurisdiction not in allowed_jurisdictions:
                await log_audit_event(
                    db=db,
                    ctx=ctx,
                    action="workflow.run.fail",
                    status="fail",
                    resource_type="workflow",
                    meta={
                        "workflow_name": CLAUSE_REDLINES_WORKFLOW,
                        "reason": "jurisdiction_not_allowed",
                        "requested_jurisdiction": body.jurisdiction,
                        "document_id": body.document_id,
                        "version_id": body.version_id,
                    },
                    request=request,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Jurisdiction '{body.jurisdiction}' is not allowed by policy. "
                    f"Allowed: {allowed_jurisdictions}",
                )

        # Execute redlines generation
        service = ClauseRedlinesService(db)
        response = await service.generate_redlines(
            ctx,
            body.document_id,
            body.version_id,
            jurisdiction=body.jurisdiction,
            clause_types=body.clause_types,
            output_language=body.output_language,
            playbook_hint=body.playbook_hint,
            request_id=request_id,
            evidence_scope=body.evidence_scope,
        )

        # Audit log success
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workflow.run.success",
            status="success",
            resource_type="workflow",
            meta={
                "workflow_name": CLAUSE_REDLINES_WORKFLOW,
                "result_status": response.meta.status.value,
                "document_id": body.document_id,
                "version_id": body.version_id,
                "evidence_chunk_count": response.meta.evidence_chunk_count,
                "model": response.meta.model,
                "provider": response.meta.provider,
                "jurisdiction": response.meta.jurisdiction,
                "output_language": body.output_language,
                "item_count": len(response.items),
                "insufficient_sources": response.insufficient_sources,
                # Strict citation enforcement fields
                "downgraded_count": response.meta.downgraded_count,
                "removed_count": response.meta.removed_count,
                "strict_citations_failed": response.meta.strict_citations_failed,
                # Prompt/model fingerprinting
                "prompt_hash": response.meta.prompt_hash,
                "llm_provider": response.meta.llm_provider,
                "llm_model": response.meta.llm_model,
                # Evidence scope and counts
                "evidence_scope": response.meta.evidence_scope,
                "workspace_evidence_count": response.meta.workspace_evidence_count,
                "global_evidence_count": response.meta.global_evidence_count,
                # Policy metadata
                "policy_jurisdictions_count": response.meta.policy_jurisdictions_count,
                "policy_languages_count": response.meta.policy_languages_count,
                "policy_denied_reason": response.meta.policy_denied_reason,
            },
            request=request,
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (policy violations, etc.)
        raise

    except ValueError as e:
        # Document/version not found or access denied
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workflow.run.fail",
            status="fail",
            resource_type="workflow",
            meta={
                "workflow_name": CLAUSE_REDLINES_WORKFLOW,
                "error": str(e)[:200],
                "document_id": body.document_id,
                "version_id": body.version_id,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    except Exception as e:
        # Log failure and re-raise
        await log_audit_event(
            db=db,
            ctx=ctx,
            action="workflow.run.fail",
            status="fail",
            resource_type="workflow",
            meta={
                "workflow_name": CLAUSE_REDLINES_WORKFLOW,
                "error": str(e)[:200],
                "document_id": body.document_id,
                "version_id": body.version_id,
            },
            request=request,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Clause redlines workflow failed: {str(e)}",
        )
