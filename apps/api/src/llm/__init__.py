"""LLM Gateway for Aiden.ai.

This module provides a minimal, model-agnostic LLM client abstraction.
It supports multiple providers via a common interface.

Providers:
- StubLLMProvider: Deterministic output for tests (default in test mode)
- OpenAILLMProvider: OpenAI integration
- AnthropicLLMProvider: Anthropic (Claude) integration
- OpenAICompatibleLLMProvider: Any OpenAI-compatible API (Ollama, OpenRouter, etc.)

Configuration:
- LLM_PROVIDER: "stub", "openai", "anthropic", or "openai_compatible"
- LLM_MODEL: Model name (provider-specific)
- LLM_API_KEY: API key (required for OpenAI/Anthropic)
- LLM_BASE_URL: Base URL (required for openai_compatible)
"""

from src.llm.base import LLMProvider, LLMResponse
from src.llm.providers import get_llm_provider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "get_llm_provider",
]
