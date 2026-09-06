"""
registry_schema.py — Pydantic schema validation for metadata/document_registry.json.
"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator


VALID_DEPARTMENTS = {
    "Human Resources",
    "Information Security",
    "Enterprise Governance",
    "Engineering",
    "Operations",
}

VALID_CLASSIFICATIONS = {"PUBLIC", "INTERNAL", "CONFIDENTIAL", "RESTRICTED"}
VALID_STATUSES = {"DRAFT", "ACTIVE", "ARCHIVED", "SUPERSEDED"}
VALID_ROLES = {
    "EMPLOYEE",
    "MANAGER",
    "ENGINEER",
    "AI_ENGINEER",
    "SECURITY_ENGINEER",
    "OPERATIONS_MANAGER",
    "HR_MANAGER",
    "ADMIN",
}
VALID_FORMATS = {"PDF", "DOCX", "TXT"}


class RegistryDocumentRecord(BaseModel):
    """Schema for a single document record in document_registry.json."""
    document_id: str = Field(..., description="Unique document identifier e.g. HR-001")
    title: str = Field(..., min_length=2, description="Official title of the document")
    department: str = Field(..., description="Department name")
    classification: str = Field(..., description="Sensitivity classification level")
    version: str = Field(..., description="Semantic version string e.g. 1.0")
    status: str = Field(..., description="Lifecycle status e.g. ACTIVE")
    effective_date: str = Field(..., description="Effective date in YYYY-MM-DD format")
    allowed_roles: List[str] = Field(..., min_length=1, description="Roles permitted to retrieve/view")
    document_type: str = Field(..., description="Document type e.g. POLICY, RUNBOOK")
    summary: str = Field(..., min_length=10, description="Concise synopsis of document contents")
    keywords: List[str] = Field(..., min_length=1, description="Topical keywords")
    file_path: str = Field(..., description="Relative file path to source document")
    file_format: str = Field(..., description="File format uppercase e.g. PDF, DOCX, TXT")

    @field_validator("department")
    @classmethod
    def validate_department(cls, v: str) -> str:
        if v not in VALID_DEPARTMENTS:
            raise ValueError(f"Invalid department '{v}'. Must be one of: {sorted(VALID_DEPARTMENTS)}")
        return v

    @field_validator("classification")
    @classmethod
    def validate_classification(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_CLASSIFICATIONS:
            raise ValueError(f"Invalid classification '{v}'. Must be one of: {sorted(VALID_CLASSIFICATIONS)}")
        return v_upper

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{v}'. Must be one of: {sorted(VALID_STATUSES)}")
        return v_upper

    @field_validator("allowed_roles")
    @classmethod
    def validate_roles(cls, v: List[str]) -> List[str]:
        for role in v:
            if role not in VALID_ROLES:
                raise ValueError(f"Invalid role '{role}'. Must be one of: {sorted(VALID_ROLES)}")
        return v

    @field_validator("file_format")
    @classmethod
    def validate_file_format(cls, v: str) -> str:
        v_upper = v.upper()
        if v_upper not in VALID_FORMATS:
            raise ValueError(f"Invalid file format '{v}'. Must be one of: {sorted(VALID_FORMATS)}")
        return v_upper


class RegistryRootSchema(BaseModel):
    """Schema for the root document_registry.json structure."""
    dataset_name: str
    company: str
    version: str
    schema_info: Optional[Dict[str, Any]] = Field(default=None, alias="schema")
    documents: List[RegistryDocumentRecord]

    model_config = {
        "populate_by_name": True
    }
