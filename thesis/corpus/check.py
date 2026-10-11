"""Corpus integrity checks before the freeze (E2-07, SCRUM-74).

    python -m thesis.corpus.check   # writes docs/corpus/integrity_report.md, exits non-zero on fail

The last cheap chance to catch a broken corpus. Five checks, each a pass/fail line in the report;
any fail blocks the freeze (record §3 risks #2, #4). A failed check means regenerating the
affected chunks (E2-05), never patching the data by hand.

1. Every scheduled episode has an execution record.
2. Every episode has traces in each source its family's E1-14 visibility row predicts.
3. Window-level label counts per family meet their METHODS.md v1.1 targets.
4. No two executed episodes overlap on the same device.
5. No gap in capture longer than one window inside any chunk.

Window-level counts overestimate bundle counts (empty windows are dropped at assembly); E3-09
confirms the bundle-level numbers (ticket risk note).
"""

from __future__ import annotations

import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from thesis.labels.windows import labels_path, load_window_seconds, read_labels
from thesis.scenario.families.base import DEVICE_SERVICE, SERVICE_IP
from thesis.scenario.schedule import load_schedule

REPO_ROOT = Path(__file__).resolve().parents[2]
RC_DIR = REPO_ROOT / "data" / "raw" / "corpus-v1.0.0-rc"
SCHEDULE = REPO_ROOT / "schedules" / "corpus-v1.0.0.yaml"
FAMILIES_YAML = REPO_ROOT / "knowledge" / "attack_families.yaml"
CORPUS_CONFIG = REPO_ROOT / "config" / "corpus.yaml"
BOTNET_MANIFEST = REPO_ROOT / "scenarios" / "botnet_manifest.yaml"
REPORT = REPO_ROOT / "docs" / "corpus" / "integrity_report.md"

ATTACKER_IP = SERVICE_IP["attacker"]


@dataclass(frozen=True)
class Executed:
    id: str
    family: str
    device: str
    start: datetime
    end: datetime


@dataclass(frozen=True)
class Chunk:
    run_id: str
    episodes: list[Executed]
    flows: list[tuple[datetime, datetime, str, str]]  # (first_seen, last_seen, src_ip, dst_ip)
    cowrie_ts: list[datetime]
    flood_ts: list[datetime]
    brute_ts: list[datetime]
    mqtt_ts: list[datetime]  # every logged MQTT message, for the capture-continuity check


def _parse(ts: str) -> datetime:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _load_visibility() -> dict[str, dict[str, bool]]:
    data = yaml.safe_load(FAMILIES_YAML.read_text(encoding="utf-8"))
    return {f["id"]: f["visibility"] for f in data["families"]}


def _c2_ip() -> str:
    return str(yaml.safe_load(BOTNET_MANIFEST.read_text(encoding="utf-8"))["retargeting"]["dst_ip"])


