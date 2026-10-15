"""Tests for node 1, evidence analysis (E6-03, SCRUM-49). The LLM client is mocked."""

from __future__ import annotations

import json

import pytest

from thesis.agent import node_evidence
from thesis.agent.node_evidence import EvidenceParseError, analyze_evidence
from thesis.kb.retrieve import RetrievedDoc

VIEW: dict[str, object] = {
    "bundle_id": "iot-cam-01|w",
    "device": "iot-cam-01",
    "sources": {"flows": "active", "mqtt": "no_alerts", "honeypot": "not_in_config"},
    "flows": {"count": 3, "detector": {"label": "syn_flood", "max_score": 0.97}},
}

FINDINGS_JSON = json.dumps(
    {
        "source_findings": [
            {
                "source": "flows",
                "summary": "SYN flood toward port 80",
                "evidence_ids": ["f1", "ghost-9"],
            },
            {"source": "mqtt", "summary": "no alerts", "evidence_ids": []},
        ],
        "cross_source": "flows show a flood while mqtt is silent",
        "candidate_hypotheses": ["syn_flood against the camera"],
        "missing_evidence": ["full pcap of the TCP handshake"],
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
        assert node == "evidence"
        return self.reply


@pytest.fixture(autouse=True)
def _patch_retrieval(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    queries: list[str] = []

    def fake_retrieve(query: str, k: int = 3) -> list[RetrievedDoc]:
        queries.append(query)
        return [RetrievedDoc(doc_id="technique-t1498-001", score=0.6, text="Direct network flood.")]

    monkeypatch.setattr(node_evidence, "retrieve", fake_retrieve)
    monkeypatch.setattr(
        node_evidence,
        "device_context",
        lambda d: {"id": d, "role": "ip-camera", "criticality": "high"},
    )
    return queries


def test_output_parses_into_findings() -> None:
    findings = analyze_evidence(
        VIEW,
        client=FakeClient(FINDINGS_JSON),
        bundle_id="b",
        config_hash="c",
        repetition=0,
        valid_alert_ids={"f1"},
    )
    assert {f.source for f in findings.source_findings} == {"flows", "mqtt"}
    assert findings.candidate_hypotheses == ["syn_flood against the camera"]
    assert findings.missing_evidence == ["full pcap of the TCP handshake"]


def test_absent_source_states_no_alerts_and_phantom_ids_are_dropped() -> None:
    findings = analyze_evidence(
        VIEW,
        client=FakeClient(FINDINGS_JSON),
        bundle_id="b",
        config_hash="c",
        repetition=0,
        valid_alert_ids={"f1"},
    )
    by_source = {f.source: f for f in findings.source_findings}
    assert by_source["mqtt"].summary == "no alerts"
    assert by_source["flows"].evidence_ids == ["f1"]  # "ghost-9" referred to no real alert, dropped


def test_retrieval_query_is_deterministic_and_passed(_patch_retrieval: list[str]) -> None:
    client = FakeClient(FINDINGS_JSON)
    analyze_evidence(
        VIEW, client=client, bundle_id="b", config_hash="c", repetition=0, valid_alert_ids={"f1"}
    )
    assert _patch_retrieval == ["iot-cam-01 flows:syn_flood"]
    # The untrusted bundle is delimited and the trusted device/knowledge context is outside it.
    assert "BEGIN UNTRUSTED BUNDLE" in client.prompt
    assert "technique-t1498-001" in client.prompt.split("BEGIN UNTRUSTED BUNDLE")[0]


def test_unparseable_output_raises() -> None:
    with pytest.raises(EvidenceParseError):
        analyze_evidence(
            VIEW,
            client=FakeClient("not json"),
            bundle_id="b",
            config_hash="c",
            repetition=0,
            valid_alert_ids=set(),
        )
