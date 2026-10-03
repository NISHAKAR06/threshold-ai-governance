"""
exceptions.py — Custom application exceptions with HTTP status codes.
"""
from fastapi import HTTPException, status


class THRESHOLDBaseException(Exception):
    """Root exception for all THRESHOLD AI errors."""
    def __init__(self, message: str, code: str = "THRESHOLD_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


# ── Authentication & Authorisation ───────────────────────────
class AuthenticationError(THRESHOLDBaseException):
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, "AUTH_ERROR")


class AuthorisationError(THRESHOLDBaseException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(message, "AUTHZ_ERROR")


class TokenExpiredError(THRESHOLDBaseException):
    def __init__(self):
        super().__init__("Token has expired", "TOKEN_EXPIRED")


# ── Validation ────────────────────────────────────────────────
class ValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")


# ── Database ──────────────────────────────────────────────────
class DatabaseError(THRESHOLDBaseException):
    def __init__(self, message: str = "Database operation failed"):
        super().__init__(message, "DB_ERROR")


class RecordNotFoundError(THRESHOLDBaseException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(f"{resource} with id '{identifier}' not found", "NOT_FOUND")
        self.resource   = resource
        self.identifier = identifier


class DuplicateRecordError(THRESHOLDBaseException):
    def __init__(self, resource: str, field: str):
        super().__init__(f"{resource} with that {field} already exists", "DUPLICATE")


class RollbackError(THRESHOLDBaseException):
    def __init__(self, action_id: str, reason: str):
        super().__init__(
            f"Rollback failed for action {action_id}: {reason}",
            "ROLLBACK_ERROR"
        )
        self.action_id = action_id
        self.reason    = reason


# ── LLM / AI ──────────────────────────────────────────────────
class LLMError(THRESHOLDBaseException):
    def __init__(self, message: str = "LLM API call failed"):
        super().__init__(message, "LLM_ERROR")


class LLMTimeoutError(THRESHOLDBaseException):
    def __init__(self, timeout_seconds: int):
        super().__init__(
            f"LLM request timed out after {timeout_seconds}s",
            "LLM_TIMEOUT"
        )


class LLMParseError(THRESHOLDBaseException):
    def __init__(self, raw_response: str):
        super().__init__(
            "Failed to parse structured action from LLM response",
            "LLM_PARSE_ERROR"
        )
        self.raw_response = raw_response


# ── Governance / Engines ──────────────────────────────────────
class PolicyBlockedError(THRESHOLDBaseException):
    def __init__(self, rule: str, reason: str):
        super().__init__(f"Action blocked by policy '{rule}': {reason}", "POLICY_BLOCKED")
        self.rule   = rule
        self.reason = reason


class RiskCalculationError(THRESHOLDBaseException):
    def __init__(self, message: str):
        super().__init__(message, "RISK_CALC_ERROR")


class InvalidDecisionError(THRESHOLDBaseException):
    def __init__(self, decision: str):
        super().__init__(f"Invalid decision type: {decision}", "INVALID_DECISION")


# ── Execution ─────────────────────────────────────────────────
class ExecutionError(THRESHOLDBaseException):
    def __init__(self, action_id: str, reason: str):
        super().__init__(f"Execution failed for action {action_id}: {reason}", "EXEC_ERROR")
        self.action_id = action_id
        self.reason    = reason


class ActionNotApprovedError(THRESHOLDBaseException):
    def __init__(self, action_id: str, status: str):
        super().__init__(
            f"Action {action_id} cannot be executed — current status: {status}",
            "NOT_APPROVED"
        )


class ActionAlreadyExecutedError(THRESHOLDBaseException):
    def __init__(self, action_id: str):
        super().__init__(f"Action {action_id} has already been executed", "ALREADY_EXECUTED")


# ── WebSocket ─────────────────────────────────────────────────
class WebSocketError(THRESHOLDBaseException):
    def __init__(self, message: str):
        super().__init__(message, "WS_ERROR")


# ── Ingestion Pipeline ─────────────────────────────────────────
class RegistryValidationError(THRESHOLDBaseException):
    def __init__(self, message: str):
        super().__init__(message, "REGISTRY_VALIDATION_ERROR")


class DocumentIngestionError(THRESHOLDBaseException):
    def __init__(self, message: str, document_id: str = None):
        self.document_id = document_id
        super().__init__(message, "DOCUMENT_INGESTION_ERROR")


class DocumentValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, document_id: str = None):
        self.document_id = document_id
        super().__init__(message, "DOCUMENT_VALIDATION_ERROR")


class LoaderError(THRESHOLDBaseException):
    def __init__(self, message: str, file_path: str = None):
        self.file_path = file_path
        super().__init__(message, "LOADER_ERROR")


class UnsupportedFormatError(THRESHOLDBaseException):
    def __init__(self, format_name: str):
        super().__init__(f"Unsupported document format: '{format_name}'", "UNSUPPORTED_FORMAT")


# ── Chunking Pipeline (Phase 9) ───────────────────────────────
class ChunkingError(THRESHOLDBaseException):
    def __init__(self, message: str, document_id: str = None):
        self.document_id = document_id
        super().__init__(message, "CHUNKING_ERROR")


class ChunkValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, chunk_id: str = None):
        self.chunk_id = chunk_id
        super().__init__(message, "CHUNK_VALIDATION_ERROR")


