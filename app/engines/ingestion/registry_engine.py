"""
registry_engine.py — Loads, validates, and parses the enterprise document registry.
"""
import json
from pathlib import Path
from typing import List, Union, Optional
from app.schemas.registry_schema import RegistryRootSchema, RegistryDocumentRecord
from app.schemas.document_schema import DocumentMetadataSchema
from app.utils.file_utils import resolve_path, get_file_extension
from app.core.exceptions import RegistryValidationError
from app.core.logger import ingestion_logger


class RegistryEngine:
    """Loads and validates metadata/document_registry.json."""

    def __init__(self, registry_path: Union[str, Path], dataset_base_dir: Optional[Union[str, Path]] = None):
        self.registry_path = Path(registry_path).resolve()
        if dataset_base_dir:
            self.dataset_base_dir = Path(dataset_base_dir).resolve()
        else:
            # Assume registry_path is inside <dataset_base>/metadata/document_registry.json
            self.dataset_base_dir = self.registry_path.parent.parent.resolve()

    def load_and_validate(self) -> List[DocumentMetadataSchema]:
        """
        Parse document_registry.json, validate schema, check uniqueness,
        and ensure all source documents exist.
        Returns a list of validated DocumentMetadataSchema instances.
        """
        ingestion_logger.info(f"Loading document registry from {self.registry_path}")

        if not self.registry_path.exists():
            raise RegistryValidationError(f"Document registry file not found at: {self.registry_path}")

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                raw_json = json.load(f)
        except json.JSONDecodeError as e:
            raise RegistryValidationError(f"Failed to parse registry JSON: {str(e)}")
        except Exception as e:
            raise RegistryValidationError(f"Error reading registry file: {str(e)}")

        try:
            root = RegistryRootSchema.model_validate(raw_json)
        except Exception as e:
            raise RegistryValidationError(f"Registry schema validation failed: {str(e)}")

        seen_ids = set()
        validated_docs: List[DocumentMetadataSchema] = []

        for record in root.documents:
            doc_id = record.document_id

            # Check duplicate IDs
            if doc_id in seen_ids:
                raise RegistryValidationError(f"Duplicate document_id detected in registry: '{doc_id}'")
            seen_ids.add(doc_id)

            # Validate source document path resolution
            resolved_source = resolve_path(self.dataset_base_dir, record.file_path)
            if not resolved_source.exists():
                raise RegistryValidationError(
                    f"Document '{doc_id}' points to non-existent file: '{record.file_path}' (resolved: '{resolved_source}')"
                )

            # Validate format matches extension
            actual_ext = get_file_extension(resolved_source).upper()
            if actual_ext != record.file_format.upper():
                raise RegistryValidationError(
                    f"Document '{doc_id}' format mismatch: metadata declares '{record.file_format}' but file extension is '.{actual_ext.lower()}'"
                )

            metadata_schema = DocumentMetadataSchema(
                document_id=record.document_id,
                title=record.title,
                department=record.department,
                classification=record.classification,
                version=record.version,
                status=record.status,
                effective_date=record.effective_date,
                allowed_roles=record.allowed_roles,
                document_type=record.document_type,
                summary=record.summary,
                keywords=record.keywords,
                file_path=record.file_path,
                file_format=record.file_format,
            )
            validated_docs.append(metadata_schema)

        ingestion_logger.info(f"Successfully validated {len(validated_docs)} document records from registry.")
        return validated_docs
