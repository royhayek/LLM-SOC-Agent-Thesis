"""The device-keyed 60-second bundle assembler (E3-05, SCRUM-64).

A bundle is every alert, from the configured sources, whose timestamp falls in window W and whose
subject device is D (record §4.1). Assembly happens outside the agent, deterministically, so every
condition sees the identical set of items and the comparisons stay paired. A bug here silently
invalidates every experiment, so the assembler is pinned by a stable `bundle_set_hash` and tested
hard (§6.9).

Windows tile contiguously per device from a fixed epoch `t0` (never each device's first alert), so
a bundle's window aligns exactly with the E2-04 label grid. Empty (device, window) cells form no
bundle (§4.1). Filtering the sources can empty a window, so a single-source condition sees a subset
of the all-sources bundles with the same ids — which keeps the H1 pairing well defined.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Iterable
from datetime import datetime, timedelta
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict

from thesis.labels.windows import WindowLabel
from thesis.schema.alert import Alert, Source

BENIGN = "benign"


class Bundle(BaseModel):
    model_config = ConfigDict(frozen=True)

    bundle_id: str
    device: str
    window_start: datetime
    window_end: datetime
    label: str
    episode_id: str | None
    sources: tuple[str, ...]  # sources present in this bundle, sorted
    alerts: tuple[Alert, ...]


def _window_start(ts: datetime, t0: datetime, window_s: int) -> datetime:
    index = int((ts - t0).total_seconds() // window_s)
    return t0 + timedelta(seconds=index * window_s)


def assemble(
    alerts: Iterable[Alert],
    labels: Iterable[WindowLabel],
    *,
    sources: set[Source],
    window_s: int,
    t0: datetime,
) -> list[Bundle]:
    """Group the configured sources' alerts into device-keyed windows, labelled from E2-04."""
    label_by_key = {(wl.device, wl.window_start): wl for wl in labels}

    grouped: dict[tuple[str, datetime], list[Alert]] = defaultdict(list)
    for alert in alerts:
        if alert.source not in sources:
            continue
        ws = _window_start(alert.ts, t0, window_s)
        grouped[(alert.subject_device, ws)].append(alert)

    bundles: list[Bundle] = []
    for (device, ws), items in grouped.items():
        ordered = tuple(sorted(items, key=lambda a: (a.ts, a.alert_id)))
        wl = label_by_key.get((device, ws))
        label = wl.label if wl is not None else BENIGN  # a window outside the grid is benign
        episode_id = wl.episode_id if wl is not None else None
        present = tuple(sorted({a.source.value for a in ordered}))
        bundles.append(
            Bundle(
                bundle_id=f"{device}|{ws.isoformat()}",
                device=device,
                window_start=ws,
                window_end=ws + timedelta(seconds=window_s),
                label=label,
                episode_id=episode_id,
                sources=present,
                alerts=ordered,
            )
        )
    return sorted(bundles, key=lambda b: b.bundle_id)


def bundle_set_hash(bundles: Iterable[Bundle]) -> str:
    """SHA-256 of the bundle set's identity: ids, labels, episode ids and alert membership."""
    canonical = [
        {
            "bundle_id": b.bundle_id,
            "label": b.label,
            "episode_id": b.episode_id,
            "sources": list(b.sources),
            "alert_ids": sorted(a.alert_id for a in b.alerts),
        }
        for b in sorted(bundles, key=lambda b: b.bundle_id)
    ]
    text = json.dumps(canonical, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


_SCHEMA = pa.schema(
    [
        ("bundle_id", pa.string()),
        ("device", pa.string()),
        ("window_start", pa.timestamp("us", tz="UTC")),
        ("window_end", pa.timestamp("us", tz="UTC")),
        ("label", pa.string()),
        ("episode_id", pa.string()),
        ("sources", pa.list_(pa.string())),
        ("alert_ids", pa.list_(pa.string())),
        ("n_alerts", pa.int64()),
    ]
)


def write_bundles(bundles: list[Bundle], path: Path) -> int:
    """Write the bundle set to Parquet (§6.7), one row per bundle, ordered by id. Returns count."""
    rows = sorted(bundles, key=lambda b: b.bundle_id)
    table = pa.table(
        {
            "bundle_id": [b.bundle_id for b in rows],
            "device": [b.device for b in rows],
            "window_start": [b.window_start for b in rows],
            "window_end": [b.window_end for b in rows],
            "label": [b.label for b in rows],
            "episode_id": [b.episode_id for b in rows],
            "sources": [list(b.sources) for b in rows],
            "alert_ids": [[a.alert_id for a in b.alerts] for b in rows],
            "n_alerts": [len(b.alerts) for b in rows],
        },
        schema=_SCHEMA,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)
    return len(rows)
