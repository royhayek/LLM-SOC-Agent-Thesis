"""The localhost-only SOC console REST API (E10-01, E10-04..E10-07).

Serves, read-only, what the experiments already wrote (record §2, §5): the incidents and their
verdicts (from the results Parquet, E9-02) per condition, the human-readable reports (E7-08), the
reasoning trace (E0-10 call log, over SSE) and the audit log (E7-05). The one write endpoint stores
the human accept/reject in SQLite (E10-01 db). The `Verdict` model (E7-01) is reused as the response
model, so the safety schema and the API schema cannot drift (§6.2). No authentication; binds to
127.0.0.1 only (§4, §6.8). The system recommends and never executes: no route acts on the testbed
or any network (§1.1).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from pathlib import Path
from typing import Literal, cast

import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel

from thesis.api import db, demo
from thesis.obs.logging import LOG_PATH
from thesis.report.render import report_filename
from thesis.safety.audit import AUDIT_PATH, AuditRecord
from thesis.schema.verdict import Verdict

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PARQUET = REPO_ROOT / "results" / "results.parquet"
REPORTS_DIR = REPO_ROOT / "reports"
CONDITIONS_YAML = REPO_ROOT / "config" / "conditions.yaml"

HOST = "127.0.0.1"  # localhost only (§4, §6.8); never 0.0.0.0
PORT = 8000
DEFAULT_CONDITION = "C1"  # the full agent

# The three reasoning nodes in order, and the SSE event name each is streamed under.
NODE_EVENT = {"evidence": "evidence", "classification": "classify", "recommendation": "recommend"}


class Incident(BaseModel):
    """One evaluated bundle under one condition, with its verdict and any human decision."""

    bundle_id: str
    condition: str  # C1..C7
    ground_truth: str
    emitted: bool
    verdict: Verdict | None  # the Verdict schema itself, so the contract cannot drift (§6.2)
    decision: str | None  # the human accept/reject, if one is stored


class DecisionIn(BaseModel):
    decision: Literal["accept", "reject"]
    note: str | None = None


class DecisionOut(BaseModel):
    bundle_id: str
    condition: str
    decision: str
    note: str | None
    decided_at: str


class ScenarioEvents(BaseModel):
    """A demo scenario and its time-ordered replay events, under one condition."""

    scenario: demo.Scenario
    condition: str
    window_seconds: float
    events: list[demo.DemoEvent]


def _condition_labels(path: Path = CONDITIONS_YAML) -> dict[tuple[str, str, frozenset[str]], str]:
    """Map each condition's (strategy, safety, sources) signature to its C-label (conditions.yaml
    order). The signature is provenance-independent, so it matches the stored result rows."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return {
        (c["strategy"], c["safety"], frozenset(c["sources"])): f"C{i + 1}"
        for i, c in enumerate(data["conditions"])
    }


def _verdict_from_row(row: dict[str, object]) -> Verdict | None:
    """Rebuild the `Verdict` from a result row's emitted fields, or None if withheld/unparsed."""
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


def _load_by_condition(
    results_path: Path, labels: dict[tuple[str, str, frozenset[str]], str]
) -> dict[str, dict[str, dict[str, object]]]:
    """Result rows at repetition 0, grouped by condition label then bundle id."""
    if not results_path.exists():
        return {}
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    out: dict[str, dict[str, dict[str, object]]] = {}
    for row in pq.read_table(results_path).to_pylist():
        if int(row["repetition"]) != 0:
            continue
        sig = (str(row["strategy"]), str(row["safety"]), frozenset(str(s) for s in row["sources"]))
        label = labels.get(sig)
        if label is not None:
            out.setdefault(label, {})[str(row["bundle_id"])] = row
    return out


def _load_trace(call_log_path: Path, bundle_id: str, config_hash: str) -> list[dict[str, object]]:
    """The recorded reasoning trace for one bundle+condition run, in node order, from the call log
    (E0-10). Replayed only. Empty if no trace was recorded (e.g. Baseline A makes no calls)."""
    if not call_log_path.exists():
        return []
    completions: dict[str, str] = {}
    for line in call_log_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if (
            str(rec.get("bundle_id")) == bundle_id
            and str(rec.get("config_hash")) == config_hash
            and int(rec.get("repetition", -1)) == 0
            and str(rec.get("node")) in NODE_EVENT
        ):
            completions[str(rec["node"])] = str(rec.get("completion", ""))
    return [
        # `untrusted`: the completion can echo attacker-controlled bundle text; the frontend must
        # escape it on display (ticket gotcha).
        {
            "node": node,
            "event": NODE_EVENT[node],
            "completion": completions[node],
            "untrusted": True,
        }
        for node in NODE_EVENT
        if node in completions
    ]


