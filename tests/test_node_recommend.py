"""Tests for node 3, constrained recommendation (E6-05, SCRUM-72). The LLM client is mocked."""

from __future__ import annotations

import json

import pytest

from thesis.agent.models import Classification
from thesis.agent.node_recommend import RecommendParseError, recommend

CLASSIFICATION = Classification(
    incident_type="syn_flood", severity="high", affected_device="iot-cam-01", confidence=0.8
)
GOOD = json.dumps({"recommended_action": "rate_limit_source", "evidence_ids": ["f1"]})


class FakeClient:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.prompt = ""

    def complete(
        self,
        prompt: str,
        *,
        node: str,
        bundle_id: str,
        config_hash: str,
        repetition: int,
        json_schema: dict[str, object] | None = None,
    ) -> str:
        self.prompt = prompt
        assert node == "recommendation"
        return self.reply


def _run(reply: str, evidence: list[str] | None = None) -> object:
    return recommend(
        CLASSIFICATION,
        evidence or ["f1"],
        client=FakeClient(reply),
        bundle_id="b",
        config_hash="c",
        repetition=0,
    )


def test_valid_output_parses_with_one_action_and_evidence() -> None:
    rec = _run(GOOD)
    assert rec.recommended_action.value == "rate_limit_source"
    assert rec.evidence_ids == ["f1"]


def test_prompt_contains_the_full_catalog_and_no_raw_exemplars() -> None:
    client = FakeClient(GOOD)
    recommend(CLASSIFICATION, ["f1"], client=client, bundle_id="b", config_hash="c", repetition=0)
    for action_id in ("no_action", "isolate_device", "rate_limit_source", "disable_service"):
        assert action_id in client.prompt  # full catalog present
    for exemplar_key in ("bytes_fwd", "exemplars", "src", "cmd"):
        assert exemplar_key not in client.prompt  # no raw exemplar text


def test_action_outside_the_catalog_is_a_parse_failure() -> None:
    with pytest.raises(RecommendParseError):
        _run(json.dumps({"recommended_action": "launch_counterattack", "evidence_ids": ["f1"]}))


def test_active_action_without_evidence_is_rejected() -> None:
    # An active action must cite evidence (METHODS changelog 21).
    with pytest.raises(RecommendParseError):
        _run(json.dumps({"recommended_action": "block_source", "evidence_ids": []}))


def test_non_response_actions_may_cite_no_evidence() -> None:
    # A benign verdict recommends no_action / monitor and need not invent evidence.
    for action in ("no_action", "monitor"):
        rec = _run(json.dumps({"recommended_action": action, "evidence_ids": []}))
        assert rec.recommended_action.value == action
        assert rec.evidence_ids == []
