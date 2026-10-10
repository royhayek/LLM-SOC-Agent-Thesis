"""Mechanical window labelling (E2-04). Ground truth comes only from the executed schedule
(record §4.1); there is no manual-edit path, by design (risk #1).

A window is labelled family F when it overlaps, by any non-zero duration, an *executed* episode
of F against the same device D; otherwise `benign` (METHODS.md §1). Windows are half-open,
`[t0 + W*i, t0 + W*(i+1))`, W = 60 s read from `config/incident.yaml` (not hardcoded). Each
window keeps the overlapping episode's id, which the episode block bootstrap needs (§4.3).

`label_windows()` is a pure function over executed episodes and the window grid. A window may
overlap at most one episode per device (the schedule never overlaps two episodes on one device,
and the corpus schedule spaces episodes so none share a window); a window overlapping two
distinct episodes is a schedule error and raises, rather than silently mislabelling.

The Parquet writer (`data/labels/<run_id>.parquet`) is added once ADR-0010 (the Parquet library)
is accepted; this module currently produces the labels in memory.
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Final, NamedTuple

import yaml  # type: ignore[import-untyped]

from thesis.schema.verdict import IncidentType

REPO_ROOT: Final = Path(__file__).resolve().parent.parent.parent
INCIDENT_CONFIG: Final = REPO_ROOT / "config" / "incident.yaml"
BENIGN: Final = IncidentType.BENIGN.value
_FAMILIES: Final = {t.value for t in IncidentType}


class ExecutedEpisode(NamedTuple):
    """One executed episode, from the execution log (actual times, never planned)."""

    id: str
    family: str
    device: str
    start: datetime
    end: datetime


class WindowLabel(NamedTuple):
    device: str
    window_start: datetime
    label: str
    episode_id: str | None


class LabelConflictError(ValueError):
    """A window overlaps two distinct episodes on one device: the schedule is wrong."""


def load_window_seconds(path: Path = INCIDENT_CONFIG) -> int:
    seconds = int(yaml.safe_load(path.read_text(encoding="utf-8"))["window_seconds"])
    if seconds <= 0:
        raise ValueError("window_seconds must be positive")
    return seconds


def _overlaps(ws: datetime, we: datetime, es: datetime, ee: datetime) -> bool:
    """Half-open overlap: the window [ws, we) and the episode [es, ee) share non-zero duration."""
    return es < we and ws < ee


def label_windows(
    episodes: Iterable[ExecutedEpisode],
    t0: datetime,
    end: datetime,
    devices: Iterable[str],
    window_s: int,
) -> list[WindowLabel]:
    """Label every window of every device in the grid `[t0, end)` tiled by `window_s`.

    `t0` and `end` must be timezone-aware (UTC); a naive/aware mix raises. Windows run while
    `t0 + W*i < end`. A window with no overlapping episode is `benign` with no episode id.
    """
    if t0.tzinfo is None or end.tzinfo is None:
        raise ValueError("t0 and end must be timezone-aware (UTC)")
    if end <= t0:
        raise ValueError("end must be after t0")

    by_device: dict[str, list[ExecutedEpisode]] = defaultdict(list)
    for e in episodes:
        if e.family not in _FAMILIES or e.family == BENIGN:
            raise ValueError(f"episode {e.id} has non-family label {e.family!r}")
        if e.start.tzinfo is None or e.end.tzinfo is None:
            raise ValueError(f"episode {e.id} times must be timezone-aware (UTC)")
        by_device[e.device].append(e)

    n_windows = math.ceil((end - t0).total_seconds() / window_s)
    out: list[WindowLabel] = []
    for device in sorted(set(devices)):
        device_eps = by_device.get(device, [])
        for i in range(n_windows):
            ws = t0 + timedelta(seconds=window_s * i)
            we = ws + timedelta(seconds=window_s)
            overlapping = [e for e in device_eps if _overlaps(ws, we, e.start, e.end)]
            if not overlapping:
                out.append(WindowLabel(device, ws, BENIGN, None))
                continue
            if len({e.id for e in overlapping}) > 1:
                raise LabelConflictError(
                    f"{device} window {ws.isoformat()} overlaps episodes "
                    f"{sorted(e.id for e in overlapping)}; the schedule must not share a window"
                )
            e = overlapping[0]
            out.append(WindowLabel(device, ws, e.family, e.id))
    return out


def read_executed_episodes(execution_log: Path) -> list[ExecutedEpisode]:
    """Executed episodes from a run's `execution_log.jsonl` (actual times; skips `no_runner`)."""
    episodes: list[ExecutedEpisode] = []
    for line in execution_log.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("event") != "episode" or row.get("actual_start_utc") is None:
            continue
        episodes.append(
            ExecutedEpisode(
                id=row["id"],
                family=row["family"],
                device=row["target_device"],
                start=datetime.fromisoformat(row["actual_start_utc"]),
                end=datetime.fromisoformat(row["actual_end_utc"]),
            )
        )
    return episodes