class InvalidChunkConfigurationError(THRESHOLDBaseException):
    def __init__(self, message: str):
        super().__init__(message, "INVALID_CHUNK_CONFIG")


class EmptyDocumentError(THRESHOLDBaseException):
    def __init__(self, message: str = "Document content is empty or contains only whitespace", document_id: str = None):
        self.document_id = document_id
        super().__init__(message, "EMPTY_DOCUMENT")


class ChunkPersistenceError(THRESHOLDBaseException):
    def __init__(self, message: str, target_path: str = None):
        self.target_path = target_path
        super().__init__(message, "CHUNK_PERSISTENCE_ERROR")


# ── Embedding & Vector Index Pipeline (Phase 10) ──────────────
class EmbeddingError(THRESHOLDBaseException):
    def __init__(self, message: str, provider: str = None):
        self.provider = provider
        super().__init__(message, "EMBEDDING_ERROR")


class EmbeddingValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, vector_id: str = None):
        self.vector_id = vector_id
        super().__init__(message, "EMBEDDING_VALIDATION_ERROR")


class VectorStoreError(THRESHOLDBaseException):
    def __init__(self, message: str, provider: str = None):
        self.provider = provider
        super().__init__(message, "VECTOR_STORE_ERROR")


class VectorPersistenceError(THRESHOLDBaseException):
    def __init__(self, message: str, collection: str = None):
        self.collection = collection
        super().__init__(message, "VECTOR_PERSISTENCE_ERROR")


class InvalidEmbeddingConfigurationError(THRESHOLDBaseException):
    def __init__(self, message: str):
        super().__init__(message, "INVALID_EMBEDDING_CONFIG")


class ChunkEmbeddingError(THRESHOLDBaseException):
    def __init__(self, message: str, chunk_id: str = None):
        self.chunk_id = chunk_id
        super().__init__(message, "CHUNK_EMBEDDING_ERROR")


# ── Semantic Retrieval Pipeline (Phase 11) ───────────────────
class InvalidRetrievalQueryError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "INVALID_RETRIEVAL_QUERY"):
        super().__init__(message, code)


class QueryValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "QUERY_VALIDATION_ERROR"):
        super().__init__(message, code)


class QueryEmbeddingError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "QUERY_EMBEDDING_ERROR"):
        super().__init__(message, code)


class RetrievalError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "RETRIEVAL_ERROR"):
        super().__init__(message, code)


class VectorSearchError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "VECTOR_SEARCH_ERROR"):
        super().__init__(message, code)


# ── Hybrid & Governance-Aware Retrieval Pipeline (Phase 12) ────
class AccessContextValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "ACCESS_CONTEXT_VALIDATION_ERROR"):
        super().__init__(message, code)


class KeywordSearchError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "KEYWORD_SEARCH_ERROR"):
        super().__init__(message, code)


class HybridRetrievalError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "HYBRID_RETRIEVAL_ERROR"):
        super().__init__(message, code)


class GovernanceFilteringError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "GOVERNANCE_FILTERING_ERROR"):
        super().__init__(message, code)


