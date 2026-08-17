"""
llm_service.py — Gemini LLM integration.
Calls Gemini API, extracts structured Action objects from natural language.
"""
from __future__ import annotations

import asyncio
import json
import re
from typing import Any, Dict, Optional

import google.generativeai as genai

from app.config import settings
from app.core.exceptions import LLMError, LLMTimeoutError, LLMParseError
from app.core.logger import service_logger
from app.prompts.system_prompt import SYSTEM_PROMPT
from app.prompts.governance_prompt import GOVERNANCE_EXTRACTION_PROMPT


class LLMService:
    """
    Wraps the Gemini generative model.
    Responsible for calling the API and parsing the JSON response.
    """

    def __init__(self) -> None:
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self._model = genai.GenerativeModel(
                model_name=settings.GEMINI_MODEL,
                generation_config=genai.types.GenerationConfig(
                    temperature=settings.LLM_TEMPERATURE,
                    max_output_tokens=settings.LLM_MAX_TOKENS,
                    response_mime_type="application/json",
                ),
                system_instruction=SYSTEM_PROMPT,
            )
        else:
            self._model = None
            service_logger.warning("GEMINI_API_KEY not set — LLM calls will use mock fallback")

    async def extract_action(
        self,
        natural_language: str,
        conversation_id: Optional[str] = None,
        department: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Convert a natural language request into a structured Action dict.
        Falls back to a mock response when API key is absent (dev mode).
        """
        if self._model is None:
            return self._mock_extraction(natural_language)

        prompt = GOVERNANCE_EXTRACTION_PROMPT.format(
            natural_language=natural_language,
            department=department or "General",
        )

        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.generate_content(prompt),
                ),
                timeout=settings.LLM_TIMEOUT,
            )
        except asyncio.TimeoutError:
            raise LLMTimeoutError(settings.LLM_TIMEOUT)
        except Exception as exc:
            raise LLMError(f"Gemini API error: {exc}") from exc

        raw_text = response.text.strip()
        return self._parse_json_response(raw_text, natural_language)

    async def generate_response(
        self,
        user_message: str,
        action_preview: Optional[Dict[str, Any]] = None,
        conversation_history: Optional[list] = None,
    ) -> str:
        """
        Generate a conversational response for the chat assistant.
        """
        if self._model is None:
            return self._mock_chat_response(user_message, action_preview)

        history_text = ""
        if conversation_history:
            history_text = "\n".join(
                f"{m['role'].capitalize()}: {m['content']}"
                for m in conversation_history[-6:]  # last 3 turns
            )

        ctx = ""
        if action_preview:
            ctx = f"\n\nGenerated Action:\n{json.dumps(action_preview, indent=2)}"

        prompt = (
            f"{history_text}\n\nUser: {user_message}{ctx}\n\n"
            "Provide a professional, concise response explaining what action has been "
            "extracted and what will happen next in the governance workflow. "
            "Do not use markdown. Keep it under 3 sentences."
        )

        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._model.generate_content(prompt),
                ),
                timeout=settings.LLM_TIMEOUT,
            )
            return response.text.strip()
        except asyncio.TimeoutError:
            raise LLMTimeoutError(settings.LLM_TIMEOUT)
        except Exception as exc:
            raise LLMError(f"Chat generation failed: {exc}") from exc

    # ── JSON Parsing ──────────────────────────────────────────
    def _parse_json_response(self, raw: str, original: str) -> Dict[str, Any]:
        # Strip markdown code fences if present
        clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`").strip()
        try:
            data = json.loads(clean)
            self._fill_defaults(data, original)
            return data
        except json.JSONDecodeError as exc:
            service_logger.error("LLM JSON parse failed", extra={"raw": raw[:300], "error": str(exc)})
            raise LLMParseError(raw)

    @staticmethod
    def _fill_defaults(data: Dict[str, Any], original: str) -> None:
        defaults = {
            "intent":              data.get("intent", original[:120]),
            "operation_type":      data.get("operation_type", "READ"),
            "target_resource":     data.get("target_resource", "unknown"),
            "target_table":        data.get("target_table"),
            "affected_records":    data.get("affected_records", 0),
            "action_json":         data.get("action_json", {"query": original}),
            "parameters":          data.get("parameters", {}),
            "reversibility":       data.get("reversibility", "reversible"),
            "data_scope":          data.get("data_scope", "single_record"),
            "regulatory_category": data.get("regulatory_category", "none"),
            "confidence":          float(data.get("confidence", 0.75)),
            "department":          data.get("department"),
        }
        data.update({k: v for k, v in defaults.items() if k not in data or data[k] is None})

    # ── Mock (dev without API key / fallback) ────────────────────
    @staticmethod
    def _mock_extraction(text: str) -> Dict[str, Any]:
        """Dynamically parses natural language requests into structured Action contracts."""
        t = text.lower()

        # Determine operation type (must be valid OperationType enum)
        if any(w in t for w in ["delete", "drop", "destroy", "purge", "remove", "truncate"]):
            op = "BULK_DELETE" if "all" in t or "many" in t else "DELETE"
            reversibility = "irreversible"
            scope = "all_records" if op == "BULK_DELETE" else "medium_batch"
            affected = 150
            dept = "Database Admin"
        elif any(w in t for w in ["scale", "shutdown", "terminate", "stop", "restart", "reboot", "down", "reduce"]):
            op = "BULK_UPDATE"
            reversibility = "reversible"
            scope = "medium_batch"
            affected = 12
            dept = "Operations"
        elif any(w in t for w in ["create", "add", "insert", "new"]):
            op = "CREATE"
            reversibility = "reversible"
            scope = "single_record"
            affected = 1
            dept = "Engineering"
        elif any(w in t for w in ["write", "update", "modify", "rotate", "change"]):
            op = "UPDATE"
            reversibility = "reversible"
            scope = "small_batch"
            affected = 25
            dept = "Engineering"
        elif any(w in t for w in ["export", "report", "download", "compliance", "gdpr"]):
            op = "EXPORT"
            reversibility = "reversible"
            scope = "large_batch"
            affected = 500
            dept = "Compliance"
        elif any(w in t for w in ["archive", "log", "backup"]):
            op = "ARCHIVE"
            reversibility = "reversible"
            scope = "large_batch"
            affected = 1000
            dept = "Database Admin"
        else:
            op = "READ"
            reversibility = "reversible"
            scope = "single_record" if "single" in t else "small_batch"
            affected = 10
            dept = "Engineering"

        # Determine target resource & table
        if any(w in t for w in ["kubernetes", "k8s", "cluster", "node", "pod"]):
            res = "staging-k8s-cluster"
            tbl = "k8s_clusters"
        elif any(w in t for w in ["s3", "bucket", "storage", "cloud"]):
            res = "production-s3-buckets"
            tbl = "s3_buckets"
        elif any(w in t for w in ["key", "credential", "api key", "service account"]):
            res = "iam_service_keys"
            tbl = "service_accounts"
        elif any(w in t for w in ["ssh", "firewall", "ip", "port"]):
            res = "prod_firewall_rules"
            tbl = "firewall_rules"
        elif any(w in t for w in ["log", "archive", "audit"]):
            res = "audit_logs_archive"
            tbl = "audit_logs"
        elif any(w in t for w in ["gdpr", "report", "compliance"]):
            res = "gdpr_compliance_reports"
            tbl = "compliance_logs"
        elif any(w in t for w in ["employee", "user", "account", "profile"]):
            res = "employees table"
            tbl = "employees"
        else:
            res = "production_database"
            tbl = "core_data"

        intent = text.strip()
        if len(intent) > 100:
            intent = intent[:97] + "..."

        return {
            "intent":              intent,
            "operation_type":      op,
            "target_resource":     res,
            "target_table":        tbl,
            "affected_records":    affected,
            "reversibility":       reversibility,
            "data_scope":          scope,
            "regulatory_category": "gdpr" if "gdpr" in t else ("soc2" if op in ["DELETE", "SCALE_DOWN"] else "none"),
            "confidence":          0.88 if len(text) > 10 else 0.72,
            "department":          dept,
            "action_json": {
                "operation": op,
                "target_resource": res,
                "table": tbl,
                "affected_records": affected,
                "natural_language": text,
            },
            "parameters": {"natural_language": text},
        }

    @staticmethod
    def _mock_chat_response(message: str, action: Optional[Dict[str, Any]]) -> str:
        if action:
            op = action.get('operation_type', 'READ')
            res = action.get('target_resource', 'target resource')
            intent = action.get('intent', message)
            return (
                f"I have analysed your request ('{intent}') and structured a {op} action "
                f"targeting {res}. The action has been submitted to the THRESHOLD AI "
                "governance pipeline for policy evaluation and risk assessment."
            )
        return (
            "I have received your request and am processing it through the THRESHOLD AI "
            "governance pipeline. Please review the action details in the Action Preview panel."
        )


# ── Module-level singleton ────────────────────────────────────
llm_service = LLMService()
