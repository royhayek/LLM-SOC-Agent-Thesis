"""Console state in SQLite (E10-01, SCRUM-45).

The only thing the console writes: the human's accept/reject of a recommendation, stored here and
nowhere else (record §6.7). It never acts on the testbed or any network (§1.1). One decision per
(incident, condition): the same bundle has a different recommendation under each condition, so a
decision is tied to the recommendation the human actually reviewed. A later decision on the same
(incident, condition) replaces the earlier one.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "console" / "state.sqlite"

DECISIONS = ("accept", "reject")

_CREATE = (
    "CREATE TABLE IF NOT EXISTS decisions ("
    "bundle_id TEXT NOT NULL, condition TEXT NOT NULL, decision TEXT NOT NULL, "
    "note TEXT, decided_at TEXT NOT NULL, PRIMARY KEY (bundle_id, condition))"
)


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open (creating if needed) the console database with the decisions table.

    Migrates a pre-existing single-key table (decisions keyed by bundle_id alone) to the
    (bundle_id, condition) schema, attributing old rows to the full agent (C1)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cols = {row["name"] for row in conn.execute("PRAGMA table_info(decisions)").fetchall()}
    if cols and "condition" not in cols:  # old schema → migrate, keeping existing decisions
        conn.execute("ALTER TABLE decisions RENAME TO _decisions_old")
        conn.execute(_CREATE)
        conn.execute(
            "INSERT OR REPLACE INTO decisions (bundle_id, condition, decision, note, decided_at) "
            "SELECT bundle_id, 'C1', decision, note, decided_at FROM _decisions_old"
        )
        conn.execute("DROP TABLE _decisions_old")
    else:
        conn.execute(_CREATE)
    conn.commit()
    return conn


def record_decision(
    conn: sqlite3.Connection, bundle_id: str, condition: str, decision: str, note: str | None
) -> dict[str, str | None]:
    """Store (or replace) the human decision for one (incident, condition); accept or reject."""
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}, not {decision!r}")
    decided_at = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO decisions (bundle_id, condition, decision, note, decided_at) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(bundle_id, condition) DO UPDATE SET decision=excluded.decision, "
        "note=excluded.note, decided_at=excluded.decided_at",
        (bundle_id, condition, decision, note, decided_at),
    )
    conn.commit()
    return {
        "bundle_id": bundle_id,
        "condition": condition,
        "decision": decision,
        "note": note,
        "decided_at": decided_at,
    }


def get_decision(
    conn: sqlite3.Connection, bundle_id: str, condition: str
) -> dict[str, str | None] | None:
    row = conn.execute(
        "SELECT bundle_id, condition, decision, note, decided_at FROM decisions "
        "WHERE bundle_id = ? AND condition = ?",
        (bundle_id, condition),
    ).fetchone()
    return dict(row) if row is not None else None


def all_decisions(conn: sqlite3.Connection) -> list[dict[str, str | None]]:
    rows = conn.execute(
        "SELECT bundle_id, condition, decision, note, decided_at FROM decisions"
    ).fetchall()
    return [dict(row) for row in rows]


__all__ = ["DB_PATH", "DECISIONS", "all_decisions", "connect", "get_decision", "record_decision"]
