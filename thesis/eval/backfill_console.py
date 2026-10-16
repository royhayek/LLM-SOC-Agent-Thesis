"""Backfill the console's reports and audit log from the frozen full-run outputs.

The full matrix run (E9-09) wrote only the result rows; it never rendered the E7-08 incident reports
nor wrote the E7-05 audit log. This module regenerates both from the frozen artifacts, **making no
model call**, so the console (EPIC-10) has something to show:

- **Reports** (`reports/`): the E7-08 renderer over the full-agent (C1) verdict, the node-1 findings
  recovered from the call log, and the real bundle. A C1 bundle with a withheld verdict gets a short
  "withheld" stub, so every incident resolves (no 404 in the Report panel).
- **Audit log** (`logs/audit.jsonl`): a **faithful replay** of the deterministic validator and
  safety stage (`apply_safety`) over the node-2 and node-3 completions recorded in the call log, for
  each agentic condition (C1-C5). The frozen rejection policy makes exactly one node-3 attempt, so
  there is exactly one record per item — the same record `apply_safety` built during the live run.
  The baselines (C6 prompt_only, C7 ml_classifier) never run the validator, so they produce none.

This is a **derived view of frozen data, regenerated after the fact** — not a live capture. It
reads the results Parquet and the call log, recomputes the condition hashes from the rows' own
provenance, and replays deterministic code. It changes no result, no locked parameter and no methods
contract, and may be re-run at any time:

    uv run python -m thesis.eval.backfill_console
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import cast

from pydantic import ValidationError

from thesis.agent.graph import _verdict_completion
from thesis.agent.models import Classification, Findings, Recommendation
from thesis.assemble.bundles import Bundle
from thesis.config import ExperimentConfig, Strategy, config_hash
from thesis.llm.parse import json_payload
from thesis.obs.logging import LOG_PATH
from thesis.report.render import REPORTS_DIR, render_report, report_filename
from thesis.safety.audit import AUDIT_PATH, AuditRecord, write_audit
from thesis.safety.stage import apply_safety
from thesis.safety.switch import SafetyMode
from thesis.schema.verdict import Verdict

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_PARQUET = REPO_ROOT / "results" / "results.parquet"

# The three graph nodes, by the name they log under (node 1, 2, 3).
NODES = ("evidence", "classification", "recommendation")

# key -> completion, keyed by (config_hash, bundle_id, node) at repetition 0.
Completions = dict[tuple[str, str, str], str]


def load_result_rows(results_path: Path = RESULTS_PARQUET) -> list[dict[str, object]]:
    """The repetition-0 result rows (one per bundle × condition), as plain dicts."""
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    rows = pq.read_table(results_path).to_pylist()
    return [r for r in rows if int(r["repetition"]) == 0]


def conditions_by_hash(
    rows: list[dict[str, object]],
) -> tuple[dict[str, ExperimentConfig], dict[str, str]]:
    """Rebuild the 7 conditions with the run's own provenance (so `config_hash` matches the stored
    hashes), keyed by hash, plus a hash → C-label map (conditions.yaml order)."""
    from thesis.eval.results import provenance_from_rows
    from thesis.eval.run import load_conditions

    conditions = load_conditions(provenance_from_rows(rows))
    by_hash = {config_hash(c): c for c in conditions}
    labels = {config_hash(c): f"C{i + 1}" for i, c in enumerate(conditions)}
    return by_hash, labels


def load_completions(
    config_hashes: set[str], bundle_ids: set[str], log_path: Path = LOG_PATH
) -> Completions:
    """Node completions for the given (real) condition hashes and eval bundles, at repetition 0.

    Filtering by the real condition hashes excludes dev, test and aborted-run noise, because a
    condition hash bakes in the model and every provenance field (so a different model or template
    has a different hash). Only `parse_outcome == "ok"` lines are kept — an over-ceiling node-3 call
    produced no verdict and no audit record in the live run. Last line wins, so a resumed item keeps
    the completion that produced its result row."""
    out: Completions = {}
    with log_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            rec = json.loads(line)
            if int(rec.get("repetition", -1)) != 0 or rec.get("parse_outcome") != "ok":
                continue
            ch, bid, node = str(rec.get("config_hash")), str(rec.get("bundle_id")), str(rec["node"])
            if ch in config_hashes and bid in bundle_ids and node in NODES:
                out[(ch, bid, node)] = str(rec.get("completion", ""))
    return out


def _verdict_from_row(row: dict[str, object]) -> Verdict | None:
    """The emitted `Verdict` for a result row, or None if the verdict was withheld."""
    if not bool(row.get("emitted")) or row.get("incident_type") is None:
        return None
    evidence = cast("list[object]", row.get("evidence") or [])
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
            "evidence": list(evidence),
        }
    )


def _parse_findings(completion: str | None) -> Findings | None:
    """Node 1's completion parsed into `Findings`, the same way the live graph does, or None."""
    if completion is None:
        return None
    try:
        return Findings.model_validate_json(json_payload(completion))
    except ValidationError:
        return None


