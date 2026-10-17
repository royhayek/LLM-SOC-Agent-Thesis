"""Tests for the demo-simulator support (scenario catalog, event assembly). Deterministic only;
no model output is asserted."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from thesis.api.demo import (
    EVAL_PARQUET,
    AlertRow,
    BundleMeta,
    Scenario,
    build_scenario_events,
    load_alert_index,
    load_bundle_meta,
    load_scenarios,
)

T0 = datetime(2026, 1, 1, tzinfo=UTC)


def _meta(bid: str, start_s: int, end_s: int, alert_ids: list[str], episode: str | None = "ep-x"):
    return BundleMeta(
        bundle_id=bid,
        device="d",
        window_start=T0 + timedelta(seconds=start_s),
        window_end=T0 + timedelta(seconds=end_s),
        label="syn_flood",
        episode_id=episode,
        sources=["flows"],
        alert_ids=alert_ids,
    )


def _alert(aid: str, ts_s: int) -> AlertRow:
    return AlertRow(aid, "flows", T0 + timedelta(seconds=ts_s), "syn_flood", 1.0, f"sum {aid}", {})


def _row(bid: str, emitted: bool = True) -> dict:
    return {
        "bundle_id": bid,
        "emitted": emitted,
        "incident_type": "syn_flood" if emitted else None,
        "confidence": 0.8 if emitted else None,
        "severity": "high" if emitted else None,
        "affected_device": "d" if emitted else None,
        "recommended_action": "rate_limit_source" if emitted else None,
        "evidence": ["a1"] if emitted else [],
        "config_hash": "h",
        "ground_truth": "syn_flood",
    }


def _scenario(**kw) -> Scenario:
    base = dict(
        id="s",
        title="t",
        description="d",
        episode_id="ep-x",
        bundle_ids=None,
        attack_family="syn_flood",
        default_condition="C1",
        highlight=None,
    )
    base.update(kw)
    return Scenario.model_validate(base)


def test_load_scenarios_returns_the_catalog() -> None:
    scenarios = load_scenarios()
    ids = {s.id for s in scenarios}
    assert {"ssh-bruteforce", "syn-flood", "mqtt-flood", "benign", "honest-limitation"} <= ids
    for s in scenarios:
        assert s.default_condition.startswith("C")
        assert s.episode_id or s.bundle_ids  # every scenario selects its bundles somehow


@pytest.mark.skipif(not EVAL_PARQUET.exists(), reason="bundle parquet not on disk")
def test_bundle_meta_and_alert_index_join() -> None:
    meta = load_bundle_meta()
    alerts = load_alert_index()
    b = next(iter(meta.values()))
    assert b.window_start <= b.window_end and b.alert_ids
    # every bundle cites alert ids that resolve in the labeled-alert index
    assert any(aid in alerts for aid in b.alert_ids)
    a = alerts[next(aid for aid in b.alert_ids if aid in alerts)]
    assert a.ts is not None and a.summary


def test_events_are_time_ordered_with_one_alert_each() -> None:
    meta = {"b1": _meta("b1", 0, 60, ["a1", "a2"])}
    alerts = {"a1": _alert("a1", 5), "a2": _alert("a2", 40)}
    events = build_scenario_events(
        _scenario(),
        "C1",
        meta=meta,
        alerts=alerts,
        rows_by_bundle={"b1": _row("b1")},
        call_log_path=None,
    )
    kinds = [e.kind for e in events]
    assert kinds.count("alert") == 2
    assert "bundle_formed" in kinds and "verdict" in kinds and "recommendation" in kinds
    assert [e.t for e in events] == sorted(e.t for e in events)


def test_withheld_bundle_emits_bundle_formed_and_withheld_verdict() -> None:
    meta = {"b1": _meta("b1", 0, 60, ["a1"])}
    alerts = {"a1": _alert("a1", 5)}
    events = build_scenario_events(
        _scenario(attack_family=None),
        "C1",
        meta=meta,
        alerts=alerts,
        rows_by_bundle={"b1": _row("b1", emitted=False)},
        call_log_path=None,
    )
    verdict = next(e for e in events if e.kind == "verdict")
    assert verdict.payload["withheld"] is True
    assert any(e.kind == "bundle_formed" for e in events)
    assert not any(e.kind == "recommendation" for e in events)


def test_bundle_ids_selector_when_no_episode() -> None:
    meta = {
        "b1": _meta("b1", 0, 60, ["a1"], episode=None),
        "b2": _meta("b2", 0, 60, ["a1"], episode=None),
    }
    alerts = {"a1": _alert("a1", 5)}
    scenario = _scenario(episode_id=None, bundle_ids=["b2"])
    events = build_scenario_events(
        scenario,
        "C1",
        meta=meta,
        alerts=alerts,
        rows_by_bundle={"b1": _row("b1"), "b2": _row("b2")},
        call_log_path=None,
    )
    assert {e.bundle_id for e in events} == {"b2"}  # only the listed bundle
