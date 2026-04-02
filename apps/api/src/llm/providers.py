"""LLM provider implementations and factory.

LLM Provider Relay
==================
The provider relay implements smart provider selection with environment-aware
fallback behavior:

1. If LLM_PROVIDER=openai:
   - If LLM_API_KEY is present -> OpenAILLMProvider
   - If missing in ENVIRONMENT=dev -> warn loudly, fall back to StubLLMProvider
   - If missing in ENVIRONMENT!=dev -> raise startup error with remediation steps

2. If LLM_PROVIDER=stub -> StubLLMProvider (always allowed)

3. If unknown provider -> raise config error

This ensures no accidental production deployments with missing API keys, while
allowing flexible development workflows.
"""

import hashlib
import logging
import re
from functools import lru_cache
from typing import TYPE_CHECKING

from src.llm.base import LLMProvider, LLMResponse

if TYPE_CHECKING:
    from src.config import Settings

logger = logging.getLogger(__name__)


class LLMProviderConfigError(Exception):
    """Raised when LLM provider configuration is invalid."""

    pass


class StubLLMProvider(LLMProvider):
    """Stub LLM provider for testing.

    Returns deterministic output based on the prompt content.
    Never makes external API calls - safe for tests.

    Test modes can be triggered by including special markers in the prompt:
    - [TEST:UNCITED_PARAGRAPH] - Include an uncited paragraph for strict test
    - [TEST:NO_CITATIONS] - Return content with no citations at all
    - [TEST:FOOTER_ONLY] - Return content with citations only in a footer

    Contract review test modes:
    - [TEST:CONTRACT_VALID] - Return valid JSON with properly cited findings
    - [TEST:CONTRACT_INVALID_CITATIONS] - Return findings with invalid citation indices
    - [TEST:CONTRACT_NO_SUMMARY_CITATION] - Return valid findings but uncited summary

    Clause redlines test modes:
    - [TEST:CLAUSE_REDLINES_VALID] - Return valid JSON with properly cited items
    - [TEST:CLAUSE_REDLINES_UNCITED_CLAIM] - Contains uncited "contract says..." claim
    - [TEST:CLAUSE_REDLINES_INVALID_CITATIONS] - Out-of-range citations
    """

    def __init__(self, test_mode: str | None = None):
        """Initialize stub provider.

        Args:
            test_mode: Optional test mode to force specific behavior
        """
        self._test_mode = test_mode

    @property
    def provider_name(self) -> str:
        return "stub"

    @property
    def default_model(self) -> str:
        return "stub-v1"

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate deterministic stub response.

        The response is designed to mimic a real LLM output with citations
        for testing the research pipeline.
        """
        # Check for test mode markers in prompt
        test_mode = self._test_mode
        if "[TEST:UNCITED_PARAGRAPH]" in prompt:
            test_mode = "uncited_paragraph"
        elif "[TEST:NO_CITATIONS]" in prompt:
            test_mode = "no_citations"
        elif "[TEST:FOOTER_ONLY]" in prompt:
            test_mode = "footer_only"
        elif "[TEST:CONTRACT_VALID]" in prompt:
            test_mode = "contract_valid"
        elif "[TEST:CONTRACT_INVALID_CITATIONS]" in prompt:
            test_mode = "contract_invalid_citations"
        elif "[TEST:CONTRACT_NO_SUMMARY_CITATION]" in prompt:
            test_mode = "contract_no_summary_citation"
        elif "[TEST:CLAUSE_REDLINES_VALID]" in prompt:
            test_mode = "clause_redlines_valid"
        elif "[TEST:CLAUSE_REDLINES_UNCITED_CLAIM]" in prompt:
            test_mode = "clause_redlines_uncited_claim"
        elif "[TEST:CLAUSE_REDLINES_INVALID_CITATIONS]" in prompt:
            test_mode = "clause_redlines_invalid_citations"

        # Detect if this is a clause redlines prompt
        is_clause_redlines = "CLAUSE REDLINES ANALYSIS" in prompt

        # Detect if this is a contract review prompt
        is_contract_review = "CONTRACT REVIEW:" in prompt

        # Detect if this is a legal research prompt by looking for evidence markers
        evidence_count = len(re.findall(r"\[EVIDENCE \d+\]", prompt))

        if is_clause_redlines:
            answer = self._generate_clause_redlines_response(
                prompt, evidence_count, test_mode
            )
        elif is_contract_review:
            answer = self._generate_contract_review_response(
                prompt, evidence_count, test_mode
            )
        elif evidence_count == 0:
            # No evidence provided, return insufficient response
            answer = "I cannot provide an answer without sufficient source material."
        elif test_mode == "no_citations":
            # Test mode: return content with NO citations
            answer = (
                "Based on the provided sources, the legal position is as follows.\n\n"
                "The documents indicate that the relevant provisions apply. "
                "The terms appear to be binding under applicable law.\n\n"
                "This interpretation is supported by standard legal principles."
            )
        elif test_mode == "footer_only":
            # Test mode: citations only in a references footer
            answer = (
                "Based on the provided sources, the legal position is as follows.\n\n"
                "The documents indicate that the relevant provisions apply. "
                "The terms are binding under applicable law.\n\n"
                "Key Sources:\n"
                "[1] Employment Agreement - Section 3\n"
                "[2] Company Policy - Article 5"
            )
        elif test_mode == "uncited_paragraph":
            # Test mode: mixed cited and uncited paragraphs
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]
            answer = (
                f"Based on the provided sources, the legal position is as follows [1].\n\n"
                f"This paragraph has no citations and should be removed by strict enforcement. "
                f"It contains general statements without proper source attribution.\n\n"
                f"The terms are binding as stated in [2]. This is properly cited content. "
                f"Source [1] also confirms this interpretation.\n\n"
                f"[Analysis ID: {prompt_hash}]"
            )
        else:
            # Default: generate properly cited answer
            prompt_hash = hashlib.sha256(prompt.encode()).hexdigest()[:8]

            citations = []
            for i in range(1, min(evidence_count, 3) + 1):
                citations.append(f"[{i}]")

            citation_str = " ".join(citations)

            answer = (
                f"Based on the provided sources {citation_str}, the legal position is as follows:\n\n"
                f"The documents indicate that the relevant provisions apply [1]. "
                f"Specifically, as stated in source [1], the terms are binding. "
            )

            if evidence_count >= 2:
                answer += f"This is further supported by [2] which provides additional context. "

            if evidence_count >= 3:
                answer += f"Source [3] confirms this interpretation. "

            answer += f"\n\n[Analysis ID: {prompt_hash}]"

        return LLMResponse(
            text=answer,
            model=model or self.default_model,
            provider=self.provider_name,
            prompt_tokens=len(prompt) // 4,  # Rough estimate
            completion_tokens=len(answer) // 4,
            total_tokens=(len(prompt) + len(answer)) // 4,
        )

    def _generate_clause_redlines_response(
        self, prompt: str, evidence_count: int, test_mode: str | None
    ) -> str:
        """Generate a clause redlines JSON response.

        Args:
            prompt: The prompt text
            evidence_count: Number of evidence chunks
            test_mode: Optional test mode

        Returns:
            JSON string for clause redlines response
        """
        import json

        if evidence_count == 0:
            return json.dumps({
                "summary": "No contract excerpts were provided for analysis.",
                "items": []
            })

        if test_mode == "clause_redlines_invalid_citations":
            # Return items with invalid citation indices (out of range)
            return json.dumps({
                "summary": "This contract has clause issues [99][100].",
                "items": [
                    {
                        "clause_type": "governing_law",
                        "status": "found",
                        "confidence": 0.8,
                        "issue": "The governing law clause references UAE law [99].",
                        "suggested_redline": "Recommended Text: This Agreement shall be governed by UAE law.",
                        "rationale": "Standard UAE clause should be used [100].",
                        "severity": "medium",
                        "citations": [99, 100]
                    },
                    {
                        "clause_type": "liability",
                        "status": "found",
                        "confidence": 0.7,
                        "issue": "The liability clause needs review [1].",
                        "suggested_redline": "Recommended Text: Liability shall be capped.",
                        "rationale": "Per the contract [1], liability is unlimited.",
                        "severity": "high",
                        "citations": [1]
                    }
                ]
            })

        if test_mode == "clause_redlines_uncited_claim":
            # Return items with uncited "contract says" claims
            return json.dumps({
                "summary": "Analysis of contract clauses [1][2].",
                "items": [
                    {
                        "clause_type": "termination",
                        "status": "found",
                        "confidence": 0.75,
                        "issue": "The contract says termination requires 30 days notice.",  # NO CITATION
                        "suggested_redline": "Recommended Text: Either party may terminate with 60 days notice.",
                        "rationale": "The current language in the contract is insufficient.",  # NO CITATION
                        "severity": "medium",
                        "citations": []  # No citations provided
                    },
                    {
                        "clause_type": "liability",
                        "status": "found",
                        "confidence": 0.8,
                        "issue": "Liability is limited to contract value [1].",
                        "suggested_redline": "Recommended Text: Liability shall not exceed 2x contract value.",
                        "rationale": "Per [1], the current cap is too low.",
                        "severity": "high",
                        "citations": [1]
                    }
                ]
            })

        # Default or clause_redlines_valid: generate properly cited response
        items = []

        if evidence_count >= 1:
            items.append({
                "clause_type": "governing_law",
                "status": "found",
                "confidence": 0.85,
                "issue": "The governing law clause specifies UAE jurisdiction [1].",
                "suggested_redline": "Recommended Text: This Agreement shall be governed by and construed in accordance with the laws of the United Arab Emirates.",
                "rationale": "The current clause [1] is acceptable but could be more detailed.",
                "severity": "low",
                "citations": [1]
            })

        if evidence_count >= 2:
            items.append({
                "clause_type": "liability",
                "status": "found",
                "confidence": 0.78,
                "issue": "The liability clause limits damages to contract value [2]. This may be insufficient for consequential damages.",
                "suggested_redline": "Recommended Text: Neither Party shall be liable for indirect, incidental, special, consequential, or punitive damages. Total liability shall not exceed 2x the contract value.",
                "rationale": "Per [2], the current cap is low. Recommend increasing to 2x.",
                "severity": "high",
                "citations": [2]
            })

        if evidence_count >= 3:
            items.append({
                "clause_type": "termination",
                "status": "found",
                "confidence": 0.72,
                "issue": "The termination clause requires only 30 days notice [3].",
                "suggested_redline": "Recommended Text: Either Party may terminate upon sixty (60) days' prior written notice.",
                "rationale": "Consider extending notice period as stated in [3].",
                "severity": "medium",
                "citations": [3]
            })

        # Add a missing clause example
        items.append({
            "clause_type": "force_majeure",
            "status": "missing",
            "confidence": 0.1,
            "issue": None,
            "suggested_redline": "Recommended Text: Neither Party shall be liable for failures due to circumstances beyond its reasonable control, including acts of God, natural disasters, war, terrorism, or pandemic.",
            "rationale": "No force majeure clause detected. Recommend adding one.",
            "severity": "medium",
            "citations": []
        })

        cite_str = "".join(f"[{i}]" for i in range(1, min(evidence_count, 3) + 1))

        return json.dumps({
            "summary": f"Clause analysis identified {len(items)} items requiring attention {cite_str}. Key areas include governing law, liability limitations, and termination provisions.",
            "items": items
        })

    def _generate_contract_review_response(
        self, prompt: str, evidence_count: int, test_mode: str | None
    ) -> str:
        """Generate a contract review JSON response.

        Args:
            prompt: The prompt text
            evidence_count: Number of evidence chunks
            test_mode: Optional test mode

        Returns:
            JSON string for contract review response
        """
        import json

        if evidence_count == 0:
            # No evidence - return empty result
            return json.dumps({
                "summary": "No contract excerpts were provided for review.",
                "findings": []
            })

        if test_mode == "contract_invalid_citations":
            # Return findings with invalid citation indices (out of range)
            return json.dumps({
                "summary": "This contract contains several issues [99][100].",
                "findings": [
                    {
                        "title": "Invalid Liability Clause",
                        "severity": "high",
                        "category": "liability",
                        "issue": "The liability clause is problematic [99].",
                        "recommendation": "Revise the clause [100].",
                        "citations": [99, 100]  # Invalid indices
                    },
                    {
                        "title": "Valid Finding",
                        "severity": "medium",
                        "category": "termination",
                        "issue": "The termination clause needs review [1].",
                        "recommendation": "Add notice period requirements [1].",
                        "citations": [1]  # Valid
                    }
                ]
            })

        if test_mode == "contract_no_summary_citation":
            # Return valid findings but summary without citations
            return json.dumps({
                "summary": "This contract has several areas requiring attention.",  # No citations
                "findings": [
                    {
                        "title": "Liability Limitation",
                        "severity": "high",
                        "category": "liability",
                        "issue": "The liability cap is too low per [1].",
                        "recommendation": "Increase the liability cap as specified in [1].",
                        "citations": [1]
                    },
                    {
                        "title": "Payment Terms",
                        "severity": "medium",
                        "category": "payment",
                        "issue": "Payment terms are vague [2].",
                        "recommendation": "Specify exact payment schedule [2].",
                        "citations": [2]
                    }
                ]
            })

        # Default or contract_valid: generate properly cited response
        findings = []

        if evidence_count >= 1:
            findings.append({
                "title": "Liability Clause Review",
                "severity": "high",
                "category": "liability",
                "issue": "The liability clause limits damages to contract value [1]. This may be insufficient for consequential damages.",
                "recommendation": "Negotiate higher liability cap or exclude certain damage types [1].",
                "citations": [1]
            })

        if evidence_count >= 2:
            findings.append({
                "title": "Termination Provisions",
                "severity": "medium",
                "category": "termination",
                "issue": "The termination clause requires 30 days notice [2]. Consider whether this is adequate.",
                "recommendation": "Extend notice period to 60 days for material breaches [2].",
                "citations": [2]
            })

        if evidence_count >= 3:
            findings.append({
                "title": "Governing Law",
                "severity": "low",
                "category": "governing_law",
                "issue": "The contract is governed by UAE law [3]. Ensure compliance with local requirements.",
                "recommendation": "No action required - standard jurisdiction clause [3].",
                "citations": [3]
            })

        cite_str = "".join(f"[{i}]" for i in range(1, min(evidence_count, 3) + 1))

        return json.dumps({
            "summary": f"Contract review identified {len(findings)} findings requiring attention {cite_str}. Key areas include liability limitations, termination provisions, and jurisdictional considerations.",
            "findings": findings
        })


class OpenAILLMProvider(LLMProvider):
    """OpenAI LLM provider.

    Uses the OpenAI API for text generation.
    Requires LLM_API_KEY environment variable.
    """

    def __init__(self, api_key: str, default_model: str = "gpt-4o-mini"):
        """Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key
            default_model: Default model to use
        """
        self._api_key = api_key
        self._default_model = default_model
        self._client = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def default_model(self) -> str:
        return self._default_model

    def _get_client(self):
        """Lazy-load the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI

                self._client = AsyncOpenAI(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "OpenAI package not installed. Run: pip install openai"
                )
        return self._client

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 2048,
        system_prompt: str | None = None,
    ) -> LLMResponse:
        """Generate text using OpenAI API."""
        client = self._get_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        use_model = model or self._default_model

        # Newer models (o1, o3, gpt-5+) require different API parameters:
        # - Use max_completion_tokens instead of max_tokens
        # - Don't support custom temperature (only default value)
        is_new_model = use_model.startswith(("o1", "o3", "gpt-5", "gpt-6"))

        if is_new_model:
            # Newer models: use max_completion_tokens, no temperature parameter
            response = await client.chat.completions.create(
                model=use_model,
                messages=messages,
                max_completion_tokens=max_tokens,
            )
        else:
            # Standard models (gpt-3.5, gpt-4): use max_tokens and temperature
            response = await client.chat.completions.create(
                model=use_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

        usage = response.usage
        return LLMResponse(
            text=response.choices[0].message.content or "",
            model=use_model,
            provider=self.provider_name,
            prompt_tokens=usage.prompt_tokens if usage else None,
            completion_tokens=usage.completion_tokens if usage else None,
            total_tokens=usage.total_tokens if usage else None,
        )


def get_llm_provider_from_settings(settings: "Settings") -> LLMProvider:
    """Get an LLM provider based on explicit settings (non-cached).

    This is the core relay logic. Use this for testing or when you need
    a fresh provider instance with specific settings.

    Args:
        settings: The Settings instance to read configuration from

    Returns:
        Configured LLMProvider instance

    Raises:
        LLMProviderConfigError: If configuration is invalid (e.g., OpenAI
            selected but API key missing in non-dev environment, or
            unknown provider specified)
    """
    provider_name = getattr(settings, "llm_provider", "stub").lower()
    model = getattr(settings, "llm_model", None)
    api_key = getattr(settings, "llm_api_key", None)
    environment = getattr(settings, "environment", "dev")

    # Validate provider name
    valid_providers = {"stub", "openai"}
    if provider_name not in valid_providers:
        raise LLMProviderConfigError(
            f"Unknown LLM_PROVIDER: '{provider_name}'.\n"
            f"\n"
            f"  Valid providers: {', '.join(sorted(valid_providers))}\n"
            f"\n"
            f"  Remediation:\n"
            f"    Set LLM_PROVIDER to one of: stub, openai\n"
        )

    # Handle stub provider (always allowed)
    if provider_name == "stub":
        logger.info("LLM Provider Relay: Using StubLLMProvider (LLM_PROVIDER=stub)")
        return StubLLMProvider()

    # Handle OpenAI provider
    if provider_name == "openai":
        if api_key:
            # API key present - use OpenAI
            effective_model = model or "gpt-4o-mini"
            logger.info(
                f"LLM Provider Relay: Using OpenAILLMProvider "
                f"(model={effective_model})"
            )
            return OpenAILLMProvider(api_key=api_key, default_model=effective_model)

        # API key missing - behavior depends on environment
        if environment == "dev":
            # Dev environment: warn loudly and fall back to stub
            logger.warning(
                "=" * 70 + "\n"
                "  LLM PROVIDER RELAY: FALLBACK TO STUB\n"
                "=" * 70 + "\n"
                "  LLM_PROVIDER=openai but LLM_API_KEY is not set.\n"
                "  ENVIRONMENT=dev, so falling back to StubLLMProvider.\n"
                "\n"
                "  To use OpenAI, set:\n"
                "    LLM_API_KEY=sk-your-api-key\n"
                "\n"
                "  The Stub provider returns generic/deterministic answers.\n"
                "  This is suitable for development and testing only.\n"
                "=" * 70
            )
            return StubLLMProvider()
        else:
            # Staging/prod: hard fail with clear error
            raise LLMProviderConfigError(
                f"CRITICAL LLM CONFIGURATION ERROR\n"
                f"\n"
                f"  Current configuration:\n"
                f"    ENVIRONMENT = {environment}\n"
                f"    LLM_PROVIDER = openai\n"
                f"    LLM_API_KEY = (not set)\n"
                f"\n"
                f"  OpenAI provider requires an API key in non-dev environments.\n"
                f"\n"
                f"  Remediation (choose one):\n"
                f"    1. Set LLM_API_KEY=sk-your-api-key\n"
                f"    2. Set LLM_PROVIDER=stub (for testing only)\n"
                f"    3. Set ENVIRONMENT=dev (for local development)\n"
            )

    # Should never reach here, but defensive fallback
    return StubLLMProvider()


@lru_cache(maxsize=1)
def get_llm_provider() -> LLMProvider:
    """Get the configured LLM provider singleton.

    This is a cached wrapper around get_llm_provider_from_settings that
    uses the global settings instance. The provider is created once and
    reused for all subsequent calls.

    Configuration is read from environment variables:
    - LLM_PROVIDER: "stub" or "openai" (default: "stub")
    - LLM_MODEL: Model name (optional, uses provider default)
    - LLM_API_KEY: API key (required for OpenAI)
    - ENVIRONMENT: "dev", "staging", or "prod" (affects fallback behavior)

    Returns:
        Configured LLMProvider instance

    Raises:
        LLMProviderConfigError: If configuration is invalid
    """
    from src.config import settings

    return get_llm_provider_from_settings(settings)


def get_stub_provider() -> StubLLMProvider:
    """Get a StubLLMProvider instance for testing.

    This always returns a new StubLLMProvider, bypassing configuration.
    Use this in tests to ensure no external calls are made.
    """
    return StubLLMProvider()


def get_llm_status() -> dict:
    """Get the current LLM provider status for diagnostics.

    Returns a dictionary with:
    - provider: The active provider name ("stub" or "openai")
    - model: The active model name
    - configured_provider: What LLM_PROVIDER is set to
    - api_key_set: Whether LLM_API_KEY is set (not the actual key)
    - environment: Current environment
    - is_fallback: Whether we fell back from OpenAI to Stub

    This is useful for health checks and debugging.
    """
    from src.config import settings

    provider_name = getattr(settings, "llm_provider", "stub").lower()
    model = getattr(settings, "llm_model", None)
    api_key = getattr(settings, "llm_api_key", None)
    environment = getattr(settings, "environment", "dev")

    api_key_set = bool(api_key)

    # Determine what provider is actually active
    is_fallback = False
    if provider_name == "openai":
        if api_key_set:
            active_provider = "openai"
            active_model = model or "gpt-4o-mini"
        else:
            # Fallback to stub (only possible in dev)
            active_provider = "stub"
            active_model = "stub-v1"
            is_fallback = True
    else:
        active_provider = "stub"
        active_model = "stub-v1"

    return {
        "provider": active_provider,
        "model": active_model,
        "configured_provider": provider_name,
        "api_key_set": api_key_set,
        "environment": environment,
        "is_fallback": is_fallback,
    }
