"""
factory.py — Factory for instantiating configured LLM providers.
"""
from __future__ import annotations

from typing import Optional

from app.config import settings
from app.providers.llm.base import BaseLLMProvider
from app.providers.llm.mock_provider import MockLLMProvider
from app.providers.llm.gemini_provider import GeminiLLMProvider


def get_llm_provider(
    provider_name: Optional[str] = None,
    model_name: Optional[str] = None,
    **kwargs,
) -> BaseLLMProvider:
    """
    Instantiate and return the configured LLM provider.

    Args:
        provider_name: Name of provider e.g. "mock", "gemini". Defaults to settings.LLM_PROVIDER.
        model_name: Optional model override.

    Returns:
        Instance of BaseLLMProvider.
    """
    chosen_provider = (provider_name or settings.LLM_PROVIDER or "mock").lower()

    if chosen_provider == "gemini":
        return GeminiLLMProvider(model_name=model_name, **kwargs)
    elif chosen_provider == "mock":
        return MockLLMProvider(model_name=model_name or "mock-governance-llm", **kwargs)
    else:
        # Fallback to mock with warning
        return MockLLMProvider(model_name=model_name or chosen_provider, **kwargs)