class AccessDeniedError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "ACCESS_DENIED_ERROR"):
        super().__init__(message, code)


# ── Governance-Aware RAG Answer Generation (Phase 13) ─────────
class RAGError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "RAG_ERROR"):
        super().__init__(message, code)


class ContextBuildError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "CONTEXT_BUILD_ERROR"):
        super().__init__(message, code)


class ContextValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "CONTEXT_VALIDATION_ERROR"):
        super().__init__(message, code)


class PromptBuildError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "PROMPT_BUILD_ERROR"):
        super().__init__(message, code)


class LLMGenerationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "LLM_GENERATION_ERROR"):
        super().__init__(message, code)


class AnswerValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "ANSWER_VALIDATION_ERROR"):
        super().__init__(message, code)


class InsufficientContextError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "INSUFFICIENT_CONTEXT_ERROR"):
        super().__init__(message, code)


# ── Controlled AI Agent & Governance Workflow (Phase 14) ────
class AgentValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "AGENT_VALIDATION_ERROR"):
        super().__init__(message, code)


class AgentRoutingError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "AGENT_ROUTING_ERROR"):
        super().__init__(message, code)


class ToolNotRegisteredError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "TOOL_NOT_REGISTERED"):
        super().__init__(message, code)


class ToolAuthorizationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "TOOL_AUTHORIZATION_ERROR"):
        super().__init__(message, code)


class ToolExecutionError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "TOOL_EXECUTION_ERROR"):
        super().__init__(message, code)


class AgentPolicyError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "AGENT_POLICY_ERROR"):
        super().__init__(message, code)


class ToolOutputValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "TOOL_OUTPUT_VALIDATION_ERROR"):
        super().__init__(message, code)


# ── Production Readiness & Responsible AI (Phase 15) ─────────
class ResponsibleAIValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "RESPONSIBLE_AI_VALIDATION_ERROR"):
        super().__init__(message, code)


class PromptInjectionDetectedError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "PROMPT_INJECTION_DETECTED"):
        super().__init__(message, code)


class OutputGuardValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "OUTPUT_GUARD_VALIDATION_ERROR"):
        super().__init__(message, code)


class ConfigurationValidationError(THRESHOLDBaseException):
    def __init__(self, message: str, code: str = "CONFIGURATION_VALIDATION_ERROR"):
        super().__init__(message, code)