def _write_withheld_stub(bundle: Bundle, out_dir: Path) -> None:
    """A short report for an incident with no emitted verdict, so the Report panel resolves."""
    body = (
        f"# Incident {bundle.bundle_id}\n\n"
        "No verdict was emitted for this incident: the recommendation was withheld by the safety "
        "validator, or no classification was produced.\n\n"
        "This is a recommendation-only console. A human decides; nothing is executed.\n"
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / report_filename(bundle.bundle_id)).write_text(body, encoding="utf-8")


def render_reports(
    c1_hash: str,
    rows: list[dict[str, object]],
    completions: Completions,
    bundles_by_id: dict[str, Bundle],
    *,
    out_dir: Path = REPORTS_DIR,
) -> tuple[int, int]:
    """Write one report per full-agent (C1) bundle; stub the withheld ones. Returns (full, stub)."""
    full = stub = 0
    for row in rows:
        if str(row["config_hash"]) != c1_hash:
            continue
        bid = str(row["bundle_id"])
        bundle = bundles_by_id.get(bid)
        if bundle is None:
            continue
        verdict = _verdict_from_row(row)
        findings = _parse_findings(completions.get((c1_hash, bid, "evidence")))
        if verdict is not None and findings is not None:
            render_report(verdict, findings, bundle, out_dir=out_dir)
            full += 1
        else:
            _write_withheld_stub(bundle, out_dir)
            stub += 1
    return full, stub


def replay_audit(
    by_hash: dict[str, ExperimentConfig],
    labels: dict[str, str],
    completions: Completions,
    bundles_by_id: dict[str, Bundle],
) -> list[AuditRecord]:
    """Reconstruct the audit record each agentic item produced, by assembling the node-2/node-3
    verdict and running the real safety stage over it — exactly as the live graph did."""
    records: list[AuditRecord] = []
    agentic = sorted(
        ((h, c) for h, c in by_hash.items() if c.strategy is Strategy.AGENTIC),
        key=lambda hc: labels[hc[0]],
    )
    for ch, config in agentic:
        mode = SafetyMode.load(config.safety)
        for bid, bundle in sorted(bundles_by_id.items()):
            cls_c = completions.get((ch, bid, "classification"))
            rec_c = completions.get((ch, bid, "recommendation"))
            if cls_c is None or rec_c is None:
                continue  # no node-2/3 call logged → the item produced no audit record
            try:
                classification = Classification.model_validate_json(json_payload(cls_c))
                recommendation = Recommendation.model_validate_json(json_payload(rec_c))
            except ValidationError:
                # A parse failure raised before apply_safety in the live run, so no record exists.
                continue
            completion = _verdict_completion(classification, recommendation)
            result = apply_safety(
                completion, bundle, mode=mode, bundle_id=bid, config_hash=ch, repetition=0
            )
            records.append(result.audit)
    return records


def main() -> int:  # pragma: no cover - reads the frozen full-run artifacts and the 124 MB call log
    rows = load_result_rows()
    by_hash, labels = conditions_by_hash(rows)
    c1_hash = next(h for h, label in labels.items() if label == "C1")

    from thesis.assemble.build_frozen import build

    bundles_by_id = {b.bundle_id: b for b in build().eval_bundles}
    completions = load_completions(set(by_hash), set(bundles_by_id))

    full, stub = render_reports(c1_hash, rows, completions, bundles_by_id)

    AUDIT_PATH.unlink(missing_ok=True)  # regenerate the derived view fresh (not a live append)
    records = replay_audit(by_hash, labels, completions, bundles_by_id)
    write_audit(records)

    print(f"reports: {full} rendered, {stub} withheld-stub (reports/)")
    print(f"audit: {len(records)} records -> {AUDIT_PATH}")
    print(f"  outcomes: {dict(Counter(r.validator_outcome for r in records))}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "conditions_by_hash",
    "load_completions",
    "load_result_rows",
    "render_reports",
    "replay_audit",
]
