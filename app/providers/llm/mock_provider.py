"""
mock_provider.py — Deterministic mock LLM provider for unit tests and offline development.
"""
from __future__ import annotations

import re
from typing import Optional, List

from app.providers.llm.base import BaseLLMProvider


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider generating grounded, citation-attributed answers without external API calls.
    """

    provider_name: str = "mock"

    def __init__(
        self,
        model_name: str = "mock-governance-llm",
        canned_response: Optional[str] = None,
        should_raise: Optional[Exception] = None,
    ):
        self.model_name = model_name
        self.canned_response = canned_response
        self.should_raise = should_raise

    def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate deterministic mock response based on prompt context."""
        if self.should_raise:
            raise self.should_raise

        if self.canned_response is not None:
            return self.canned_response

        # Extract available source IDs from prompt
        source_ids = re.findall(r"\[(SOURCE_\d+)\]", prompt)
        unique_sources = sorted(list(dict.fromkeys(source_ids)))

        # Extract user question from prompt if demarcated
        q_match = re.search(r"<user_question>\s*(.*?)\s*</user_question>", prompt, re.DOTALL)
        question_text = q_match.group(1).strip() if q_match else "the query"

        if not unique_sources:
            return (
                "Based on the provided governance documentation, the available authorized documents "
                "do not contain sufficient information to answer this question."
            )

        # Build a grounded response citing available source IDs
        primary_source = unique_sources[0]
        secondary_source = unique_sources[1] if len(unique_sources) > 1 else None

        answer_parts = [
            f"Based on the authorized governance policies regarding {question_text}, "
            f"the documented requirements establish specific security standards and operational protocols [{primary_source}]."
        ]

        if secondary_source:
            answer_parts.append(
                f"Additionally, compliance guidelines mandate role-appropriate verification and strict adherence to established organizational controls [{secondary_source}]."
            )

        return " ".join(answer_parts)
