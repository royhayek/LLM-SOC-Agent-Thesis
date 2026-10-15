"""Tests for the enforcing / logging_only safety switch (E7-06, SCRUM-85)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import yaml  # type: ignore[import-untyped]

from thesis.assemble.bundles import Bundle
from thesis.config import Safety
from thesis.prompts.render import render
from thesis.prompts.templates import recommendation as rec_template
from thesis.safety.stage import apply_safety
from thesis.safety.switch import MODES_PATH, SafetyMode
from thesis.schema.alert import Alert, FlowDetail
from thesis.schema.verdict import Verdict

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _bundle() -> Bundle:
    alert = Alert(
        alert_id="f1",
        source="flows",
        ts=T0,
        subject_device="iot-cam-01",
        detector_score=0.9,
        detector_label="syn_flood",
        detector_name="flow_classifier",
        detail=FlowDetail(
            flow_start=T0,
            duration_s=1.0,
            src_ip="10.77.0.22",
            src_port=5,
            dst_ip="192.0.2.1",
            dst_port=80,
            protocol="tcp",
            packets_fwd=10,
            packets_bwd=0,
            bytes_fwd=600,
            bytes_bwd=0,
        ),
    )
    return Bundle(
        bundle_id="iot-cam-01|w",
        device="iot-cam-01",
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label="syn_flood",
        episode_id="ep-1",
        sources=("flows",),
        alerts=(alert,),
    )


def _verdict(action: str) -> str:
    return json.dumps(
        {
            "classification": {"incident_type": "syn_flood", "confidence": 0.8},
            "recommendation": {"recommended_action": action, "severity": "high"},
            "affected_device": "iot-cam-01",
            "evidence": ["f1"],
        }
    )


def _run(action: str, safety: Safety) -> object:
    return apply_safety(
        _verdict(action),
        _bundle(),
        mode=SafetyMode.load(safety),
        bundle_id="b",
        config_hash="h",
        repetition=0,
    )


def test_enforcing_applies_the_rejection_policy_to_an_out_of_space_action() -> None:
    result = _run("launch_counterattack", Safety.ENFORCING)
    assert result.validator_outcome == "reject"
    assert result.rejection_reason == "action_out_of_space"
    assert result.policy_action == "hard_fail"
    assert result.emitted is None  # E = ∅
    assert result.audit.emitted is False


def test_logging_only_passes_the_same_completion_through_and_records_would_reject() -> None:
    result = _run("launch_counterattack", Safety.LOGGING_ONLY)
    assert result.validator_outcome == "would_reject"
    assert result.rejection_reason == "action_out_of_space"
    assert result.policy_action == "not_applied"
    assert isinstance(result.emitted, str) and result.emitted  # E = R, emitted unchanged
    assert result.audit.validator_outcome == "would_reject"
    assert result.audit.emitted is True


def test_enforcing_emits_a_valid_verdict() -> None:
    result = _run("rate_limit_source", Safety.ENFORCING)
    assert result.validator_outcome == "pass"
    assert isinstance(result.emitted, Verdict)
    assert result.policy_action == "emit"


def test_node3_prompt_contains_the_full_catalog_in_both_modes() -> None:
    prompt = render(rec_template.TEMPLATE, "{}")  # the prompt does not depend on the safety mode
    for action_id in ("no_action", "isolate_device", "rate_limit_source", "disable_service"):
        assert action_id in prompt
    modes = yaml.safe_load(MODES_PATH.read_text(encoding="utf-8"))
    assert modes["enforcing"]["catalog_in_prompt"] is True
    assert modes["logging_only"]["catalog_in_prompt"] is True


def test_switch_matches_the_frozen_e0_12_list() -> None:
    enforcing = SafetyMode.load(Safety.ENFORCING)
    logging_only = SafetyMode.load(Safety.LOGGING_ONLY)
    # §6.1: both prompt mechanisms and the audit log stay on in both modes.
    for mode in (enforcing, logging_only):
        assert mode.catalog_in_prompt and mode.schema_in_prompt and mode.audit_log
    # The three enforcement mechanisms are on only under enforcing.
    assert (
        enforcing.constrained_decoding and enforcing.validator_gate and enforcing.rejection_policy
    )
    assert not logging_only.constrained_decoding
    assert not logging_only.validator_gate
    assert not logging_only.rejection_policy
