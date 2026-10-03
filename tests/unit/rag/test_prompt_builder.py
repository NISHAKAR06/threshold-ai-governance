"""
test_prompt_builder.py — Unit tests for PromptBuilder.
"""
from app.engines.rag.prompt_builder import PromptBuilder


def test_prompt_builder_structure():
    builder = PromptBuilder()
    context = "[SOURCE_1]\nDocument ID: SEC-001\nContent:\nSecurity guidelines."
    question = "Who is allowed to access AI models?"

    built = builder.build_prompt(question=question, formatted_context=context)

    # 1. Verify system instruction exists and has grounding rules
    assert "STRICT GROUNDING RULES" in built.system_instruction
    assert "SOURCE_X" in built.system_instruction

    # 2. Verify prompt text separates context and question with delimiters
    assert "<retrieved_context>" in built.prompt_text
    assert "</retrieved_context>" in built.prompt_text
    assert context in built.prompt_text

    assert "<user_question>" in built.prompt_text
    assert "</user_question>" in built.prompt_text
    assert question in built.prompt_text

    # 3. Verify deterministic output
    built_second = builder.build_prompt(question=question, formatted_context=context)
    assert built.prompt_text == built_second.prompt_text


def test_prompt_builder_empty_inputs():
    builder = PromptBuilder()
    built = builder.build_prompt(question="", formatted_context="")

    assert "<user_question>" in built.prompt_text
    assert "<retrieved_context>" in built.prompt_text
