"""Normalize honeypot logs into alerts (E3-04, SCRUM-50).

Cowrie events (ADR-0002) carry the commands the attacker typed: evidence for the agent and, at the
same time, the prompt-injection channel (risk #7). This normalizer keeps that text **verbatim** in
a typed field and does nothing else with it — no interpreting, no executing, no logging it as an
instruction (§6.11). Delimiting and truncation happen later, at prompt time (E7-07).

Every honeypot event keys to the honeypot (§4.1). Each event becomes one `Alert`, or a malformed
line is counted as skipped with a reason (§6.9).
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from thesis.normalize.store import ALERTS_DIR, NormalizeResult, write_alerts
from thesis.schema.alert import Alert, HoneypotDetail, Source
from thesis.schema.devices import HONEYPOT_ID

# Cowrie eventid -> alert event name for the events the reduction and exemplars use (Annex E).
_EVENT_MAP = {
    "cowrie.session.connect": "session_connect",
    "cowrie.login.success": "login_success",
    "cowrie.login.failed": "login_failed",
    "cowrie.command.input": "command",
    "cowrie.command.failed": "command_failed",
}


def _event_name(eventid: str) -> str:
    return _EVENT_MAP.get(eventid, eventid.removeprefix("cowrie.").replace(".", "_"))


def parse_cowrie(rec: dict[str, Any], alert_id: str) -> tuple[Alert | None, str | None]:
    try:
        eventid = str(rec["eventid"])
        session_id = str(rec["session"])
        src_ip = str(rec["src_ip"])
        ts = datetime.fromisoformat(str(rec["timestamp"]).replace("Z", "+00:00"))
    except (KeyError, TypeError, ValueError):
        return None, "malformed"
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=UTC)

    event = _event_name(eventid)
    detail = HoneypotDetail(
        event=event,
        session_id=session_id,
        src_ip=src_ip,
        src_port=rec.get("src_port"),
        dst_ip=rec.get("dst_ip"),
        dst_port=rec.get("dst_port"),
        protocol=rec.get("protocol"),
        username=rec.get("username"),
        password=rec.get("password"),
        command=rec.get("input"),  # verbatim attacker text; stored as data only (§6.11)
        client_version=rec.get("version"),
    )
    alert = Alert(
        alert_id=alert_id, source=Source.HONEYPOT, ts=ts, subject_device=HONEYPOT_ID, detail=detail
    )
    return alert, None


def normalize_honeypot(
    run_dir: Path, run_id: str, alerts_dir: Path = ALERTS_DIR
) -> NormalizeResult:
    """Normalize a run's honeypot log to `data/alerts/honeypot/<run_id>.parquet` (plus skip log)."""
    result = NormalizeResult(run_id=run_id)
    alerts: list[Alert] = []
    skips: list[dict[str, object]] = []
    cj = run_dir / "honeypot" / "cowrie.json"
    lines = cj.read_text(encoding="utf-8").splitlines() if cj.is_file() else []
    seq = 0
    for i, raw in enumerate(lines):
        if not raw.strip():
            continue
        try:
            rec = json.loads(raw)
            alert, reason = parse_cowrie(rec, f"hp-{run_id}-{seq:06d}")
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

    out = alerts_dir / "honeypot" / f"{run_id}.parquet"
    write_alerts(alerts, out)
    result.parquet_path = out
    skip_path = alerts_dir / "honeypot" / f"{run_id}.skips.jsonl"
    skip_path.parent.mkdir(parents=True, exist_ok=True)
    skip_path.write_text("".join(json.dumps(s) + "\n" for s in skips), encoding="utf-8")
    result.skip_log_path = skip_path
    return result
