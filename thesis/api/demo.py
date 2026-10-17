"""Demo-simulator support: a curated scenario catalog and the replay event assembly, read-only over
the frozen run (record §2, §5). No model call happens here (the optional live run lives in app.py).
Recommend-only: nothing in this module acts on a testbed or network (§1.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, cast

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_PATH = REPO_ROOT / "config" / "demo_scenarios.yaml"
EVAL_PARQUET = REPO_ROOT / "data" / "bundles" / "v1.0.0" / "eval.parquet"
ANNOTATED_DIRS = [
    REPO_ROOT / "data" / "bundles" / "_annotated" / s for s in ("flows", "honeypot", "mqtt")
]


class Scenario(BaseModel):
    """One curated replay scenario. It selects its bundles by `episode_id`, or by an explicit
    `bundle_ids` list when the bundles carry no episode (benign background traffic)."""

    id: str
    title: str
    description: str
    episode_id: str | None
    bundle_ids: list[str] | None
    attack_family: str | None
    default_condition: str
    highlight: str | None


def load_scenarios(path: Path = SCENARIOS_PATH) -> list[Scenario]:
    """Load the curated scenario catalog from `config/demo_scenarios.yaml`."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Scenario.model_validate(s) for s in data["scenarios"]]


class BundleMeta(BaseModel):
    """One evaluation bundle's metadata, from the persisted bundle parquet (no detector rerun)."""

    bundle_id: str
    device: str
    window_start: datetime
    window_end: datetime
    label: str
    episode_id: str | None
    sources: list[str]
    alert_ids: list[str]


@dataclass(frozen=True)
class AlertRow:
    """A labeled alert, from the annotated alert parquet (carries the detector's verdict)."""

    alert_id: str
    source: str
    ts: datetime
    detector_label: str | None
    detector_score: float | None
    summary: str
    alert_json: dict[str, object]


def load_bundle_meta(eval_path: Path = EVAL_PARQUET) -> dict[str, BundleMeta]:
    """Every evaluation bundle's metadata, keyed by bundle id."""
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    out: dict[str, BundleMeta] = {}
    for r in pq.read_table(eval_path).to_pylist():
        out[str(r["bundle_id"])] = BundleMeta(
            bundle_id=str(r["bundle_id"]),
            device=str(r["device"]),
            window_start=r["window_start"],
            window_end=r["window_end"],
            label=str(r["label"]),
            episode_id=(str(r["episode_id"]) or None),
            sources=[str(s) for s in r["sources"]],
            alert_ids=[str(a) for a in r["alert_ids"]],
        )
    return out


def _alert_summary(source: str, detail: dict[str, object]) -> str:
    """A one-line, human summary of an alert's detail, by source."""
    if source == "flows":
        return (
            f"flow {detail.get('src_ip')}:{detail.get('src_port')}"
            f"->{detail.get('dst_ip')}:{detail.get('dst_port')} {detail.get('protocol')}"
        )
    if source == "mqtt":
        return f"mqtt {detail.get('event')} topic={detail.get('topic')}"
    if source == "honeypot":
        return f"honeypot {detail.get('event')} session={detail.get('session_id')}"
    return source


def load_alert_index(dirs: list[Path] = ANNOTATED_DIRS) -> dict[str, AlertRow]:
    """The labeled alerts, keyed by alert id, from the annotated alert parquet."""
    import pyarrow.parquet as pq

    out: dict[str, AlertRow] = {}
    for d in dirs:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.parquet")):
            for r in pq.read_table(f).to_pylist():
                aj = json.loads(r["alert_json"])
                out[str(r["alert_id"])] = AlertRow(
                    alert_id=str(r["alert_id"]),
                    source=str(r["source"]),
                    ts=r["ts"],
                    detector_label=aj.get("detector_label"),
                    detector_score=aj.get("detector_score"),
                    summary=_alert_summary(str(r["source"]), aj.get("detail", {})),
                    alert_json=aj,
                )
    return out


class DemoEvent(BaseModel):
    """One time-stamped event in a scenario replay. `t` is seconds from the window start."""

    t: float
    kind: Literal["alert", "bundle_formed", "reasoning", "verdict", "recommendation"]
    bundle_id: str
    payload: dict[str, object]


