"""Tests for LLM Provider Relay functionality.

These tests verify the provider selection logic, fallback behavior,
and error handling for different environment configurations.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.llm.providers import (
    LLMProviderConfigError,
    StubLLMProvider,
    OpenAILLMProvider,
    get_llm_provider_from_settings,
    get_llm_status,
)


class TestProviderRelaySelection:
    """Tests for provider selection logic."""

    def test_stub_provider_always_works(self):
        """LLM_PROVIDER=stub always returns StubLLMProvider regardless of API key."""
        settings = MagicMock()
        settings.llm_provider = "stub"
        settings.llm_model = None
        settings.llm_api_key = None
        settings.environment = "dev"

        provider = get_llm_provider_from_settings(settings)
        assert isinstance(provider, StubLLMProvider)
        assert provider.provider_name == "stub"

    def test_stub_provider_works_in_prod(self):
        """LLM_PROVIDER=stub works in prod environment."""
        settings = MagicMock()
        settings.llm_provider = "stub"
        settings.llm_model = None
        settings.llm_api_key = None
        settings.environment = "prod"

        provider = get_llm_provider_from_settings(settings)
        assert isinstance(provider, StubLLMProvider)

    def test_openai_provider_with_api_key(self):
        """LLM_PROVIDER=openai with API key returns OpenAILLMProvider."""
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_model = "gpt-4o-mini"
        settings.llm_api_key = "sk-test-key"
        settings.environment = "dev"

        provider = get_llm_provider_from_settings(settings)
        assert isinstance(provider, OpenAILLMProvider)
        assert provider.provider_name == "openai"
        assert provider.default_model == "gpt-4o-mini"

    def test_openai_uses_default_model_when_not_specified(self):
        """OpenAI provider uses gpt-4o-mini as default when model not specified."""
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_model = None  # Not specified
        settings.llm_api_key = "sk-test-key"
        settings.environment = "dev"

        provider = get_llm_provider_from_settings(settings)
        assert isinstance(provider, OpenAILLMProvider)
        assert provider.default_model == "gpt-4o-mini"


class TestDevEnvironmentFallback:
    """Tests for dev environment fallback behavior."""

    def test_openai_missing_key_dev_falls_back_to_stub(self):
        """In dev, OpenAI without API key falls back to Stub with warning."""
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_model = "gpt-4o-mini"
        settings.llm_api_key = None  # Missing
        settings.environment = "dev"

        with patch("src.llm.providers.logger") as mock_logger:
            provider = get_llm_provider_from_settings(settings)

            # Should fall back to stub
            assert isinstance(provider, StubLLMProvider)
            assert provider.provider_name == "stub"

            # Should log a warning
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert "FALLBACK TO STUB" in warning_msg

    def test_openai_missing_key_dev_empty_string_falls_back(self):
        """Empty string API key is treated as missing."""
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_model = None
        settings.llm_api_key = ""  # Empty string
        settings.environment = "dev"

        provider = get_llm_provider_from_settings(settings)
        assert isinstance(provider, StubLLMProvider)


class TestNonDevEnvironmentErrors:
    """Tests for staging/prod environment error behavior."""

    def test_openai_missing_key_staging_raises_error(self):
        """In staging, OpenAI without API key raises startup error."""
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_model = "gpt-4o-mini"
        settings.llm_api_key = None
        settings.environment = "staging"

        with pytest.raises(LLMProviderConfigError) as exc_info:
            get_llm_provider_from_settings(settings)

        error_msg = str(exc_info.value)
        assert "CRITICAL LLM CONFIGURATION ERROR" in error_msg
        assert "ENVIRONMENT = staging" in error_msg
        assert "LLM_PROVIDER = openai" in error_msg
        assert "Remediation" in error_msg

    def test_openai_missing_key_prod_raises_error(self):
        """In prod, OpenAI without API key raises startup error."""
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_model = "gpt-4o-mini"
        settings.llm_api_key = None
        settings.environment = "prod"

        with pytest.raises(LLMProviderConfigError) as exc_info:
            get_llm_provider_from_settings(settings)

        error_msg = str(exc_info.value)
        assert "CRITICAL LLM CONFIGURATION ERROR" in error_msg
        assert "ENVIRONMENT = prod" in error_msg

    def test_openai_with_key_works_in_prod(self):
        """OpenAI with API key works in prod environment."""
        settings = MagicMock()
        settings.llm_provider = "openai"
        settings.llm_model = "gpt-4o"
        settings.llm_api_key = "sk-production-key"
        settings.environment = "prod"

        provider = get_llm_provider_from_settings(settings)
        assert isinstance(provider, OpenAILLMProvider)
        assert provider.default_model == "gpt-4o"


class TestUnknownProviderError:
    """Tests for unknown provider configuration errors."""

    def test_unknown_provider_raises_error(self):
        """Unknown provider name raises config error."""
        settings = MagicMock()
        settings.llm_provider = "anthropic"  # Not supported
        settings.llm_model = None
        settings.llm_api_key = "sk-test"
        settings.environment = "dev"

        with pytest.raises(LLMProviderConfigError) as exc_info:
            get_llm_provider_from_settings(settings)

        error_msg = str(exc_info.value)
        assert "Unknown LLM_PROVIDER" in error_msg
        assert "'anthropic'" in error_msg
        assert "Valid providers:" in error_msg

    def test_provider_name_case_insensitive(self):
        """Provider name matching is case-insensitive."""
        settings = MagicMock()
        settings.llm_provider = "OPENAI"  # Uppercase
        settings.llm_model = None
        settings.llm_api_key = "sk-test"
        settings.environment = "dev"

        provider = get_llm_provider_from_settings(settings)
        assert isinstance(provider, OpenAILLMProvider)


class TestLLMStatusFunction:
    """Tests for the get_llm_status diagnostic function."""

    def test_llm_status_stub_provider(self):
        """get_llm_status returns correct info for stub provider."""
        with patch("src.llm.providers.settings") as mock_settings:
            mock_settings.llm_provider = "stub"
            mock_settings.llm_model = None
            mock_settings.llm_api_key = None
            mock_settings.environment = "dev"

            status = get_llm_status()

            assert status["provider"] == "stub"
            assert status["model"] == "stub-v1"
            assert status["configured_provider"] == "stub"
            assert status["api_key_set"] is False
            assert status["environment"] == "dev"
            assert status["is_fallback"] is False

    def test_llm_status_openai_provider(self):
        """get_llm_status returns correct info for OpenAI provider."""
        with patch("src.llm.providers.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_api_key = "sk-test-key"
            mock_settings.environment = "dev"

            status = get_llm_status()

            assert status["provider"] == "openai"
            assert status["model"] == "gpt-4o-mini"
            assert status["configured_provider"] == "openai"
            assert status["api_key_set"] is True
            assert status["is_fallback"] is False

    def test_llm_status_fallback_detected(self):
        """get_llm_status correctly identifies fallback scenario."""
        with patch("src.llm.providers.settings") as mock_settings:
            mock_settings.llm_provider = "openai"
            mock_settings.llm_model = "gpt-4o-mini"
            mock_settings.llm_api_key = None  # Missing
            mock_settings.environment = "dev"

            status = get_llm_status()

            assert status["provider"] == "stub"  # Fell back
            assert status["model"] == "stub-v1"
            assert status["configured_provider"] == "openai"  # Was configured
            assert status["api_key_set"] is False
            assert status["is_fallback"] is True


class TestProviderMetaInWorkflows:
    """Tests to verify workflow meta contains correct provider info.

    These tests use mocking to avoid real API calls while verifying
    that the correct provider/model info flows through to responses.
    """

    def test_stub_provider_meta_properties(self):
        """StubLLMProvider returns correct meta in responses."""
        provider = StubLLMProvider()

        assert provider.provider_name == "stub"
        assert provider.default_model == "stub-v1"

    def test_openai_provider_meta_properties(self):
        """OpenAILLMProvider returns correct meta in responses."""
        provider = OpenAILLMProvider(api_key="sk-test", default_model="gpt-4o")

        assert provider.provider_name == "openai"
        assert provider.default_model == "gpt-4o"

    @pytest.mark.asyncio
    async def test_stub_response_includes_correct_meta(self):
        """Stub provider response includes correct provider/model in LLMResponse."""
        provider = StubLLMProvider()

        response = await provider.generate(
            prompt="[EVIDENCE 1] Test content\n\nWhat is the legal position?"
        )

        assert response.provider == "stub"
        assert response.model == "stub-v1"
