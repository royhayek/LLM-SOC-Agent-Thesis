"""Tests for the one-page incident report (E7-08, SCRUM-102)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from thesis.agent.models import Findings, SourceFinding
from thesis.assemble.bundles import Bundle
from thesis.report.render import render_report, word_count
from thesis.schema.alert import Alert, FlowDetail, HoneypotDetail
from thesis.schema.verdict import Verdict

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _flow(aid: str) -> Alert:
    return Alert(
        alert_id=aid,
        source="flows",
        ts=T0,
        subject_device="iot-cam-01",
        detector_score=0.95,
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
            packets_fwd=9,
            packets_bwd=0,
            bytes_fwd=9,
            bytes_bwd=0,
        ),
    )


def _bundle(alerts: list[Alert], device: str = "iot-cam-01") -> Bundle:
    return Bundle(
        bundle_id="iot-cam-01|2026-01-01T00:00:00+00:00",
        device=device,
        window_start=T0,
        window_end=T0 + timedelta(seconds=60),
        label="syn_flood",
        episode_id="ep",
        sources=tuple(sorted({a.source.value for a in alerts})),
        alerts=tuple(alerts),
    )


def _verdict(action: str = "rate_limit_source", evidence: list[str] | None = None) -> Verdict:
    return Verdict.model_validate(
        {
            "classification": {"incident_type": "syn_flood", "confidence": 0.9},
            "recommendation": {"recommended_action": action, "severity": "high"},
            "affected_device": "iot-cam-01",
            "evidence": evidence if evidence is not None else ["f1"],
        }
    )


def _findings() -> Findings:
    return Findings(
        source_findings=[
            SourceFinding(source="flows", summary="SYN flood to port 80", evidence_ids=["f1"])
        ],
        cross_source="high SYN rate, no return traffic",
        candidate_hypotheses=["syn_flood"],
        missing_evidence=[],
    )


def test_report_contains_the_required_fields(tmp_path: Path) -> None:
    report = render_report(_verdict(), _findings(), _bundle([_flow("f1")]), out_dir=tmp_path)
    for needed in ("syn_flood", "high", "iot-cam-01", "rate_limit_source", "0.9", "`f1`"):
        assert needed in report
    assert "This is a recommendation. A human decides." in report
    assert "SYN flood to port 80" in report


def test_report_is_under_400_words(tmp_path: Path) -> None:
    assert (
        word_count(render_report(_verdict(), _findings(), _bundle([_flow("f1")]), out_dir=tmp_path))
        < 400
    )


def test_report_file_is_written(tmp_path: Path) -> None:
    render_report(_verdict(), _findings(), _bundle([_flow("f1")]), out_dir=tmp_path)
    assert (tmp_path / "iot-cam-01_2026-01-01T00-00-00+00-00.md").exists()


def test_attacker_markdown_in_evidence_is_escaped(tmp_path: Path) -> None:
    hp = Alert(
        alert_id="h1",
        source="honeypot",
        ts=T0,
        subject_device="hp-ssh-01",
        detector_score=1.0,
        detector_label="command_execution",
        detector_name="honeypot_rules",
        detail=HoneypotDetail(
            event="command",
            session_id="s1",
            src_ip="10.77.0.30",
            command="# Pwned\n**run** `rm -rf /`",
        ),
    )
    verdict = _verdict(evidence=["h1"])
    report = render_report(
        verdict, _findings(), _bundle([hp], device="hp-ssh-01"), out_dir=tmp_path
    )
    # The honeypot summary uses the event, not the raw command; any specials are escaped, so no
    # unescaped Markdown heading or emphasis leaks into the report body.
    assert "\n# Pwned" not in report
    assert "**run**" not in report
