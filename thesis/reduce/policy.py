"""The frozen reduction policy v1.0: a bundle to its reduced view (E3-06, SCRUM-77).

Implements `reduction-v1.0` (METHODS.md Annex E, `docs/methods/reduction_policy.md`) exactly: the
one compact-JSON view every condition receives, computed deterministically outside the agent. If
the agent saw a reduced view and a baseline the full one, H4 would be contaminated (§4.1), so this
is the single representation for all conditions. See the frozen Annex for every formula.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from collections.abc import Iterable
from datetime import datetime

from thesis.assemble.bundles import Bundle
from thesis.schema.alert import Alert, FlowDetail, HoneypotDetail, MqttDetail, Source
from thesis.schema.devices import DEVICES

POLICY_VERSION = "reduction-v1.0"

FLOW_EXEMPLARS = 5
MQTT_EXEMPLARS = 3
HONEYPOT_SEQUENCES = 3
OTHER_IDS = 5
CMD_DELIMITER = " ; "
CMD_CAP = 200

_DEVICE_IPS: dict[str, set[str]] = defaultdict(set)
for _ip, _id in DEVICES.items():
    _DEVICE_IPS[_id].add(_ip)


def _round(value: float, places: int) -> float:
    r = round(value, places)
    return int(r) if r == int(r) and places == 0 else r


def _stats(values: list[float]) -> dict[str, float] | None:
    if not values:
        return None
    ordered = sorted(values)
    n = len(ordered)
    median = ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2
    return {"min": round(ordered[0], 3), "median": round(median, 3), "max": round(ordered[-1], 3)}


def _flows(alerts: list[Alert], device: str) -> dict[str, object]:
    details = [a.detail for a in alerts if isinstance(a.detail, FlowDetail)]
    addr = _DEVICE_IPS.get(device, set())
    bytes_out = sum(d.bytes_fwd for d in details if d.src_ip in addr) + sum(
        d.bytes_bwd for d in details if d.dst_ip in addr
    )
    bytes_in = sum(d.bytes_bwd for d in details if d.src_ip in addr) + sum(
        d.bytes_fwd for d in details if d.dst_ip in addr
    )
    proto_counts = Counter(d.protocol for d in details)
    protocol_mix = {p: c for p, c in sorted(proto_counts.items(), key=lambda kv: (-kv[1], kv[0]))}
    tcp = [d for d in details if d.protocol == "tcp"]
    out: dict[str, object] = {
        "count": len(details),
        "unique_dst_ips": len({d.dst_ip for d in details}),
        "unique_dst_ports": len({d.dst_port for d in details}),
        "bytes_out": bytes_out,
        "bytes_in": bytes_in,
        "protocol_mix": protocol_mix,
    }
    if tcp:
        syn_only = sum(
            1 for d in tcp if (d.syn_count_fwd or 0) >= 1 and (d.ack_count_fwd or 0) == 0
        )
        out["syn_only_ratio"] = round(syn_only / len(tcp), 2)
    stats = _stats([d.duration_s for d in details])
    if stats:
        out["duration_s"] = stats
    return out


def _mqtt(alerts: list[Alert]) -> dict[str, object]:
    details = [a.detail for a in alerts if isinstance(a.detail, MqttDetail)]
    pubs = [d for d in details if d.event == "publish"]
    out: dict[str, object] = {
        "message_count": len(pubs),
        "unique_topics": len({d.topic for d in pubs if d.topic}),
    }
    payloads = _stats([float(d.payload_bytes) for d in pubs if d.payload_bytes is not None])
    if payloads:
        out["payload_bytes"] = payloads
    out["qos_mix"] = {
        str(q): c for q, c in sorted(Counter(d.qos for d in pubs if d.qos is not None).items())
    }
    out["connect_count"] = sum(1 for d in details if d.event == "connect")
    out["disconnect_count"] = sum(1 for d in details if d.event == "disconnect")
    out["auth_failures"] = sum(1 for d in details if d.event == "auth_failure")
    return out


def _honeypot(alerts: list[Alert]) -> dict[str, object]:
    details = [a.detail for a in alerts if isinstance(a.detail, HoneypotDetail)]
    connects = {d.session_id for d in details if d.event == "session_connect"}
    succ = sum(1 for d in details if d.event == "login_success")
    fail = sum(1 for d in details if d.event == "login_failed")
    return {
        "session_count": len(connects),
        "unique_src_ips": len({d.src_ip for d in details}),
        "auth_attempts": succ + fail,
        "login_success": succ,
        "login_failed": fail,
    }


def _detector_block(alerts: list[Alert], top: Alert | None) -> dict[str, object]:
    scores = [a.detector_score for a in alerts if a.detector_score is not None]
    block: dict[str, object] = {}
    if scores:
        block["max_score"] = round(max(scores), 2)
    if top is not None and top.detector_label is not None:
        block["label"] = top.detector_label
    return block


def _rank(alerts: list[Alert]) -> list[Alert]:
    # Detector score descending; alerts without a score last; tie-break earlier ts then alert_id.
    return sorted(
        alerts,
        key=lambda a: (a.detector_score is None, -(a.detector_score or 0.0), a.ts, a.alert_id),
    )


def _t(alert: Alert, window_start: datetime) -> float:
    return round((alert.ts - window_start).total_seconds(), 3)


def _flow_exemplar(a: Alert, window_start: datetime) -> dict[str, object]:
    d = a.detail
    assert isinstance(d, FlowDetail)
    ex: dict[str, object] = {
        "id": a.alert_id,
        "t": _t(a, window_start),
        "src": f"{d.src_ip}:{d.src_port}",
        "dst": f"{d.dst_ip}:{d.dst_port}",
        "proto": d.protocol,
        "dur_s": round(d.duration_s, 3),
        "bytes_fwd": d.bytes_fwd,
        "bytes_bwd": d.bytes_bwd,
        "pkts_fwd": d.packets_fwd,
        "pkts_bwd": d.packets_bwd,
    }
    if d.tcp_flags is not None:
        ex["flags"] = d.tcp_flags
    if a.detector_score is not None:
        ex["score"] = round(a.detector_score, 2)
    return ex


def _mqtt_exemplar(a: Alert, window_start: datetime) -> dict[str, object]:
    d = a.detail
    assert isinstance(d, MqttDetail)
    ex: dict[str, object] = {"id": a.alert_id, "t": _t(a, window_start), "event": d.event}
    for key, val in (
        ("client", d.client_id),
        ("topic", d.topic),
        ("qos", d.qos),
        ("payload_bytes", d.payload_bytes),
    ):
        if val is not None:
            ex[key] = val
    if a.detector_score is not None:
        ex["score"] = round(a.detector_score, 2)
    return ex


def _clean(text: str) -> str:
    return "".join(" " if (ord(c) < 0x20 or ord(c) == 0x7F) else c for c in text)


def _cmd_sequence(session_alerts: list[Alert]) -> str:
    commands: list[str] = []
    for a in session_alerts:
        d = a.detail
        if (
            isinstance(d, HoneypotDetail)
            and d.event in ("command", "command_failed")
            and d.command is not None
        ):
            commands.append(d.command)
    joined = CMD_DELIMITER.join(_clean(c) for c in commands)
    if len(joined) > CMD_CAP:
        removed = len(joined) - CMD_CAP
        joined = joined[:CMD_CAP] + f"…[+{removed} chars]"
    return joined


def _hp_event(a: Alert) -> str:
    assert isinstance(a.detail, HoneypotDetail)
    return a.detail.event


def _honeypot_sequences(alerts: list[Alert]) -> list[dict[str, object]]:
    by_session: dict[str, list[Alert]] = defaultdict(list)
    for a in alerts:
        if isinstance(a.detail, HoneypotDetail):
            by_session[a.detail.session_id].append(a)
    ranked: list[tuple[int, datetime, dict[str, object]]] = []
    for sid, items in by_session.items():
        cmds = [a for a in items if _hp_event(a) in ("command", "command_failed")]
        if not cmds:
            continue
        cmds_sorted = sorted(cmds, key=lambda a: a.ts)
        connect = next((a for a in items if _hp_event(a) == "session_connect"), cmds_sorted[0])
        cd = connect.detail
        assert isinstance(cd, HoneypotDetail)
        src = f"{cd.src_ip}:{cd.src_port}" if cd.src_port is not None else cd.src_ip
        ex: dict[str, object] = {
            "id": cmds_sorted[0].alert_id,
            "session": sid,
            "src": src,
            "cmd": _cmd_sequence(items),
        }
        ranked.append((len(cmds), cmds_sorted[0].ts, ex))
    ranked.sort(key=lambda r: (-r[0], r[1]))
    return [r[2] for r in ranked[:HONEYPOT_SEQUENCES]]


def _other_ids(ranked: list[Alert], exemplar_ids: set[str]) -> list[str]:
    ids = [a.alert_id for a in ranked if a.alert_id not in exemplar_ids]
    return ids[:OTHER_IDS]


_HP_CLASS = {"command": 0, "command_failed": 0, "login_success": 1, "login_failed": 2}


def _honeypot_other_ids(alerts: list[Alert], shown: set[str]) -> list[str]:
    hp = [a for a in alerts if isinstance(a.detail, HoneypotDetail) and a.alert_id not in shown]
    ordered = sorted(hp, key=lambda a: (_HP_CLASS.get(_hp_event(a), 3), a.ts, a.alert_id))
    return [a.alert_id for a in ordered][:OTHER_IDS]


def reduce(bundle: Bundle, sources: Iterable[Source] = tuple(Source)) -> dict[str, object]:
    """Reduce a bundle to its view. `sources` are the sources in configuration (default all)."""
    configured = set(sources)
    by_source: dict[Source, list[Alert]] = {s: [] for s in Source}
    for a in bundle.alerts:
        by_source[a.source].append(a)

    state: dict[str, str] = {}
    for s in (Source.FLOWS, Source.MQTT, Source.HONEYPOT):
        if s not in configured:
            state[s.value] = "not_in_config"
        elif by_source[s]:
            state[s.value] = "active"
        else:
            state[s.value] = "no_alerts"

    view: dict[str, object] = {
        "bundle_id": bundle.bundle_id,
        "window": [bundle.window_start.isoformat(), bundle.window_end.isoformat()],
        "device": bundle.device,
        "sources": state,
    }

    for s in (Source.FLOWS, Source.MQTT, Source.HONEYPOT):
        if state[s.value] != "active":
            continue
        alerts = by_source[s]
        if s is Source.FLOWS:
            block: dict[str, object] = _flows(alerts, bundle.device)
        elif s is Source.MQTT:
            block = _mqtt(alerts)
        else:
            block = _honeypot(alerts)
        ranked = _rank(alerts)
        det = _detector_block(alerts, ranked[0] if ranked else None)
        if det:
            block["detector"] = det
        if s is Source.FLOWS:
            exemplars = [_flow_exemplar(a, bundle.window_start) for a in ranked[:FLOW_EXEMPLARS]]
            block["exemplars"] = exemplars
            other = _other_ids(ranked, {str(e["id"]) for e in exemplars})
        elif s is Source.MQTT:
            exemplars = [_mqtt_exemplar(a, bundle.window_start) for a in ranked[:MQTT_EXEMPLARS]]
            block["exemplars"] = exemplars
            other = _other_ids(ranked, {str(e["id"]) for e in exemplars})
        else:
            seqs = _honeypot_sequences(alerts)
            block["exemplars"] = seqs
            other = _honeypot_other_ids(alerts, {str(e["id"]) for e in seqs})
        if other:
            block["other_ids"] = other
        view[s.value] = block
    return view


def to_json(view: dict[str, object]) -> str:
    """Compact JSON (Annex E §8): no whitespace, UTF-8 as-is, keys in insertion order."""
    return json.dumps(view, separators=(",", ":"), ensure_ascii=False)
