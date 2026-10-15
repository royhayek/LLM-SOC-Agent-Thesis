"""Tests for the Baseline A strategy (E8-02, SCRUM-46)."""

from __future__ import annotations

import pytest

from thesis.baselines.baseline_a import FrozenModelError, baseline_a_verdict, verify_model
from thesis.schema.verdict import Verdict


def _view(label: str | None, score: float) -> dict[str, object]:
    view: dict[str, object] = {"device": "iot-cam-01", "sources": {"flows": "active"}}
    if label is not None:
        view["flows"] = {"count": 3, "detector": {"label": label, "max_score": score}}
    return view


def test_attack_bundle_maps_to_type_severity_and_action() -> None:
    v = baseline_a_verdict(_view("syn_flood", 0.95))
    assert isinstance(v, Verdict)
    assert v.classification.incident_type.value == "syn_flood"
    assert v.recommendation.severity.value == "critical"  # score 0.95 >= 0.9
    assert v.recommendation.recommended_action.value == "block_source"  # syn_flood/critical
    assert v.affected_device == "iot-cam-01"
    assert v.evidence == []  # Baseline A cites no evidence


def test_no_flows_block_is_benign_no_action() -> None:
    v = baseline_a_verdict(_view(None, 0.0))
    assert v.classification.incident_type.value == "benign"
    assert v.recommendation.recommended_action.value == "no_action"


def test_severity_bands() -> None:
    assert baseline_a_verdict(_view("botnet", 0.4)).recommendation.severity.value == "low"
    assert baseline_a_verdict(_view("botnet", 0.6)).recommendation.severity.value == "medium"
    assert baseline_a_verdict(_view("botnet", 0.8)).recommendation.severity.value == "high"


def test_is_deterministic() -> None:
    view = _view("mqtt_publish_flood", 0.92)
    assert baseline_a_verdict(view) == baseline_a_verdict(view)


def test_frozen_model_hash_is_checked() -> None:
    verify_model()  # the committed model matches the frozen hash
    with pytest.raises(FrozenModelError):
        verify_model(expected="0" * 64)
