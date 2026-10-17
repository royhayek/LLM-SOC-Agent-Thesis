"""Demo-simulator support: a curated scenario catalog and the replay event assembly, read-only over
the frozen run (record §2, §5). No model call happens here (the optional live run lives in app.py).
Recommend-only: nothing in this module acts on a testbed or network (§1.1)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

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


__all__ = [
    "ANNOTATED_DIRS",
    "EVAL_PARQUET",
    "SCENARIOS_PATH",
    "AlertRow",
    "BundleMeta",
    "Scenario",
    "load_alert_index",
    "load_bundle_meta",
    "load_scenarios",
]
