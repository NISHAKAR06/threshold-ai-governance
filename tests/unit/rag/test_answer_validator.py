"""
test_answer_validator.py — Unit tests for AnswerValidator.
"""
from app.engines.rag.answer_validator import AnswerValidator


def test_answer_validator_valid_citations():
    validator = AnswerValidator()
    raw = "Employees must log in via MFA [SOURCE_1] and adhere to password policies [SOURCE_2]."
    valid_ids = {"SOURCE_1", "SOURCE_2", "SOURCE_3"}

    res = validator.validate(raw_answer=raw, valid_source_ids=valid_ids)
    assert res.is_grounded is True
    assert res.is_insufficient_context is False
    assert res.cited_source_ids == ["SOURCE_1", "SOURCE_2"]
    assert res.invalid_source_ids == []
    assert "[SOURCE_1]" in res.text
    assert "[SOURCE_2]" in res.text


def test_answer_validator_empty_answer():
    validator = AnswerValidator()
    res = validator.validate(raw_answer="   \n\t ", valid_source_ids={"SOURCE_1"})

    assert res.is_grounded is False
    assert res.is_insufficient_context is True
    assert res.cited_source_ids == []
    assert "No response" in res.text


def test_answer_validator_invalid_citation_sanitization():
    validator = AnswerValidator()
    # Model hallucinated [SOURCE_99] which is not in valid_source_ids
    raw = "Access requires special clearance [SOURCE_1] and executive override [SOURCE_99]."
    valid_ids = {"SOURCE_1"}

    res = validator.validate(raw_answer=raw, valid_source_ids=valid_ids)
    assert "SOURCE_1" in res.cited_source_ids
    assert "SOURCE_99" in res.invalid_source_ids
    # Hallucinated citation tag [SOURCE_99] must be stripped from returned text
    assert "[SOURCE_99]" not in res.text
    assert "[SOURCE_1]" in res.text


def test_answer_validator_insufficient_context_detection():
    validator = AnswerValidator()
    raw = (
        "Based on the provided governance documents, there is insufficient information "
        "to determine the retention schedule."
    )
    res = validator.validate(raw_answer=raw, valid_source_ids={"SOURCE_1"})

    assert res.is_insufficient_context is True
    assert res.is_grounded is True  # Truthfully acknowledging lack of context is grounded


def test_answer_validator_truncation_on_excessive_length():
    validator = AnswerValidator(max_answer_length=50)
    raw = "This is a very long response that exceeds the configured fifty character limit."
    res = validator.validate(raw_answer=raw, valid_source_ids=set())

    assert len(res.text) <= 53  # 50 + "..."
    assert res.text.endswith("...")