def _read_chunk(run_dir: Path) -> Chunk:
    episodes: list[Executed] = []
    for line in (run_dir / "execution_log.jsonl").read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        r = json.loads(line)
        if (
            r.get("event") == "episode"
            and r.get("actual_start_utc")
            and r.get("exit_status") in (0, None)
        ):
            episodes.append(
                Executed(
                    r["id"],
                    r["family"],
                    r["target_device"],
                    _parse(r["actual_start_utc"]),
                    _parse(r["actual_end_utc"]),
                )
            )

    flows: list[tuple[datetime, datetime, str, str]] = []
    flows_path = run_dir / "flows" / "flows.jsonl"
    if flows_path.is_file():
        for line in flows_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            f = json.loads(line)
            first = datetime.fromtimestamp(f["bidirectional_first_seen_ms"] / 1000, tz=UTC)
            last = datetime.fromtimestamp(f["bidirectional_last_seen_ms"] / 1000, tz=UTC)
            flows.append((first, last, f.get("src_ip", ""), f.get("dst_ip", "")))

    cowrie_ts: list[datetime] = []
    cj = run_dir / "honeypot" / "cowrie.json"
    if cj.is_file():
        for line in cj.read_text(encoding="utf-8").splitlines():
            if line.strip():
                cowrie_ts.append(_parse(json.loads(line)["timestamp"]))

    flood_ts: list[datetime] = []
    mqtt_ts: list[datetime] = []
    ml = run_dir / "mqtt" / "mqtt.log"
    if ml.is_file():
        for line in ml.read_text(encoding="utf-8").splitlines():
            parts = line.split(" ", 2)
            if len(parts) < 2:
                continue
            ts = _parse(parts[0])
            mqtt_ts.append(ts)
            if "/flood" in parts[1]:
                flood_ts.append(ts)

    brute_ts: list[datetime] = []
    bl = run_dir / "mqtt" / "broker.log"
    if bl.is_file():
        for line in bl.read_text(encoding="utf-8").splitlines():
            if "not authori" in line and "brute" in line:
                brute_ts.append(_parse(line.split(": ", 1)[0]))

    return Chunk(run_dir.name, episodes, flows, cowrie_ts, flood_ts, brute_ts, mqtt_ts)


def _in(ts: list[datetime], start: datetime, end: datetime) -> int:
    return sum(1 for t in ts if start <= t < end)


def check_execution_records(chunks: list[Chunk], scheduled: set[str]) -> tuple[bool, str]:
    executed = {e.id for c in chunks for e in c.episodes}
    missing = scheduled - executed
    extra = executed - scheduled
    ok = not missing and not extra
    detail = f"{len(executed)}/{len(scheduled)} scheduled episodes executed"
    if missing:
        detail += f"; missing {sorted(missing)[:5]}"
    if extra:
        detail += f"; unexpected {sorted(extra)[:5]}"
    return ok, detail


def check_source_traces(
    chunks: list[Chunk], vis: dict[str, dict[str, bool]], c2: str
) -> tuple[bool, str]:
    failures: list[str] = []
    checked = 0
    for c in chunks:
        for e in c.episodes:
            checked += 1
            want = vis[e.family]
            if want.get("flows"):
                # The attack flow differs by family: ssh/scan/syn ride the attacker's connection,
                # botnet goes to the retargeted C2, and the MQTT families ride the device's own
                # connection to the broker (the flood/brute volume). A flow counts if it is active
                # during the episode (interval overlap), not only if it opened inside the window.
                if e.family == "botnet":
                    ip = c2
                elif e.family in ("mqtt_publish_flood", "mqtt_brute_force"):
                    ip = SERVICE_IP[DEVICE_SERVICE[e.device]]
                else:
                    ip = ATTACKER_IP
                n = sum(
                    1
                    for first, last, s, d in c.flows
                    if first < e.end and last >= e.start and ip in (s, d)
                )
                if n == 0:
                    failures.append(f"{e.id}: no attack flow")
            if want.get("honeypot") and _in(c.cowrie_ts, e.start, e.end) == 0:
                failures.append(f"{e.id}: no honeypot event")
            if want.get("mqtt"):
                hits = c.flood_ts if e.family == "mqtt_publish_flood" else c.brute_ts
                if _in(hits, e.start, e.end) == 0:
                    failures.append(f"{e.id}: no mqtt trace")
    ok = not failures
    detail = f"{checked} episodes checked against the E1-14 matrix"
    if failures:
        detail += f"; {len(failures)} missing: {failures[:5]}"
    return ok, detail


def check_label_counts(targets: dict[str, int]) -> tuple[bool, str]:
    counts: Counter[str] = Counter()
    for run_dir in sorted(RC_DIR.iterdir()):
        for wl in read_labels(labels_path(run_dir.name)):
            if wl.label != "benign":
                counts[wl.label] += 1
    short = {fam: (counts[fam], t) for fam, t in targets.items() if counts[fam] < t}
    ok = not short
    detail = "per-family windows: " + ", ".join(
        f"{f}={counts[f]}(>={t})" for f, t in targets.items()
    )
    if short:
        detail += f"; BELOW target: {short}"
    return ok, detail


