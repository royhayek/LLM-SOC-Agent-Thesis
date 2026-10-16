"""Console state in SQLite (E10-01, SCRUM-45).

The only thing the console writes: the human's accept/reject of a recommendation, stored here and
nowhere else (record §6.7). It never acts on the testbed or any network (§1.1). One decision per
incident (bundle); a later decision replaces the earlier one.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_PATH = REPO_ROOT / "data" / "console" / "state.sqlite"

DECISIONS = ("accept", "reject")


def connect(path: Path = DB_PATH) -> sqlite3.Connection:
    """Open (creating if needed) the console database with the decisions table."""
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS decisions ("
        "bundle_id TEXT PRIMARY KEY, decision TEXT NOT NULL, note TEXT, decided_at TEXT NOT NULL)"
    )
    conn.commit()
    return conn


def record_decision(
    conn: sqlite3.Connection, bundle_id: str, decision: str, note: str | None
) -> dict[str, str | None]:
    """Store (or replace) the human decision for one incident; `decision` is accept or reject."""
    if decision not in DECISIONS:
        raise ValueError(f"decision must be one of {DECISIONS}, not {decision!r}")
    decided_at = datetime.now(UTC).isoformat()
    conn.execute(
        "INSERT INTO decisions (bundle_id, decision, note, decided_at) VALUES (?, ?, ?, ?) "
        "ON CONFLICT(bundle_id) DO UPDATE SET decision=excluded.decision, note=excluded.note, "
        "decided_at=excluded.decided_at",
        (bundle_id, decision, note, decided_at),
    )
    conn.commit()
    return {"bundle_id": bundle_id, "decision": decision, "note": note, "decided_at": decided_at}


def get_decision(conn: sqlite3.Connection, bundle_id: str) -> dict[str, str | None] | None:
    row = conn.execute(
        "SELECT bundle_id, decision, note, decided_at FROM decisions WHERE bundle_id = ?",
        (bundle_id,),
    ).fetchone()
    return dict(row) if row is not None else None


def all_decisions(conn: sqlite3.Connection) -> dict[str, dict[str, str | None]]:
    rows = conn.execute("SELECT bundle_id, decision, note, decided_at FROM decisions").fetchall()
    return {row["bundle_id"]: dict(row) for row in rows}


__all__ = ["DB_PATH", "DECISIONS", "all_decisions", "connect", "get_decision", "record_decision"]
