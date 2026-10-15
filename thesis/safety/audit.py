"""The append-only JSONL audit log (E7-05, SCRUM-76).

The audit log is one of the four safety mechanisms (record §6.4): every validation attempt — passed
or not — produces one record linking the LLM call log (E0-10), the validator outcome and the bundle.
It is the evidence that the system is auditable. The file is **append-only**, never rewritten
(§6.7): one writer, one file.

Each record joins to `logs/llm_calls.jsonl` by `call_ref` — the (config_hash, bundle_id,
repetition, node) identity of the node-3 call it describes — and carries the §5 audit fields of the
rejection policy (validator outcome, rejection reason, policy action, whether it was emitted).
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from thesis.safety.rejection import PolicyOutcome

AUDIT_PATH = Path(__file__).resolve().parents[2] / "logs" / "audit.jsonl"
RECOMMENDATION_NODE = "recommendation"


class AuditRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    bundle_id: str = Field(min_length=1)
    config_hash: str = Field(min_length=1)
    repetition: int = Field(ge=0)
    node: str = Field(min_length=1)
    attempt: int = Field(ge=1)
    validator_outcome: str = Field(min_length=1)  # pass | reject | would_reject
    rejection_reason: str | None
    policy_action: str = Field(min_length=1)  # emit | hard_fail | not_applied
    emitted: bool
    call_ref: str = Field(min_length=1)  # joins to logs/llm_calls.jsonl


def _call_ref(config_hash: str, bundle_id: str, repetition: int, node: str) -> str:
    return f"{config_hash}:{bundle_id}:r{repetition}:{node}"


def records_from_outcome(
    outcome: PolicyOutcome,
    *,
    bundle_id: str,
    config_hash: str,
    repetition: int,
    node: str = RECOMMENDATION_NODE,
) -> list[AuditRecord]:
    """One audit record per attempt in a rejection-policy outcome (E7-04)."""
    emit_attempt = outcome.final_attempt.attempt if outcome.policy_action == "emit" else None
    ref = _call_ref(config_hash, bundle_id, repetition, node)
    return [
        AuditRecord(
            bundle_id=bundle_id,
            config_hash=config_hash,
            repetition=repetition,
            node=node,
            attempt=record.attempt,
            validator_outcome=record.validator_outcome,
            rejection_reason=record.rejection_reason,
            policy_action=outcome.policy_action,
            emitted=record.attempt == emit_attempt,
            call_ref=ref,
        )
        for record in outcome.attempts
    ]


def write_audit(records: list[AuditRecord], path: Path = AUDIT_PATH) -> None:
    """Append each record as one JSON line. The file is only ever opened for appending (§6.7)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as sink:  # append-only: earlier lines are never rewritten
        for record in records:
            sink.write(json.dumps(record.model_dump(), sort_keys=True) + "\n")


__all__ = ["AUDIT_PATH", "AuditRecord", "records_from_outcome", "write_audit"]