# Synthetic spacing (seconds) for the agent's reasoning steps after a bundle forms. The reasoning
# happened offline, so the demo narrates it just after the bundle closes (spec §5 timing model).
_REASON_GAP = 2.0


def _scenario_bundles(scenario: Scenario, meta: dict[str, BundleMeta]) -> list[BundleMeta]:
    """The scenario's bundles in time order: the episode's bundles, or the explicit bundle_ids."""
    if scenario.episode_id is not None:
        chosen = [m for m in meta.values() if m.episode_id == scenario.episode_id]
    else:
        chosen = [meta[b] for b in (scenario.bundle_ids or []) if b in meta]
    return sorted(chosen, key=lambda m: m.window_start)


def build_scenario_events(
    scenario: Scenario,
    condition: str,
    *,
    meta: dict[str, BundleMeta],
    alerts: dict[str, AlertRow],
    rows_by_bundle: dict[str, dict[str, object]],
    call_log_path: Path | None,
) -> list[DemoEvent]:
    """Assemble the time-ordered replay events for one scenario under one condition, from the frozen
    alerts, result rows and (optionally) the recorded reasoning trace."""
    bundles = _scenario_bundles(scenario, meta)
    if not bundles:
        return []
    t0 = bundles[0].window_start
    events: list[DemoEvent] = []
    for b in bundles:
        for aid in b.alert_ids:
            a = alerts.get(aid)
            if a is None:
                continue
            events.append(
                DemoEvent(
                    t=(a.ts - t0).total_seconds(),
                    kind="alert",
                    bundle_id=b.bundle_id,
                    payload={
                        "alert_id": a.alert_id,
                        "source": a.source,
                        "detector_label": a.detector_label,
                        "detector_score": a.detector_score,
                        "summary": a.summary,
                    },
                )
            )
        bt = (b.window_end - t0).total_seconds()
        events.append(
            DemoEvent(
                t=bt,
                kind="bundle_formed",
                bundle_id=b.bundle_id,
                payload={
                    "device": b.device,
                    "sources": b.sources,
                    "n_alerts": len(b.alert_ids),
                    "ground_truth": b.label,
                },
            )
        )
        row = rows_by_bundle.get(b.bundle_id)
        if row is None:
            continue
        trace: list[dict[str, object]] = []
        if call_log_path is not None:
            from thesis.api.app import _load_trace

            trace = _load_trace(call_log_path, b.bundle_id, str(row["config_hash"]))
        for i, step in enumerate(trace, start=1):
            events.append(
                DemoEvent(
                    t=bt + i * _REASON_GAP,
                    kind="reasoning",
                    bundle_id=b.bundle_id,
                    payload={
                        "node": step["node"],
                        "event": step["event"],
                        "completion": step["completion"],
                    },
                )
            )
        vt = bt + (len(trace) + 1) * _REASON_GAP
        emitted = bool(row["emitted"]) and row["incident_type"] is not None
        events.append(
            DemoEvent(
                t=vt,
                kind="verdict",
                bundle_id=b.bundle_id,
                payload=(
                    {"withheld": True}
                    if not emitted
                    else {
                        "withheld": False,
                        "incident_type": row["incident_type"],
                        "severity": row["severity"],
                        "affected_device": row["affected_device"],
                        "confidence": row["confidence"],
                    }
                ),
            )
        )
        if emitted:
            events.append(
                DemoEvent(
                    t=vt + _REASON_GAP,
                    kind="recommendation",
                    bundle_id=b.bundle_id,
                    payload={
                        "recommended_action": row["recommended_action"],
                        "severity": row["severity"],
                        "evidence": list(cast("list[object]", row["evidence"] or [])),
                    },
                )
            )
    return sorted(events, key=lambda e: e.t)


__all__ = [
    "ANNOTATED_DIRS",
    "EVAL_PARQUET",
    "SCENARIOS_PATH",
    "AlertRow",
    "BundleMeta",
    "DemoEvent",
    "Scenario",
    "build_scenario_events",
    "load_alert_index",
    "load_bundle_meta",
    "load_scenarios",
]
