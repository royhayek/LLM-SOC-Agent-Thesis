"""Result rows with full provenance (E9-02, SCRUM-53).

Every (bundle, condition, repetition) produces one row carrying the verdict, the ground truth, the
cost data and the full provenance (record §6.1, §4.2) — this is what makes every number in the
thesis traceable to an exact model, prompt and bundle. Metric computation and plots are later
tickets; this only defines and writes the rows.

Token and latency totals are the sum over **all** the item's LLM calls (3 for agentic, 1 for
prompt-only, 0 for Baseline A), including a rejected attempt's calls, consistent with E0-11 (every
result row's cost is those calls, rejected or not).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

import pyarrow as pa  # type: ignore[import-untyped]
import pyarrow.parquet as pq  # type: ignore[import-untyped]

from thesis.agent.graph import GraphTrace
from thesis.assemble.bundles import Bundle
from thesis.config import ExperimentConfig, Provenance, config_hash
from thesis.eval.run import RunResult
from thesis.schema.verdict import Verdict

# Provenance stand-in for Baseline A, which makes no LLM call; keeps every row's columns non-null.
_BASELINE_A_PROV = {
    "model": "flow_classifier",
    "model_revision": "baseline-a-v1.0",
    "provider": "local",
    "temperature": 0.0,
    "top_p": 1.0,
    "max_tokens": 0,
    "seed": None,
    "prompt_template_version": "n/a",
    "graph_version": "n/a",
}


@dataclass(frozen=True)
class ResultRow:
    # condition + provenance (§4.2)
    config_hash: str
    strategy: str
    safety: str
    sources: list[str]
    model: str
    model_revision: str
    provider: str
    temperature: float
    top_p: float
    max_tokens: int
    seed: int | None
    prompt_template_version: str
    graph_version: str
    # item + ground truth
    bundle_id: str
    episode_id: str  # "" for benign bundles (no episode), never null
    repetition: int
    ground_truth: str
    # emitted verdict (predicted fields null when withheld or unparsed)
    emitted: bool
    validator_outcome: str
    incident_type: str | None
    severity: str | None
    affected_device: str | None
    recommended_action: str | None
    confidence: float | None
    evidence: list[str]
    # cost (§4.4)
    tokens_in: int
    tokens_out: int
    latency_ms: float


def _predicted(emitted: Verdict | str | None) -> dict[str, object]:
    verdict: Verdict | None = emitted if isinstance(emitted, Verdict) else None
    if isinstance(emitted, str):
        try:
            verdict = Verdict.model_validate_json(emitted)
        except ValueError:
            verdict = None
    if verdict is None:
        return {
            "incident_type": None,
            "severity": None,
            "affected_device": None,
            "recommended_action": None,
            "confidence": None,
            "evidence": [],
        }
    return {
        "incident_type": verdict.classification.incident_type.value,
        "severity": verdict.recommendation.severity.value,
        "affected_device": verdict.affected_device,
        "recommended_action": verdict.recommendation.recommended_action.value,
        "confidence": verdict.classification.confidence,
        "evidence": list(verdict.evidence),
    }


def _emitted_and_outcome(result: RunResult) -> tuple[Verdict | str | None, str]:
    if isinstance(result.payload, GraphTrace):
        return result.payload.emitted, result.payload.validator_outcome
    if isinstance(result.payload, Verdict):  # baselines returned a parsed verdict
        return result.payload, "not_applied"
    return None, "not_applied"  # prompt_only parse failure (None)


def build_row(
    result: RunResult,
    bundle: Bundle,
    config: ExperimentConfig,
    *,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
) -> ResultRow:
    """Build one result row from a run result, its bundle and its config."""
    prov = (
        _BASELINE_A_PROV
        if config.provenance is None
        else {k: v for k, v in config.provenance.model_dump().items()}
    )
    emitted, outcome = _emitted_and_outcome(result)
    predicted = _predicted(emitted)
    return ResultRow(
        config_hash=config_hash(config),
        strategy=config.strategy.value,
        safety=config.safety.value,
        sources=sorted(s.value for s in config.sources),
        bundle_id=bundle.bundle_id,
        episode_id=bundle.episode_id or "",
        repetition=result.repetition,
        ground_truth=bundle.label,
        emitted=emitted is not None,
        validator_outcome=outcome,
        tokens_in=tokens_in,
        tokens_out=tokens_out,
        latency_ms=latency_ms,
        **prov,
        **predicted,  # type: ignore[arg-type]
    )


def call_totals(records: list[dict[str, object]]) -> tuple[int, int, float]:
    """Sum tokens and latency over an item's call-log records (E0-10), rejected calls included."""
    t_in = sum(cast("int", r["tokens_in"]) for r in records)
    t_out = sum(cast("int", r["tokens_out"]) for r in records)
    latency = sum(cast("float", r["latency_ms"]) for r in records)
    return t_in, t_out, latency


def write_results(rows: list[ResultRow], path: Path) -> int:
    """Write result rows to Parquet; returns the row count."""
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.Table.from_pylist([asdict(r) for r in rows])
    pq.write_table(table, path)
    return len(rows)


def read_results(path: Path) -> list[dict[str, object]]:
    return pq.read_table(path).to_pylist()  # type: ignore[no-any-return]


def provenance_from_rows(rows: list[dict[str, object]]) -> Provenance:
    """Rebuild the run's Provenance from an LLM-bearing result row, so that `config_hash` recomputed
    in analysis matches the hashes stored in the rows (config_hash includes provenance). Baseline A
    (ml_classifier) carries a stand-in provenance, so it is skipped."""
    row = next(r for r in rows if str(r["strategy"]) != "ml_classifier")
    seed = row["seed"]
    return Provenance(
        model=str(row["model"]),
        model_revision=str(row["model_revision"]),
        provider=str(row["provider"]),
        temperature=float(cast("float", row["temperature"])),
        top_p=float(cast("float", row["top_p"])),
        max_tokens=int(cast("int", row["max_tokens"])),
        seed=None if seed is None else int(cast("int", seed)),
        prompt_template_version=str(row["prompt_template_version"]),
        graph_version=str(row["graph_version"]),
    )


__all__ = [
    "ResultRow",
    "build_row",
    "call_totals",
    "provenance_from_rows",
    "read_results",
    "write_results",
]
