"""Shared alert store: write normalized alerts to Parquet, read them back (record §6.7).

One format for all three normalizers (MQTT, flows, honeypot). The polymorphic `detail` is kept
losslessly as the alert's canonical JSON (`Alert.to_json`); the flat columns are for querying and
for the bundler (E3-05) to group by device and window without parsing every row.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from thesis.schema.alert import Alert

REPO_ROOT = Path(__file__).resolve().parents[2]
ALERTS_DIR = REPO_ROOT / "data" / "alerts"


@dataclass
class NormalizeResult:
    """Outcome of normalizing one run's source, shared by the MQTT, flow and honeypot normalizers.

    The invariant `alerts + skipped == lines` is the guard against silent dropping (§6.9).
    """

    run_id: str
    alerts: int = 0
    skipped: int = 0
    skip_reasons: Counter[str] = field(default_factory=Counter)
    parquet_path: Path | None = None
    skip_log_path: Path | None = None

    @property
    def lines(self) -> int:
        return self.alerts + self.skipped


_SCHEMA = pa.schema(
    [
        ("alert_id", pa.string()),
        ("source", pa.string()),
        ("ts", pa.timestamp("us", tz="UTC")),
        ("subject_device", pa.string()),
        ("event", pa.string()),
        ("alert_json", pa.string()),
    ]
)


def _event(alert: Alert) -> str:
    event = getattr(alert.detail, "event", None)
    return str(event) if event is not None else ""


def write_alerts(alerts: Iterable[Alert], path: Path) -> int:
    """Write alerts to Parquet, sorted by (ts, alert_id) for a reproducible file. Returns count."""
    rows = sorted(alerts, key=lambda a: (a.ts, a.alert_id))
    table = pa.table(
        {
            "alert_id": [a.alert_id for a in rows],
            "source": [a.source.value for a in rows],
            "ts": [a.ts for a in rows],
            "subject_device": [a.subject_device for a in rows],
            "event": [_event(a) for a in rows],
            "alert_json": [a.to_json() for a in rows],
        },
        schema=_SCHEMA,
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)
    return len(rows)


def read_alerts(path: Path) -> list[Alert]:
    rows = pq.read_table(path).to_pylist()
    return [Alert.model_validate_json(r["alert_json"]) for r in rows]