def check_no_overlap(chunks: list[Chunk]) -> tuple[bool, str]:
    clashes: list[str] = []
    for c in chunks:
        by_device: dict[str, list[Executed]] = defaultdict(list)
        for e in c.episodes:
            by_device[e.device].append(e)
        for eps in by_device.values():
            eps.sort(key=lambda e: e.start)
            for a, b in zip(eps, eps[1:], strict=False):
                if b.start < a.end:
                    clashes.append(f"{a.id} & {b.id} on {a.device}")
    ok = not clashes
    return ok, ("no executed episodes overlap on one device" if ok else f"overlaps: {clashes[:5]}")


def check_capture_gaps(chunks: list[Chunk], window_s: int) -> tuple[bool, str]:
    worst = 0.0
    worst_chunk = ""
    for c in chunks:
        ts = sorted(c.mqtt_ts)
        for a, b in zip(ts, ts[1:], strict=False):
            gap = (b - a).total_seconds()
            if gap > worst:
                worst, worst_chunk = gap, c.run_id
    ok = worst <= window_s
    detail = f"largest MQTT-logging gap {worst:.0f} s (<= {window_s} s) in {worst_chunk or 'n/a'}"
    return ok, detail


def run_checks() -> tuple[list[tuple[str, bool, str]], bool]:
    schedule = load_schedule(SCHEDULE)
    scheduled = {e.id for e in schedule.episodes}
    vis = _load_visibility()
    c2 = _c2_ip()
    window_s = load_window_seconds()
    cfg = yaml.safe_load(CORPUS_CONFIG.read_text(encoding="utf-8"))
    eval_t = int(cfg["eval_bundles_per_family"])
    share = float(cfg["train_share"])
    per_family_target = eval_t + math.ceil(eval_t * share / (1 - share))
    targets = {fam: per_family_target for fam in cfg["families"]}

    chunks = [_read_chunk(d) for d in sorted(RC_DIR.iterdir()) if d.is_dir()]

    results = [
        (
            "1. every scheduled episode has an execution record",
            *check_execution_records(chunks, scheduled),
        ),
        (
            "2. every episode has traces in its predicted sources (E1-14)",
            *check_source_traces(chunks, vis, c2),
        ),
        ("3. per-family label counts meet the METHODS v1.1 targets", *check_label_counts(targets)),
        ("4. no two executed episodes overlap on one device", *check_no_overlap(chunks)),
        (
            "5. no capture gap longer than one window in any chunk",
            *check_capture_gaps(chunks, window_s),
        ),
    ]
    return results, all(ok for _, ok, _ in results)


def _write_report(results: list[tuple[str, bool, str]], passed: bool) -> None:
    lines = [
        "# Corpus v1.0.0 integrity report (E2-07, SCRUM-74)",
        "",
        "GENERATED by `python -m thesis.corpus.check` over `data/raw/corpus-v1.0.0-rc/` and "
        "`data/labels/`. Any failing check blocks the freeze (E2-09); the fix is to regenerate the "
        "affected chunks (E2-05), never to patch the data.",
        "",
        f"**Verdict: {'PASS' if passed else 'FAIL'}** — {sum(ok for _, ok, _ in results)}/"
        f"{len(results)} checks passed.",
        "",
        "| Check | Result | Detail |",
        "|---|---|---|",
    ]
    for name, ok, detail in results:
        lines.append(f"| {name} | {'PASS' if ok else 'FAIL'} | {detail} |")
    lines += [
        "",
        "Window-level counts (check 3) overestimate bundle counts, because empty windows are "
        "dropped at assembly; E3-09 confirms the bundle-level numbers.",
        "",
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    results, passed = run_checks()
    _write_report(results, passed)
    for name, ok, detail in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {name} — {detail}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
