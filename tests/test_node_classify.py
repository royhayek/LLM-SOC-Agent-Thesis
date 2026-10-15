"""Tests for node 2, structured classification (E6-04, SCRUM-61). The LLM client is mocked."""

from __future__ import annotations

import json

import pytest

from thesis.agent.models import Findings, SourceFinding
from thesis.agent.node_classify import ClassifyParseError, classify

FINDINGS = Findings(
    source_findings=[SourceFinding(source="flows", summary="SYN flood", evidence_ids=["f1"])],
    cross_source="flood on the camera, mqtt silent",
    candidate_hypotheses=["syn_flood"],
    missing_evidence=[],
)

GOOD = json.dumps(
    {
        "incident_type": "syn_flood",
        "severity": "high",
        "affected_device": "iot-cam-01",
        "confidence": 0.82,
    }
)


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
        assert node == "classification"
        return self.reply


def _run(reply: str) -> object:
    return classify(
        FINDINGS, client=FakeClient(reply), bundle_id="b", config_hash="c", repetition=0
    )


def test_valid_output_parses_into_classification() -> None:
    result = _run(GOOD)
    assert result.incident_type.value == "syn_flood"
    assert result.severity.value == "high"
    assert result.affected_device == "iot-cam-01"
    assert 0.0 <= result.confidence <= 1.0


def test_prompt_contains_no_action_catalog_text() -> None:
    client = FakeClient(GOOD)
    classify(FINDINGS, client=client, bundle_id="b", config_hash="c", repetition=0)
    assert "no_action" not in client.prompt
    assert "isolate_device" not in client.prompt
    assert "Action catalog" not in client.prompt


def test_label_outside_the_enum_is_a_parse_failure() -> None:
    near_miss = json.dumps(
        {
            "incident_type": "SYN Flooding",
            "severity": "high",
            "affected_device": "d",
            "confidence": 0.5,
        }
    )
    with pytest.raises(ClassifyParseError):
        _run(near_miss)


def test_confidence_out_of_range_is_rejected() -> None:
    bad = json.dumps(
        {"incident_type": "benign", "severity": "low", "affected_device": "d", "confidence": 1.5}
    )
    with pytest.raises(ClassifyParseError):
        _run(bad)
