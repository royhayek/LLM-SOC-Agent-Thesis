"""The localhost-only SOC console REST API (E10-01, SCRUM-45).

Serves, read-only, what the experiments already wrote (record §2, §5): the incidents and their
verdicts (from the results Parquet, E9-02), the human-readable reports (E7-08) and the audit log
(E7-05). The one write endpoint stores the human accept/reject in SQLite (E10-01 db). The `Verdict`
model (E7-01) is reused as the response model, so the safety schema and the API schema cannot drift
(§6.2). No authentication; binds to 127.0.0.1 only (§4, §6.8). The system recommends and never
executes: no route acts on the testbed or any network (§1.1).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, cast

from fastapi import FastAPI, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from thesis.api import db
from thesis.safety.audit import AUDIT_PATH, AuditRecord
from thesis.schema.verdict import Verdict

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PARQUET = REPO_ROOT / "results" / "results.parquet"
REPORTS_DIR = REPO_ROOT / "reports"

HOST = "127.0.0.1"  # localhost only (§4, §6.8); never 0.0.0.0
PORT = 8000

# The console shows the full agent's verdict: C1 = all three sources, agentic, enforcing.
PRIMARY_SOURCES = frozenset({"flows", "mqtt", "honeypot"})


class Incident(BaseModel):
    """One evaluated bundle with the full agent's verdict and any recorded human decision."""

    bundle_id: str
    ground_truth: str
    emitted: bool
    verdict: Verdict | None  # the Verdict schema itself, so the contract cannot drift (§6.2)
    decision: str | None  # the human accept/reject, if one is stored


class DecisionIn(BaseModel):
    decision: Literal["accept", "reject"]
    note: str | None = None


class DecisionOut(BaseModel):
    bundle_id: str
    decision: str
    note: str | None
    decided_at: str


def _verdict_from_row(row: dict[str, object]) -> Verdict | None:
    """Rebuild the `Verdict` from a result row's emitted fields, or None if the bundle was withheld
    or unparsed. The agent recommends only; nothing here acts."""
    if not bool(row.get("emitted")) or row.get("incident_type") is None:
        return None
    return Verdict.model_validate(
        {
            "classification": {
                "incident_type": row["incident_type"],
                "confidence": row["confidence"],
            },
            "recommendation": {
                "recommended_action": row["recommended_action"],
                "severity": row["severity"],
            },
            "affected_device": row["affected_device"] or "",
            "evidence": list(cast("list[object]", row.get("evidence") or [])),
        }
    )


def _load_primary_incidents(results_path: Path) -> dict[str, dict[str, object]]:
    """One row per bundle from the C1 condition (agentic, enforcing, all sources), repetition 0."""
    if not results_path.exists():
        return {}
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    out: dict[str, dict[str, object]] = {}
    for row in pq.read_table(results_path).to_pylist():
        if (
            str(row["strategy"]) == "agentic"
            and str(row["safety"]) == "enforcing"
            and frozenset(str(s) for s in row["sources"]) == PRIMARY_SOURCES
            and int(row["repetition"]) == 0
        ):
            out[str(row["bundle_id"])] = row
    return out


def create_app(
    *,
    results_path: Path = RESULTS_PARQUET,
    reports_dir: Path = REPORTS_DIR,
    audit_path: Path = AUDIT_PATH,
    db_path: Path = db.DB_PATH,
) -> FastAPI:
    """Build the console API over the given artifact paths (so tests can point at fixtures)."""
    app = FastAPI(title="SOC console", description="Read-only over experiment outputs (E10-01).")
    incidents = _load_primary_incidents(results_path)

    def _incident(bundle_id: str, row: dict[str, object]) -> Incident:
        conn = db.connect(db_path)
        try:
            decision = db.get_decision(conn, bundle_id)
        finally:
            conn.close()
        return Incident(
            bundle_id=bundle_id,
            ground_truth=str(row["ground_truth"]),
            emitted=bool(row["emitted"]),
            verdict=_verdict_from_row(row),
            decision=None if decision is None else str(decision["decision"]),
        )

    @app.get("/incidents")
    def list_incidents() -> list[Incident]:
        return [_incident(bid, incidents[bid]) for bid in sorted(incidents)]

    @app.get("/incidents/{bundle_id}")
    def get_incident(bundle_id: str) -> Incident:
        if bundle_id not in incidents:
            raise HTTPException(status_code=404, detail="unknown incident")
        return _incident(bundle_id, incidents[bundle_id])

    @app.get("/reports/{bundle_id}", response_class=PlainTextResponse)
    def get_report(bundle_id: str) -> str:
        path = reports_dir / f"{bundle_id}.md"
        if not path.exists():
            raise HTTPException(status_code=404, detail="no report for this incident")
        return path.read_text(encoding="utf-8")

    @app.get("/audit")
    def get_audit() -> list[AuditRecord]:
        if not audit_path.exists():
            return []
        records = []
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                records.append(AuditRecord.model_validate(json.loads(line)))
        return records

    @app.post("/incidents/{bundle_id}/decision")
    def post_decision(bundle_id: str, body: DecisionIn) -> DecisionOut:
        if bundle_id not in incidents:
            raise HTTPException(status_code=404, detail="unknown incident")
        conn = db.connect(db_path)
        try:
            stored = db.record_decision(conn, bundle_id, body.decision, body.note)
        finally:
            conn.close()
        return DecisionOut.model_validate(stored)

    return app


def run() -> None:  # pragma: no cover - the live server
    import uvicorn

    uvicorn.run(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":  # pragma: no cover
    run()


__all__ = ["HOST", "PORT", "DecisionIn", "DecisionOut", "Incident", "create_app", "run"]
