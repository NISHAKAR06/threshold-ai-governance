"""
gemini_provider.py — Google Gemini LLM provider implementation for production answer generation.
"""
from __future__ import annotations

from typing import Optional

from app.config import settings
from app.core.logger import service_logger
from app.core.exceptions import LLMGenerationError
from app.providers.llm.base import BaseLLMProvider


class GeminiLLMProvider(BaseLLMProvider):
    """Production provider integrating Google Gemini models via google.generativeai."""

    provider_name: str = "gemini"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model_name = model_name or settings.LLM_MODEL or settings.GEMINI_MODEL
        self._configured = False

        if self.api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self._configured = True
            except Exception as exc:
                service_logger.warning(f"GeminiLLMProvider: Failed to configure genai: {exc}")
        else:
            service_logger.warning("GeminiLLMProvider: GEMINI_API_KEY is not set.")

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate answer text via Gemini."""
        if not self._configured:
            raise LLMGenerationError(
                "Gemini API key is not configured. Set GEMINI_API_KEY or use MockLLMProvider."
            )

        try:
            import google.generativeai as genai

            generation_config = genai.types.GenerationConfig(
                temperature=temperature if temperature is not None else settings.RAG_TEMPERATURE,
                max_output_tokens=max_tokens or settings.RAG_MAX_ANSWER_LENGTH,
            )

            kwargs = {
                "model_name": self.model_name,
                "generation_config": generation_config,
            }
            if system_instruction:
                kwargs["system_instruction"] = system_instruction

            model = genai.GenerativeModel(**kwargs)
            response = model.generate_content(prompt)

            if not response or not response.text:
                raise LLMGenerationError("Gemini returned an empty response")

            return response.text.strip()
        except Exception as exc:
            if isinstance(exc, LLMGenerationError):
                raise
            service_logger.error(f"GeminiLLMProvider generation failed: {exc}")
            raise LLMGenerationError(f"Gemini API error during generation: {exc}") from exc
