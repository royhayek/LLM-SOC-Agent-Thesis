"""MQTT statistical-threshold detector (E4-04, SCRUM-48).

A deliberately simple detector (record §6.2): thresholds fitted on **benign training windows only**
(E2-01), so benign irregularities from E1-05 (jitter, bursts, the occasional refused login) stay
below the decision threshold by construction. Every MQTT alert gets a score in [0, 1] and a label;
the score ranks the MQTT exemplars in the reduction (§4.4).

    python -m thesis.detect.mqtt    # calibrate on benign training MQTT; writes the thresholds JSON
"""

from __future__ import annotations

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import cast

from thesis.labels.windows import labels_path, load_window_seconds, read_labels
from thesis.normalize.mqtt import normalize_mqtt
from thesis.normalize.store import ALERTS_DIR, read_alerts
from thesis.schema.alert import Alert, MqttDetail

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "data" / "raw" / "corpus-v1.0.0"
THRESHOLDS_PATH = REPO_ROOT / "models" / "mqtt_thresholds.json"
DOC_PATH = REPO_ROOT / "docs" / "detectors" / "mqtt.md"

DECISION_THRESHOLD = 0.5  # score above this counts as an anomaly (for the false-positive rate)
AUTH_FAILURE_SCORE = 0.4  # below the decision threshold: a lone refused login is benign (E1-05)
PAYLOAD_PERCENTILE = 99


def _channel(topic: str | None) -> str:
    # Topic is iot/<device>/<channel>; the channel ("telemetry", "status", "flood", ...) is the
    # behavioural part. Benign emulators publish only telemetry/status (E1-05).
    return topic.split("/")[2] if topic and topic.count("/") >= 2 else ""


def _percentile(values: list[int], pct: int) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    k = min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1))))
    return float(ordered[k])


def calibrate(benign_alerts: list[Alert]) -> dict[str, object]:
    channels: set[str] = set()
    payloads: list[int] = []
    for a in benign_alerts:
        if isinstance(a.detail, MqttDetail) and a.detail.event == "publish":
            channels.add(_channel(a.detail.topic))
            if a.detail.payload_bytes is not None:
                payloads.append(a.detail.payload_bytes)
    return {
        "benign_channels": sorted(c for c in channels if c),
        "payload_bytes_p99": _percentile(payloads, PAYLOAD_PERCENTILE),
        "payload_percentile": PAYLOAD_PERCENTILE,
        "auth_failure_score": AUTH_FAILURE_SCORE,
        "decision_threshold": DECISION_THRESHOLD,
    }


def score_mqtt(alert: Alert, thresholds: dict[str, object]) -> tuple[float, str]:
    """Return (score in [0,1], label) for one MQTT alert against the calibrated thresholds."""
    detail = alert.detail
    if not isinstance(detail, MqttDetail):
        return 0.0, "benign"
    if detail.event == "auth_failure":
        return float(cast(float, thresholds["auth_failure_score"])), "auth_failure"
    if detail.event == "publish":
        benign_channels = set(cast("list[str]", thresholds["benign_channels"]))
        if _channel(detail.topic) not in benign_channels:
            return 1.0, "novel_topic"  # e.g. the flood channel: never seen in benign traffic
        p99 = float(cast(float, thresholds["payload_bytes_p99"]))
        if detail.payload_bytes is not None and p99 > 0 and detail.payload_bytes > p99:
            over = detail.payload_bytes / p99
            return min(1.0, round(0.5 + 0.25 * (over - 1), 3)), "large_payload"
        return 0.0, "benign"
    return 0.0, "benign"  # connect / disconnect


def _window_start(ts: datetime, origin: datetime, window_s: int) -> datetime:
    return origin + timedelta(seconds=window_s * int((ts - origin).total_seconds() // window_s))


def _benign_mqtt_alerts() -> list[Alert]:
    window_s = load_window_seconds()
    benign: list[Alert] = []
    for run_dir in sorted(p for p in CORPUS_DIR.iterdir() if p.is_dir()):
        result = normalize_mqtt(run_dir, run_dir.name, alerts_dir=ALERTS_DIR)
        alerts = read_alerts(result.parquet_path) if result.parquet_path else []
        labels = read_labels(labels_path(run_dir.name))
        if not labels:
            continue
        origin = min(w.window_start for w in labels)
        label_by_key = {(w.device, w.window_start): w for w in labels}
        for a in alerts:
            wl = label_by_key.get((a.subject_device, _window_start(a.ts, origin, window_s)))
            if wl is None or wl.label == "benign":  # benign window (or unlabelled) only
                benign.append(a)
    return benign


def main() -> int:
    benign = _benign_mqtt_alerts()
    rng = random.Random(20261015)
    rng.shuffle(benign)
    split = int(0.7 * len(benign))
    calib, held_out = benign[:split], benign[split:]

    thresholds = calibrate(calib)
    THRESHOLDS_PATH.parent.mkdir(parents=True, exist_ok=True)
    THRESHOLDS_PATH.write_text(
        json.dumps(thresholds, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    false_pos = sum(1 for a in held_out if score_mqtt(a, thresholds)[0] > DECISION_THRESHOLD)
    fp_rate = round(false_pos / len(held_out), 4) if held_out else 0.0

    DOC_PATH.parent.mkdir(parents=True, exist_ok=True)
    DOC_PATH.write_text(
        "# MQTT statistical-threshold detector (E4-04, SCRUM-48)\n\n"
        "Thresholds fitted on benign training MQTT only (E2-01). Each alert scores in [0, 1]:\n"
        f"publish on a channel never seen in benign traffic (the flood channel) scores 1.0; a "
        f"payload above the benign p{PAYLOAD_PERCENTILE} scores 0.5-1.0; a refused login scores "
        f"{AUTH_FAILURE_SCORE} (below the {DECISION_THRESHOLD} decision threshold, so benign "
        "irregularities are not anomalies); normal publishes and connects score 0.0.\n\n"
        f"- Benign channels: {thresholds['benign_channels']}\n"
        f"- Payload p{PAYLOAD_PERCENTILE}: {thresholds['payload_bytes_p99']} bytes\n"
        f"- **False-positive rate on held-out benign training windows: {fp_rate}** "
        f"({false_pos}/{len(held_out)} alerts scored above {DECISION_THRESHOLD}).\n",
        encoding="utf-8",
    )
    print(f"calibrated; benign channels {thresholds['benign_channels']}; FP rate {fp_rate}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
