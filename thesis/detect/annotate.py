"""Write detector scores and labels into alerts (E4-06, SCRUM-68).

The architecture detects before grouping (Arch §5): the reduction includes each detector's score
and ranks exemplars by it (§4.4). This bridges EPIC-4 to EPIC-3 (C-15). Every normalized alert is
annotated with its detector's name, score and label, then written to
`data/alerts_annotated/<source>/<run_id>.parquet`. A completeness check fails, naming the alert,
if any alert is left without a detector output.

    python -m thesis.detect.annotate    # annotate every corpus run's normalized alerts
"""

from __future__ import annotations

import json
from pathlib import Path

import lightgbm as lgb
import numpy as np

from thesis.detect.flow_features import flow_features
from thesis.detect.honeypot import apply_rules
from thesis.detect.mqtt import THRESHOLDS_PATH, score_mqtt
from thesis.detect.train_flow import META_PATH, MODEL_PATH
from thesis.normalize.flows import normalize_flows
from thesis.normalize.honeypot import normalize_honeypot
from thesis.normalize.mqtt import normalize_mqtt
from thesis.normalize.store import ALERTS_DIR, read_alerts, write_alerts
from thesis.schema.alert import Alert, FlowDetail, Source

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "data" / "raw" / "corpus-v1.0.0"
ANNOTATED_DIR = REPO_ROOT / "data" / "alerts_annotated"

FLOW_DETECTOR = "flow_classifier"
MQTT_DETECTOR = "mqtt_thresholds"
HONEYPOT_DETECTOR = "honeypot_rules"


def _annotated(alert: Alert, score: float, label: str, name: str) -> Alert:
    return alert.model_copy(
        update={"detector_score": round(score, 4), "detector_label": label, "detector_name": name}
    )


def annotate_flows(alerts: list[Alert], booster: lgb.Booster, classes: list[str]) -> list[Alert]:
    flows = [a for a in alerts if isinstance(a.detail, FlowDetail)]
    if not flows:
        return []
    rows: list[list[float]] = []
    for a in flows:
        assert isinstance(a.detail, FlowDetail)  # narrowed for the type checker
        rows.append(list(flow_features(a.detail).values()))
    probs = booster.predict(np.asarray(rows))
    out = []
    for a, row in zip(flows, probs, strict=True):
        idx = int(np.argmax(row))
        out.append(_annotated(a, float(row[idx]), classes[idx], FLOW_DETECTOR))
    return out


def annotate_mqtt(alerts: list[Alert], thresholds: dict[str, object]) -> list[Alert]:
    out = []
    for a in alerts:
        score, label = score_mqtt(a, thresholds)
        out.append(_annotated(a, score, label, MQTT_DETECTOR))
    return out


def annotate_honeypot(alerts: list[Alert]) -> list[Alert]:
    scored = apply_rules(alerts)
    out = []
    for a in alerts:
        score, label = scored.get(a.alert_id, (0.3, "contact"))
        out.append(_annotated(a, score, label, HONEYPOT_DETECTOR))
    return out


def completeness_check(alerts: list[Alert]) -> list[str]:
    """Return the ids of any alerts missing a detector name, score or label (empty = complete)."""
    return [
        a.alert_id
        for a in alerts
        if a.detector_name is None or a.detector_score is None or a.detector_label is None
    ]


def annotate_run(run_dir: Path, annotated_dir: Path = ANNOTATED_DIR) -> dict[str, int]:
    run_id = run_dir.name
    meta = json.loads(META_PATH.read_text(encoding="utf-8"))
    booster = lgb.Booster(model_file=str(MODEL_PATH))
    thresholds = json.loads(THRESHOLDS_PATH.read_text(encoding="utf-8"))

    flow_alerts = read_alerts(normalize_flows(run_dir, run_id, ALERTS_DIR).parquet_path)  # type: ignore[arg-type]
    mqtt_alerts = read_alerts(normalize_mqtt(run_dir, run_id, ALERTS_DIR).parquet_path)  # type: ignore[arg-type]
    hp_alerts = read_alerts(normalize_honeypot(run_dir, run_id, ALERTS_DIR).parquet_path)  # type: ignore[arg-type]

    annotated = {
        Source.FLOWS.value: annotate_flows(flow_alerts, booster, meta["classes"]),
        Source.MQTT.value: annotate_mqtt(mqtt_alerts, thresholds),
        Source.HONEYPOT.value: annotate_honeypot(hp_alerts),
    }
    counts: dict[str, int] = {}
    for source, alerts in annotated.items():
        missing = completeness_check(alerts)
        if missing:
            raise SystemExit(f"{source} alerts without a detector output: {missing[:5]}")
        write_alerts(alerts, annotated_dir / source / f"{run_id}.parquet")
        counts[source] = len(alerts)
    return counts


def main() -> int:
    total: dict[str, int] = {}
    for run_dir in sorted(p for p in CORPUS_DIR.iterdir() if p.is_dir()):
        for source, n in annotate_run(run_dir).items():
            total[source] = total.get(source, 0) + n
    print(f"annotated: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
