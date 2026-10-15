"""Tests for the three-node graph runner (E6-06, SCRUM-81). The LLM client is mocked."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest

from thesis.agent import node_evidence
from thesis.agent.graph import run_graph
from thesis.config import ExperimentConfig, Provenance, Safety, Strategy
from thesis.kb.retrieve import RetrievedDoc
from thesis.schema.alert import Alert, FlowDetail, HoneypotDetail, MqttDetail, Source

T0 = datetime(2026, 1, 1, tzinfo=UTC)

# Distinctive content that must NOT leak into prompts when a source is not configured.
MQTT_TOPIC = "iot/SECRET-TOPIC/flood"
HP_CMD = "SECRET-HONEYPOT-CMD"
NODE1_SENTINEL = "NODE1-ONLY-CROSS-SOURCE-NOTE"

FINDINGS_REPLY = json.dumps(
    {
        "source_findings": [{"source": "flows", "summary": "flood", "evidence_ids": ["f1"]}],
        "cross_source": NODE1_SENTINEL,
        "candidate_hypotheses": ["syn_flood"],
        "missing_evidence": [],
    }
)
CLASSIFY_REPLY = json.dumps(
    {
        "incident_type": "syn_flood",
        "severity": "high",
        "affected_device": "iot-cam-01",
        "confidence": 0.9,
    }
)
RECOMMEND_REPLY = json.dumps({"recommended_action": "rate_limit_source", "evidence_ids": ["f1"]})
REPLIES = {
    "evidence": FINDINGS_REPLY,
    "classification": CLASSIFY_REPLY,
    "recommendation": RECOMMEND_REPLY,
}


class MultiReplyClient:
    def __init__(self) -> None:
        self.prompts: dict[str, str] = {}

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
        self.prompts[node] = prompt
        return REPLIES[node]


def _flow(aid: str) -> Alert:
    return Alert(
        alert_id=aid,
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
            syn_count_fwd=10,
            ack_count_fwd=0,
        ),
    )


def _mqtt() -> Alert:
    return Alert(
        alert_id="m1",
        source="mqtt",
        ts=T0,
        subject_device="iot-cam-01",
        detector_score=1.0,
        detector_label="novel_topic",
        detector_name="mqtt_thresholds",
        detail=MqttDetail(event="publish", topic=MQTT_TOPIC, payload_bytes=9),
    )


def _hp() -> Alert:
    return Alert(
        alert_id="h1",
        source="honeypot",
        ts=T0,
        subject_device="hp-ssh-01",
        detector_score=0.8,
        detector_label="command",
        detector_name="honeypot_rules",
        detail=HoneypotDetail(
            event="command", session_id="s1", src_ip="10.77.0.30", command=HP_CMD
        ),
    )


def _bundle(alerts: list[Alert]) -> object:
    from thesis.assemble.bundles import Bundle

    return Bundle(
        bundle_id="iot-cam-01|w",
        device="iot-cam-01",
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label="syn_flood",
        episode_id="ep-1",
        sources=tuple(sorted({a.source.value for a in alerts})),
        alerts=tuple(alerts),
    )


def _config(sources: set[Source]) -> ExperimentConfig:
    prov = Provenance(
        model="m",
        model_revision="r",
        provider="p",
        temperature=0.6,
        top_p=0.9,
        max_tokens=250,
        seed=None,
        prompt_template_version="prompts-v1.0",
        graph_version="graph-v1.0",
    )
    return ExperimentConfig(
        sources=frozenset(sources),
        strategy=Strategy.AGENTIC,
        safety=Safety.LOGGING_ONLY,
        provenance=prov,
    )


@pytest.fixture(autouse=True)
def _patch_retrieval(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        node_evidence,
        "retrieve",
        lambda q, k=3: [RetrievedDoc("technique-t1498-001", 0.6, "flood")],
    )
    monkeypatch.setattr(
        node_evidence,
        "device_context",
        lambda d: {"id": d, "role": "ip-camera", "criticality": "high"},
    )


def test_exactly_three_calls_in_fixed_order() -> None:
    client = MultiReplyClient()
    trace = run_graph(_bundle([_flow("f1")]), _config({Source.FLOWS}), client=client, repetition=0)
    assert list(client.prompts) == ["evidence", "classification", "recommendation"]
    assert trace.recommendation.recommended_action.value == "rate_limit_source"
    assert trace.sources == ("flows",)


def test_flows_only_config_leaks_no_other_source_content() -> None:
    client = MultiReplyClient()
    run_graph(
        _bundle([_flow("f1"), _mqtt(), _hp()]), _config({Source.FLOWS}), client=client, repetition=0
    )
    for prompt in client.prompts.values():
        assert MQTT_TOPIC not in prompt  # unconfigured MQTT content never reaches a prompt
        assert HP_CMD not in prompt  # unconfigured honeypot content never reaches a prompt


def test_only_parsed_fields_flow_forward_no_accumulation() -> None:
    client = MultiReplyClient()
    run_graph(_bundle([_flow("f1")]), _config({Source.FLOWS}), client=client, repetition=0)
    # Node 1's cross-source note reaches node 2 (parsed, passed on) but not node 3.
    assert NODE1_SENTINEL in client.prompts["classification"]
    assert NODE1_SENTINEL not in client.prompts["recommendation"]
