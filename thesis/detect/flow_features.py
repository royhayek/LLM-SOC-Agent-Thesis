"""Flow features for the classifier / Baseline A, on the training split only (E4-01, SCRUM-23).

The flow classifier is both a detector and Baseline A (record §5), so its features get real
engineering (§6.6). Features are computed per flow and describe *behaviour*, never raw addresses
(a classifier must not memorise the attacker's or the testbed's fixed IPs). The training table is
built only from data E2-01 allows: flows in benign windows and flows in **training-split** attack
episodes; every flow in an **evaluation** episode is excluded, and a leakage check enforces it.

    python -m thesis.detect.flow_features    # writes data/features/flows_train.parquet
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from thesis.labels.windows import labels_path, load_window_seconds, read_labels
from thesis.normalize.flows import normalize_flows
from thesis.normalize.store import ALERTS_DIR, read_alerts
from thesis.scenario.schedule import load_schedule
from thesis.schema.alert import FlowDetail

REPO_ROOT = Path(__file__).resolve().parents[2]
CORPUS_DIR = REPO_ROOT / "data" / "raw" / "corpus-v1.0.0"
SCHEDULE = REPO_ROOT / "schedules" / "corpus-v1.0.0.yaml"
OUT_PATH = REPO_ROOT / "data" / "features" / "flows_train.parquet"

# Feature name -> one-line reason (also rendered into docs/detectors/flow_features.md).
FEATURES: dict[str, str] = {
    "duration_s": "flow lifetime; scans are near-instant, floods and sessions last longer",
    "packets_fwd": "initiator packet count; floods and scans are initiator-heavy",
    "packets_bwd": "responder packet count; a refused/absent service answers little",
    "bytes_fwd": "initiator bytes; separates chatty sessions from probes",
    "bytes_bwd": "responder bytes",
    "total_packets": "overall volume of the flow",
    "total_bytes": "overall size of the flow",
    "bytes_per_packet": "mean packet size; floods use tiny packets, transfers large ones",
    "fwd_bwd_packet_ratio": "directionality; one-sided for scans and SYN floods",
    "syn_count_fwd": "initiator SYNs; high for scans and SYN floods",
    "ack_count_fwd": "initiator ACKs; near-zero when no handshake completes",
    "syn_ratio_fwd": "SYNs per initiator packet; ~1 for SYN-only probes",
    "dst_port": "destination service port (behaviour, not an address): 22/80/1883 differ by attack",
    "is_tcp": "transport is TCP",
    "is_udp": "transport is UDP",
    "is_icmp": "transport is ICMP",
}


def flow_features(detail: FlowDetail) -> dict[str, float]:
    pf, pb = detail.packets_fwd, detail.packets_bwd
    total_p = pf + pb
    total_b = detail.bytes_fwd + detail.bytes_bwd
    syn = detail.syn_count_fwd or 0
    return {
        "duration_s": round(detail.duration_s, 3),
        "packets_fwd": float(pf),
        "packets_bwd": float(pb),
        "bytes_fwd": float(detail.bytes_fwd),
        "bytes_bwd": float(detail.bytes_bwd),
        "total_packets": float(total_p),
        "total_bytes": float(total_b),
        "bytes_per_packet": round(total_b / total_p, 3) if total_p else 0.0,
        "fwd_bwd_packet_ratio": round(pf / pb, 3) if pb else float(pf),
        "syn_count_fwd": float(syn),
        "ack_count_fwd": float(detail.ack_count_fwd or 0),
        "syn_ratio_fwd": round(syn / pf, 3) if pf else 0.0,
        "dst_port": float(detail.dst_port),
        "is_tcp": 1.0 if detail.protocol == "tcp" else 0.0,
        "is_udp": 1.0 if detail.protocol == "udp" else 0.0,
        "is_icmp": 1.0 if detail.protocol == "icmp" else 0.0,
    }


def _window_start(ts: datetime, origin: datetime, window_s: int) -> datetime:
    return origin + timedelta(seconds=window_s * int((ts - origin).total_seconds() // window_s))


def _rows_for_chunk(
    run_dir: Path, window_s: int, split_by_episode: dict[str, str]
) -> list[dict[str, object]]:
    result = normalize_flows(run_dir, run_dir.name, alerts_dir=ALERTS_DIR)
    alerts = read_alerts(result.parquet_path) if result.parquet_path else []
    labels = read_labels(labels_path(run_dir.name))
    if not labels:
        return []
    origin = min(w.window_start for w in labels)
    label_by_key = {(w.device, w.window_start): w for w in labels}

    rows: list[dict[str, object]] = []
    for a in alerts:
        if not isinstance(a.detail, FlowDetail):
            continue
        wl = label_by_key.get((a.subject_device, _window_start(a.ts, origin, window_s)))
        label = wl.label if wl is not None else "benign"
        episode_id = wl.episode_id if wl is not None else None
        split = "benign" if episode_id is None else split_by_episode.get(episode_id, "eval")
        if split == "eval":
            continue  # never train on an evaluation-split episode (E2-01)
        row: dict[str, object] = dict(flow_features(a.detail))
        row.update({"label": label, "episode_id": episode_id or "", "device": a.subject_device})
        rows.append(row)
    return rows


def build_training_table(out_path: Path = OUT_PATH) -> pa.Table:
    window_s = load_window_seconds()
    schedule = load_schedule(SCHEDULE)
    split_by_episode = {e.id: (e.split.value if e.split else "eval") for e in schedule.episodes}

    rows: list[dict[str, object]] = []
    for run_dir in sorted(p for p in CORPUS_DIR.iterdir() if p.is_dir()):
        rows += _rows_for_chunk(run_dir, window_s, split_by_episode)
    # Any total order makes the table deterministic (AC1); stringify to keep it type-clean.
    _cols = ("label", "episode_id", "device", "dst_port", "total_bytes")
    rows.sort(key=lambda r: tuple(str(r[c]) for c in _cols))

    columns = list(FEATURES) + ["label", "episode_id", "device"]
    table = pa.table({c: [r[c] for r in rows] for c in columns})
    out_path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, out_path)
    return table


def evaluation_episode_ids() -> set[str]:
    schedule = load_schedule(SCHEDULE)
    return {e.id for e in schedule.episodes if e.split is not None and e.split.value == "eval"}


def leakage_check(table: pa.Table, eval_ids: set[str]) -> list[str]:
    """Return any evaluation episode ids that leaked into the training table (empty = clean)."""
    present = {e for e in table.column("episode_id").to_pylist() if e}
    return sorted(present & eval_ids)


def main() -> int:
    table = build_training_table()
    leaked = leakage_check(table, evaluation_episode_ids())
    if leaked:
        print(f"LEAKAGE: evaluation episodes in the training table: {leaked}")
        return 1
    print(
        f"wrote {OUT_PATH.relative_to(REPO_ROOT)}: {table.num_rows} flows, {len(FEATURES)} features"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