def create_app(
    *,
    results_path: Path = RESULTS_PARQUET,
    reports_dir: Path = REPORTS_DIR,
    audit_path: Path = AUDIT_PATH,
    db_path: Path = db.DB_PATH,
    call_log_path: Path = LOG_PATH,
    conditions_path: Path = CONDITIONS_YAML,
    scenarios_path: Path = demo.SCENARIOS_PATH,
    eval_path: Path = demo.EVAL_PARQUET,
    annotated_dirs: list[Path] | None = None,
    demo_bundle_meta: dict[str, demo.BundleMeta] | None = None,
    demo_alert_index: dict[str, demo.AlertRow] | None = None,
) -> FastAPI:
    """Build the console API over the given artifact paths (so tests can point at fixtures)."""
    app = FastAPI(title="SOC console", description="Read-only over experiment outputs (EPIC-10).")
    by_condition = _load_by_condition(results_path, _condition_labels(conditions_path))

    # Demo-simulator data: the catalog, and the bundle/alert indexes (loaded once, or injected by
    # tests). Missing artifacts degrade to an empty catalog so the app still starts.
    scenarios = (
        {s.id: s for s in demo.load_scenarios(scenarios_path)} if scenarios_path.exists() else {}
    )
    if demo_bundle_meta is not None:
        bundle_meta = demo_bundle_meta
    elif eval_path.exists():
        bundle_meta = demo.load_bundle_meta(eval_path)
    else:
        bundle_meta = {}
    alert_index = (
        demo_alert_index
        if demo_alert_index is not None
        else demo.load_alert_index(
            annotated_dirs if annotated_dirs is not None else demo.ANNOTATED_DIRS
        )
    )

    def _incident(
        condition: str, bundle_id: str, row: dict[str, object], conn: sqlite3.Connection
    ) -> Incident:
        decision = db.get_decision(conn, bundle_id, condition)
        return Incident(
            bundle_id=bundle_id,
            condition=condition,
            ground_truth=str(row["ground_truth"]),
            emitted=bool(row["emitted"]),
            verdict=_verdict_from_row(row),
            decision=None if decision is None else str(decision["decision"]),
        )

    def _rows_for(condition: str) -> dict[str, dict[str, object]]:
        if condition not in by_condition:
            raise HTTPException(status_code=404, detail="unknown condition")
        return by_condition[condition]

    @app.get("/conditions")
    def list_conditions() -> list[str]:
        return sorted(by_condition)

    @app.get("/incidents")
    def list_incidents(
        condition: str = DEFAULT_CONDITION,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> list[Incident]:
        rows = _rows_for(condition)
        page = sorted(rows)[offset : offset + limit]
        conn = db.connect(db_path)
        try:
            return [_incident(condition, bid, rows[bid], conn) for bid in page]
        finally:
            conn.close()

    @app.get("/incidents/{bundle_id}")
    def get_incident(bundle_id: str, condition: str = DEFAULT_CONDITION) -> Incident:
        rows = _rows_for(condition)
        if bundle_id not in rows:
            raise HTTPException(status_code=404, detail="unknown incident")
        conn = db.connect(db_path)
        try:
            return _incident(condition, bundle_id, rows[bundle_id], conn)
        finally:
            conn.close()

    @app.get("/incidents/{bundle_id}/trace")
    def get_trace(bundle_id: str, condition: str = DEFAULT_CONDITION) -> StreamingResponse:
        rows = _rows_for(condition)
        if bundle_id not in rows:
            raise HTTPException(status_code=404, detail="unknown incident")
        trace = _load_trace(call_log_path, bundle_id, str(rows[bundle_id]["config_hash"]))
        if not trace:
            raise HTTPException(status_code=404, detail="no recorded trace for this incident")

        def events() -> Iterator[str]:
            for step in trace:
                yield f"event: {step['event']}\ndata: {json.dumps(step)}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.get("/reports/{bundle_id}", response_class=PlainTextResponse)
    def get_report(bundle_id: str) -> str:
        # Same sanitised name the renderer writes (bundle ids carry ':' and '|').
        path = reports_dir / report_filename(bundle_id)
        if not path.exists():
            raise HTTPException(status_code=404, detail="no report for this incident")
        return path.read_text(encoding="utf-8")

    @app.get("/audit")
    def get_audit(
        outcome: str | None = None,
        limit: int = Query(default=100, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> list[AuditRecord]:
        if not audit_path.exists():
            return []
        records: list[AuditRecord] = []
        for line in audit_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = AuditRecord.model_validate(json.loads(line))
            if outcome is None or record.validator_outcome == outcome:
                records.append(record)
        return records[offset : offset + limit]

    @app.post("/incidents/{bundle_id}/decision")
    def post_decision(
        bundle_id: str, body: DecisionIn, condition: str = DEFAULT_CONDITION
    ) -> DecisionOut:
        # The decision is tied to the recommendation reviewed, so the incident must exist under the
        # given condition (each condition has its own verdict for the same bundle).
        if bundle_id not in _rows_for(condition):
            raise HTTPException(status_code=404, detail="unknown incident")
        conn = db.connect(db_path)
        try:
            stored = db.record_decision(conn, bundle_id, condition, body.decision, body.note)
        finally:
            conn.close()
        return DecisionOut.model_validate(stored)

    @app.get("/demo/scenarios")
    def list_scenarios() -> list[demo.Scenario]:
        return list(scenarios.values())

    @app.get("/demo/scenarios/{scenario_id}")
    def scenario_events(scenario_id: str, condition: str = DEFAULT_CONDITION) -> ScenarioEvents:
        scenario = scenarios.get(scenario_id)
        if scenario is None:
            raise HTTPException(status_code=404, detail="unknown scenario")
        rows = _rows_for(condition)
        events = demo.build_scenario_events(
            scenario,
            condition,
            meta=bundle_meta,
            alerts=alert_index,
            rows_by_bundle=rows,
            call_log_path=call_log_path,
        )
        window = max((e.t for e in events), default=0.0)
        return ScenarioEvents(
            scenario=scenario, condition=condition, window_seconds=window, events=events
        )

    return app


def run() -> None:  # pragma: no cover - the live server
    import uvicorn

    uvicorn.run(create_app(), host=HOST, port=PORT)


if __name__ == "__main__":  # pragma: no cover
    run()


__all__ = ["HOST", "PORT", "DecisionIn", "DecisionOut", "Incident", "create_app", "run"]