# ── HTTP exception factory ────────────────────────────────────
def to_http_exception(exc: THRESHOLDBaseException) -> HTTPException:
    """Convert a domain exception to an HTTPException."""
    status_map = {
        "AUTH_ERROR":                 status.HTTP_401_UNAUTHORIZED,
        "AUTHZ_ERROR":                status.HTTP_403_FORBIDDEN,
        "TOKEN_EXPIRED":              status.HTTP_401_UNAUTHORIZED,
        "NOT_FOUND":                  status.HTTP_404_NOT_FOUND,
        "DUPLICATE":                  status.HTTP_409_CONFLICT,
        "VALIDATION_ERROR":           status.HTTP_422_UNPROCESSABLE_ENTITY,
        "POLICY_BLOCKED":             status.HTTP_403_FORBIDDEN,
        "NOT_APPROVED":               status.HTTP_409_CONFLICT,
        "ALREADY_EXECUTED":           status.HTTP_409_CONFLICT,
        "LLM_TIMEOUT":                status.HTTP_504_GATEWAY_TIMEOUT,
        "REGISTRY_VALIDATION_ERROR":  status.HTTP_422_UNPROCESSABLE_ENTITY,
        "DOCUMENT_INGESTION_ERROR":   status.HTTP_500_INTERNAL_SERVER_ERROR,
        "DOCUMENT_VALIDATION_ERROR":  status.HTTP_422_UNPROCESSABLE_ENTITY,
        "LOADER_ERROR":               status.HTTP_500_INTERNAL_SERVER_ERROR,
        "UNSUPPORTED_FORMAT":         status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        "CHUNKING_ERROR":             status.HTTP_500_INTERNAL_SERVER_ERROR,
        "CHUNK_VALIDATION_ERROR":     status.HTTP_422_UNPROCESSABLE_ENTITY,
        "INVALID_CHUNK_CONFIG":       status.HTTP_400_BAD_REQUEST,
        "EMPTY_DOCUMENT":             status.HTTP_422_UNPROCESSABLE_ENTITY,
        "CHUNK_PERSISTENCE_ERROR":    status.HTTP_500_INTERNAL_SERVER_ERROR,
        "EMBEDDING_ERROR":            status.HTTP_500_INTERNAL_SERVER_ERROR,
        "EMBEDDING_VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "VECTOR_STORE_ERROR":         status.HTTP_500_INTERNAL_SERVER_ERROR,
        "VECTOR_PERSISTENCE_ERROR":   status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INVALID_EMBEDDING_CONFIG":   status.HTTP_400_BAD_REQUEST,
        "CHUNK_EMBEDDING_ERROR":      status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INVALID_RETRIEVAL_QUERY":    status.HTTP_400_BAD_REQUEST,
        "QUERY_VALIDATION_ERROR":     status.HTTP_400_BAD_REQUEST,
        "EMPTY_QUERY":                status.HTTP_400_BAD_REQUEST,
        "QUERY_TOO_SHORT":            status.HTTP_400_BAD_REQUEST,
        "QUERY_TOO_LONG":             status.HTTP_400_BAD_REQUEST,
        "INVALID_TOP_K":              status.HTTP_400_BAD_REQUEST,
        "QUERY_EMBEDDING_ERROR":      status.HTTP_500_INTERNAL_SERVER_ERROR,
        "RETRIEVAL_ERROR":            status.HTTP_500_INTERNAL_SERVER_ERROR,
        "VECTOR_SEARCH_ERROR":        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "ACCESS_CONTEXT_VALIDATION_ERROR": status.HTTP_400_BAD_REQUEST,
        "KEYWORD_SEARCH_ERROR":       status.HTTP_500_INTERNAL_SERVER_ERROR,
        "HYBRID_RETRIEVAL_ERROR":     status.HTTP_500_INTERNAL_SERVER_ERROR,
        "GOVERNANCE_FILTERING_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
        "ACCESS_DENIED_ERROR":        status.HTTP_403_FORBIDDEN,
        "RAG_ERROR":                  status.HTTP_500_INTERNAL_SERVER_ERROR,
        "CONTEXT_BUILD_ERROR":        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "CONTEXT_VALIDATION_ERROR":   status.HTTP_422_UNPROCESSABLE_ENTITY,
        "PROMPT_BUILD_ERROR":         status.HTTP_500_INTERNAL_SERVER_ERROR,
        "LLM_GENERATION_ERROR":       status.HTTP_502_BAD_GATEWAY,
        "ANSWER_VALIDATION_ERROR":    status.HTTP_500_INTERNAL_SERVER_ERROR,
        "INSUFFICIENT_CONTEXT_ERROR": status.HTTP_404_NOT_FOUND,
        "AGENT_VALIDATION_ERROR":     status.HTTP_422_UNPROCESSABLE_ENTITY,
        "AGENT_ROUTING_ERROR":        status.HTTP_400_BAD_REQUEST,
        "TOOL_NOT_REGISTERED":        status.HTTP_404_NOT_FOUND,
        "TOOL_AUTHORIZATION_ERROR":   status.HTTP_403_FORBIDDEN,
        "TOOL_EXECUTION_ERROR":       status.HTTP_500_INTERNAL_SERVER_ERROR,
        "AGENT_POLICY_ERROR":         status.HTTP_403_FORBIDDEN,
        "TOOL_OUTPUT_VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "RESPONSIBLE_AI_VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "PROMPT_INJECTION_DETECTED":  status.HTTP_400_BAD_REQUEST,
        "OUTPUT_GUARD_VALIDATION_ERROR": status.HTTP_422_UNPROCESSABLE_ENTITY,
        "CONFIGURATION_VALIDATION_ERROR": status.HTTP_500_INTERNAL_SERVER_ERROR,
    }
    http_status = status_map.get(exc.code, status.HTTP_500_INTERNAL_SERVER_ERROR)
    return HTTPException(
        status_code=http_status,
        detail={"code": exc.code, "message": exc.message},
    )


