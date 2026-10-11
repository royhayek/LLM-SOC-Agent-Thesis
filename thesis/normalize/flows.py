"""Normalize network flows into alerts (E3-03, SCRUM-38).

Flows are the only source present in every attack family, and correct device keying matters most
here: a flow keyed to the broker instead of the device puts evidence in the wrong bundle (§4.1).
Each NFStream flow record (ADR-0002) becomes one `Alert` keyed to the non-infrastructure endpoint,
or is counted as skipped with a reason. The device mapping is the single IP-based
`subject_device()` (E0-08 / E3-10); a `None` subject is classified into a specific skip reason.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from thesis.normalize.store import ALERTS_DIR, NormalizeResult, write_alerts
from thesis.schema.alert import Alert, FlowDetail, Source
from thesis.schema.devices import DEVICES, INFRASTRUCTURE, subject_device

_PROTO = {6: "tcp", 17: "udp", 1: "icmp"}
# Bidirectional TCP flag-count fields (NFStream), in a fixed render order for `tcp_flags`.
_FLAGS = [
    ("syn", "SYN"),
    ("ack", "ACK"),
    ("psh", "PSH"),
    ("fin", "FIN"),
    ("rst", "RST"),
    ("urg", "URG"),
]


def _skip_reason(src_ip: str, dst_ip: str | None) -> str:
    ips = [ip for ip in (src_ip, dst_ip) if ip is not None]
    infra = [ip for ip in ips if ip in INFRASTRUCTURE]
    devs = [ip for ip in ips if ip in DEVICES]
    if len(devs) >= 2:
        return "device_to_device"
    if len(infra) == len(ips):
        return "infrastructure_only"
    if infra:
        return "external_to_infrastructure"
    return "no_subject_device"


def _tcp_flags(rec: dict[str, Any]) -> str | None:
    present = [
        label for key, label in _FLAGS if int(rec.get(f"bidirectional_{key}_packets", 0) or 0) > 0
    ]
    return ",".join(present) if present else None


def parse_flow(rec: dict[str, Any], alert_id: str) -> tuple[Alert | None, str | None]:
    try:
        src_ip = str(rec["src_ip"])
        dst_ip = str(rec["dst_ip"])
        first_ms = int(rec["bidirectional_first_seen_ms"])
        proto_num = int(rec["protocol"])
    except (KeyError, TypeError, ValueError):
        return None, "malformed"

    subject = subject_device(Source.FLOWS, src_ip, dst_ip)
    if subject is None:
        return None, _skip_reason(src_ip, dst_ip)

    ts = datetime.fromtimestamp(first_ms / 1000, tz=UTC)
    proto = _PROTO.get(proto_num, str(proto_num))
    detail = FlowDetail(
        flow_start=ts,
        duration_s=int(rec.get("bidirectional_duration_ms", 0) or 0) / 1000,
        src_ip=src_ip,
        src_port=int(rec.get("src_port", 0) or 0),
        dst_ip=dst_ip,
        dst_port=int(rec.get("dst_port", 0) or 0),
        protocol=proto,
        packets_fwd=int(rec.get("src2dst_packets", 0) or 0),
        packets_bwd=int(rec.get("dst2src_packets", 0) or 0),
        bytes_fwd=int(rec.get("src2dst_bytes", 0) or 0),
        bytes_bwd=int(rec.get("dst2src_bytes", 0) or 0),
        tcp_flags=_tcp_flags(rec) if proto == "tcp" else None,
        syn_count_fwd=int(rec["src2dst_syn_packets"]) if "src2dst_syn_packets" in rec else None,
        ack_count_fwd=int(rec["src2dst_ack_packets"]) if "src2dst_ack_packets" in rec else None,
    )
    return Alert(
        alert_id=alert_id, source=Source.FLOWS, ts=ts, subject_device=subject, detail=detail
    ), None


def normalize_flows(run_dir: Path, run_id: str, alerts_dir: Path = ALERTS_DIR) -> NormalizeResult:
    """Normalize a run's flows to `data/alerts/flows/<run_id>.parquet`, with a skip log."""
    result = NormalizeResult(run_id=run_id)
    alerts: list[Alert] = []
    skips: list[dict[str, object]] = []
    flows_path = run_dir / "flows" / "flows.jsonl"
    lines = flows_path.read_text(encoding="utf-8").splitlines() if flows_path.is_file() else []
    seq = 0
    for i, raw in enumerate(lines):
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
            alert, reason = parse_flow(rec, f"fl-{run_id}-{seq:06d}")
        except json.JSONDecodeError:
            alert, reason = None, "malformed"
        seq += 1
        if alert is not None:
            alerts.append(alert)
            result.alerts += 1
        else:
            reason = reason or "unknown"
            result.skipped += 1
            result.skip_reasons[reason] += 1
            skips.append({"line": i + 1, "reason": reason})

    out = alerts_dir / "flows" / f"{run_id}.parquet"
    write_alerts(alerts, out)
    result.parquet_path = out
    skip_path = alerts_dir / "flows" / f"{run_id}.skips.jsonl"
    skip_path.parent.mkdir(parents=True, exist_ok=True)
    skip_path.write_text("".join(json.dumps(s) + "\n" for s in skips), encoding="utf-8")
    result.skip_log_path = skip_path
    return result
