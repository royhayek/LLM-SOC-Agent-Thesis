"""Tests for the append-only audit log (E7-05, SCRUM-76)."""

from __future__ import annotations

import json
from pathlib import Path

from thesis.safety.audit import AuditRecord, records_from_outcome, write_audit
from thesis.safety.rejection import apply_rejection_policy
from thesis.safety.validator import Rejection, RejectionReason
from thesis.schema.verdict import Verdict

VERDICT = Verdict.model_validate(
    {
        "classification": {"incident_type": "syn_flood", "confidence": 0.8},
        "recommendation": {"recommended_action": "rate_limit_source", "severity": "high"},
        "affected_device": "iot-cam-01",
        "evidence": ["f1"],
    }
)
REJECT = Rejection(RejectionReason.UNKNOWN_EVIDENCE, detail=["ghost"])


def test_rejected_and_accepted_attempts_each_write_a_record(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    rejected = apply_rejection_policy(lambda i: REJECT, bundle_id="b-rej")
    accepted = apply_rejection_policy(lambda i: VERDICT, bundle_id="b-ok")
    write_audit(
        records_from_outcome(rejected, bundle_id="b-rej", config_hash="h", repetition=0), path
    )
    write_audit(
        records_from_outcome(accepted, bundle_id="b-ok", config_hash="h", repetition=0), path
    )

    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(rows) == 2
    rej, ok = rows
    assert rej["validator_outcome"] == "reject"
    assert rej["rejection_reason"] == "unknown_evidence"
    assert rej["policy_action"] == "hard_fail"
    assert rej["emitted"] is False
    assert rej["bundle_id"] == "b-rej" and rej["config_hash"] == "h"
    assert rej["call_ref"] == "h:b-rej:r0:recommendation"  # joins to the call log
    assert ok["validator_outcome"] == "pass" and ok["emitted"] is True


def test_writer_is_append_only(tmp_path: Path) -> None:
    path = tmp_path / "audit.jsonl"
    path.write_text('{"pre":"existing"}\n', encoding="utf-8")
    rec = AuditRecord(
        bundle_id="b",
        config_hash="h",
        repetition=0,
        node="recommendation",
        attempt=1,
        validator_outcome="pass",
        rejection_reason=None,
        policy_action="emit",
        emitted=True,
        call_ref="h:b:r0:recommendation",
    )
    write_audit([rec], path)
    lines = path.read_text(encoding="utf-8").splitlines()
    assert lines[0] == '{"pre":"existing"}'  # pre-existing line kept: opened in append mode
    assert json.loads(lines[1])["bundle_id"] == "b"
