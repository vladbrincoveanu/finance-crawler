from __future__ import annotations

import json
import os
from collections.abc import Sequence
from typing import Any, Literal

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..models.identity import IdentityCandidate
from .candidates import CandidateOption


class _ModelResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject", "defer", "create_new"]
    candidate_id: str | None = None
    confidence: float = Field(ge=0, le=1)
    reason_codes: list[str]


class ResolutionSuggestion(BaseModel):
    decision: Literal["approve", "reject", "defer", "create_new", "pending"]
    candidate_id: str | None = None
    confidence: float | None = None
    reason_codes: list[str] = Field(default_factory=list)
    provider: str = "deepinfra"
    request_status: str
    model_name: str
    prompt_version: str
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cached_tokens: int = 0
    error_message: str | None = None


class DeepInfraAdjudicator:
    model = "deepseek-ai/DeepSeek-V4-Flash-0731"
    base_url = "https://api.deepinfra.com/v1/openai"
    prompt_version = "identity-resolution-v1"

    def __init__(self, timeout: float = 20.0, session: Session | None = None):
        self.timeout = timeout
        self.session = session

    def suggest(
        self,
        entity_type: Literal["investor", "security"],
        source_record: dict[str, Any],
        candidates: Sequence[CandidateOption],
    ) -> ResolutionSuggestion:
        api_key = os.getenv("DEEPINFRA_API_KEY")
        if not api_key:
            return self._pending(
                "missing_api_key",
                entity_type=entity_type,
                source_record=source_record,
                candidates=candidates,
            )

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self._system_prompt()},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "entity_type": entity_type,
                            "source_record": source_record,
                            "candidates": [candidate.__dict__ for candidate in candidates],
                        },
                        default=str,
                        sort_keys=True,
                    ),
                },
            ],
            "temperature": 0,
            "max_tokens": 256,
            "prompt_cache_key": f"{self.model}:{self.prompt_version}:{entity_type}",
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "identity_resolution",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "additionalProperties": False,
                        "properties": {
                            "decision": {
                                "type": "string",
                                "enum": ["approve", "reject", "defer", "create_new"],
                            },
                            "candidate_id": {"type": ["string", "null"]},
                            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                            "reason_codes": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["decision", "candidate_id", "confidence", "reason_codes"],
                    },
                },
            },
        }

        try:
            with httpx.Client(
                base_url=self.base_url,
                headers={"Authorization": f"Bearer {api_key}"},
                timeout=self.timeout,
            ) as client:
                response = client.post("/chat/completions", json=payload)
                response.raise_for_status()
        except httpx.TimeoutException as error:
            return self._pending(
                "timeout",
                str(error),
                entity_type=entity_type,
                source_record=source_record,
                candidates=candidates,
            )
        except httpx.HTTPError as error:
            return self._pending(
                "http_error",
                str(error),
                entity_type=entity_type,
                source_record=source_record,
                candidates=candidates,
            )

        try:
            response_body = response.json()
            content = response_body["choices"][0]["message"]["content"]
            parsed = _ModelResponse.model_validate_json(content)
            candidate_ids = {candidate.candidate_id for candidate in candidates}
            if parsed.candidate_id is not None and parsed.candidate_id not in candidate_ids:
                return self._pending(
                    "invalid_response",
                    "unknown candidate_id",
                    entity_type=entity_type,
                    source_record=source_record,
                    candidates=candidates,
                )
        except (KeyError, IndexError, TypeError, ValueError, ValidationError) as error:
            return self._pending(
                "invalid_response",
                str(error),
                entity_type=entity_type,
                source_record=source_record,
                candidates=candidates,
            )

        usage = response_body.get("usage") or {}
        prompt_details = usage.get("prompt_tokens_details") or {}
        return ResolutionSuggestion(
            decision=parsed.decision,
            candidate_id=parsed.candidate_id,
            confidence=parsed.confidence,
            reason_codes=parsed.reason_codes,
            request_status="complete",
            model_name=self.model,
            prompt_version=self.prompt_version,
            prompt_tokens=usage.get("prompt_tokens", 0),
            completion_tokens=usage.get("completion_tokens", 0),
            cached_tokens=prompt_details.get("cached_tokens", 0),
        )

    def _system_prompt(self) -> str:
        return (
            "You provide identity suggestions only. Never invent facts, never write the database, "
            "and choose only from opaque candidate IDs. Return the requested strict JSON schema. "
            f"Model={self.model}; prompt_version={self.prompt_version}."
        )

    def _pending(
        self,
        status: str,
        error_message: str | None = None,
        *,
        entity_type: Literal["investor", "security"] | None = None,
        source_record: dict[str, Any] | None = None,
        candidates: Sequence[CandidateOption] = (),
    ) -> ResolutionSuggestion:
        suggestion = ResolutionSuggestion(
            decision="pending",
            request_status=status,
            model_name=self.model,
            prompt_version=self.prompt_version,
            error_message=error_message,
        )
        if entity_type and source_record:
            self._persist_pending(entity_type, source_record, candidates, status)
        return suggestion

    def _persist_pending(
        self,
        entity_type: Literal["investor", "security"],
        source_record: dict[str, Any],
        candidates: Sequence[CandidateOption],
        request_status: str,
    ) -> None:
        if self.session is None:
            return
        run_id = source_record.get("run_id")
        source_record_id = source_record.get("id")
        if not run_id or not source_record_id:
            return
        first_candidate = candidates[0] if candidates else None
        row = IdentityCandidate(
            run_id=str(run_id),
            entity_type=entity_type,
            source_record_id=str(source_record_id)[:36],
            candidate_entity_id=(
                first_candidate.candidate_entity_id if first_candidate else None
            ),
            deterministic_score=(
                first_candidate.deterministic_score if first_candidate else None
            ),
            evidence_json={
                "request_status": request_status,
                "model_name": self.model,
                "prompt_version": self.prompt_version,
            },
            status="pending",
        )
        try:
            self.session.add(row)
            self.session.commit()
        except SQLAlchemyError:
            self.session.rollback()
