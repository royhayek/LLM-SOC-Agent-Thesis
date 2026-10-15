"""The exploratory partial run (E9-08, SCRUM-107).

The budget allows one small run before the full matrix, to catch bugs and confirm the cost while a
mistake is still cheap (record §4.4.1). It runs a seeded ~10 % slice of the evaluation set through
**every** condition at k = 1 and through the whole metric pipeline, measures the euros actually
spent, and projects the cost of the full runs. **Its accuracy numbers are discarded and never
reported** (scope): only the cost and the "everything ran" result leave this run. Seeing an accuracy
number here and tuning a prompt to it would be a locked-parameter change (the gotcha).

    LLM_BASE_URL=... LLM_MODEL=... python -m thesis.eval.exploratory

Run it under `caffeinate -is` so the machine cannot sleep mid-run, and confirm the spending cap is
set on the provider first (ADR-0001). With no `LLM_BASE_URL` the command prints the runbook and
exits, spending nothing.
"""

from __future__ import annotations

import os
import random
import sys
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from thesis.config import Provenance
    from thesis.llm.client import LLMClient

from thesis.assemble.bundles import Bundle, bundle_set_hash
from thesis.config import ExperimentConfig, config_hash
from thesis.eval.bootstrap import block_bootstrap_ci, blocks_from_episodes
from thesis.eval.cost import USD_PER_EUR, cost_per_incident
from thesis.eval.metrics import (
    BENIGN,
    compute_classification,
    compute_detection,
    compute_reliability,
    compute_safety,
)
from thesis.eval.run import USD_PER_1M_IN, USD_PER_1M_OUT, K
from thesis.eval.stats import run_tests

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORT_PATH = REPO_ROOT / "docs" / "eval" / "exploratory_run.md"

SLICE_SEED = 20260931  # ASSUMPTION (E9-08): the slice is drawn by this fixed seed; never reported
SLICE_FRACTION = 0.10  # about 10 % of the evaluation bundles (scope)
FULL_RUNS = 3  # planned full runs (ADR-0001 cost table)
CAP_USD = 20.0  # spending cap (ADR-0001); the projection must sit under it


def draw_slice(
    bundles: Sequence[Bundle], *, fraction: float = SLICE_FRACTION, seed: int = SLICE_SEED
) -> list[Bundle]:
    """A seeded ~`fraction` slice of the bundles, stratified by label so every family (and benign)
    is present — otherwise a per-label metric could crash on an empty class. At least one bundle per
    present label. Deterministic for a fixed seed; the ids are sorted before sampling so the draw
    does not depend on input order."""
    by_label: dict[str, list[Bundle]] = defaultdict(list)
    for bundle in bundles:
        by_label[bundle.label].append(bundle)
    rng = random.Random(seed)
    chosen: list[Bundle] = []
    for label in sorted(by_label):
        group = sorted(by_label[label], key=lambda b: b.bundle_id)
        take = max(1, round(len(group) * fraction))
        chosen.extend(rng.sample(group, min(take, len(group))))
    return sorted(chosen, key=lambda b: b.bundle_id)


@dataclass(frozen=True)
class ExploratoryCost:
    measured_usd: float
    measured_eur: float
    per_full_run_usd: float
    per_full_run_eur: float
    projected_total_usd: float  # this exploratory run + FULL_RUNS full runs (ADR-0001)
    projected_total_eur: float
    within_cap: bool
    n_slice: int
    n_eval: int


def _row_usd(tokens_in: int, tokens_out: int) -> float:
    return (tokens_in * USD_PER_1M_IN + tokens_out * USD_PER_1M_OUT) / 1_000_000


def project_cost(
    rows: Sequence[Mapping[str, object]],
    n_eval: int,
    *,
    full_runs: int = FULL_RUNS,
    cap_usd: float = CAP_USD,
) -> ExploratoryCost:
    """Scale the measured slice cost (k = 1, `n_slice` bundles) to the full runs (`n_eval` bundles,
    k = K). The slice carries the same condition mix as a full run, so one full run costs the
    measured amount times `n_eval / n_slice` times `K`; the projected total is `full_runs` of those
    plus this exploratory run itself (ADR-0001 includes it)."""
    measured_usd = sum(
        (_row_usd(cast("int", r["tokens_in"]), cast("int", r["tokens_out"])) for r in rows),
        0.0,
    )
    n_slice = len({str(r["bundle_id"]) for r in rows})
    scale = (n_eval / n_slice) * K if n_slice else 0.0
    per_full_run_usd = measured_usd * scale
    projected_total_usd = per_full_run_usd * full_runs + measured_usd
    return ExploratoryCost(
        measured_usd=round(measured_usd, 4),
        measured_eur=round(measured_usd / USD_PER_EUR, 4),
        per_full_run_usd=round(per_full_run_usd, 4),
        per_full_run_eur=round(per_full_run_usd / USD_PER_EUR, 4),
        projected_total_usd=round(projected_total_usd, 4),
        projected_total_eur=round(projected_total_usd / USD_PER_EUR, 4),
        within_cap=projected_total_usd < cap_usd,
        n_slice=n_slice,
        n_eval=n_eval,
    )


def run_all_metrics(
    rows: Sequence[Mapping[str, object]], conditions: Sequence[ExperimentConfig]
) -> list[str]:
    """Run every metric function on the slice rows, to prove the pipeline runs end to end (AC1).
    Returns the names that produced output; raises with context on the first that errors. The
    computed values are intentionally discarded — this run never reports accuracy (scope)."""
    conditions = list(conditions)
    steps: list[tuple[str, object]] = [
        ("detection", lambda: compute_detection(rows)),
        ("classification", lambda: compute_classification(rows)),
        ("safety", lambda: compute_safety(rows)),
        ("reliability", lambda: compute_reliability(rows)),
        ("cost_per_incident", lambda: cost_per_incident(rows)),
        ("hypothesis_tests", lambda: run_tests(rows, conditions)),
        ("block_bootstrap", lambda: _smoke_bootstrap(rows, conditions)),
    ]
    ran: list[str] = []
    for name, fn in steps:
        try:
            fn()  # type: ignore[operator]
        except Exception as error:  # noqa: BLE001 - surface which metric broke, with context
            raise RuntimeError(
                f"metric {name!r} failed on the exploratory slice: {error}"
            ) from error
        ran.append(name)
    return ran


def _smoke_bootstrap(
    rows: Sequence[Mapping[str, object]], conditions: Sequence[ExperimentConfig]
) -> None:
    """Exercise the episode bootstrap on one contrast's per-bundle emitted-rate difference."""
    if len(conditions) < 2:
        return
    a, b = config_hash(conditions[0]), config_hash(conditions[1])
    emitted: dict[str, dict[str, list[float]]] = {a: defaultdict(list), b: defaultdict(list)}
    episode_of: dict[str, str] = {}
    for row in rows:
        ch = str(row["config_hash"])
        if ch in emitted:
            bundle = str(row["bundle_id"])
            emitted[ch][bundle].append(1.0 if bool(row["emitted"]) else 0.0)
            truth = str(row["ground_truth"])
            episode_of[bundle] = "" if truth == BENIGN else str(row["episode_id"])
    shared = sorted(set(emitted[a]) & set(emitted[b]))

    def _mean(values: list[float]) -> float:
        return sum(values) / len(values)

    diffs = [_mean(emitted[a][x]) - _mean(emitted[b][x]) for x in shared]
    blocks = blocks_from_episodes([episode_of[x] for x in shared], diffs)
    block_bootstrap_ci(blocks, seed=SLICE_SEED)


def write_report(
    cost: ExploratoryCost,
    metrics_ran: Sequence[str],
    *,
    eval_hash: str,
    path: Path = REPORT_PATH,
) -> None:
    """Write `docs/eval/exploratory_run.md`: the measured and projected cost, the metrics that ran,
    and the human sections (bugs, parameter-change confirmation) for Roy to complete."""
    path.parent.mkdir(parents=True, exist_ok=True)
    verdict = "WITHIN CAP" if cost.within_cap else "OVER CAP — STOP"
    body = [
        "# Exploratory partial run (E9-08, SCRUM-107)",
        "",
        "GENERATED by `python -m thesis.eval.exploratory`. The accuracy metrics of this run are "
        "**discarded and not reported** (scope): only the cost and the end-to-end result are kept.",
        "",
        f"- Slice: **{cost.n_slice}** of {cost.n_eval} evaluation bundles "
        f"(~{SLICE_FRACTION:.0%}, seed {SLICE_SEED}), every condition, k = 1.",
        f"- Evaluation set hash (recomputed this run): `{eval_hash}` "
        "— compare to the frozen value.",
        "",
        "## Cost",
        "",
        "| Quantity | USD | EUR |",
        "|---|---|---|",
        f"| Measured (this exploratory slice) | {cost.measured_usd} | {cost.measured_eur} |",
        f"| Projected per full run (N_eval, k={K}) | "
        f"{cost.per_full_run_usd} | {cost.per_full_run_eur} |",
        f"| Projected total ({FULL_RUNS} full runs + exploratory) | "
        f"{cost.projected_total_usd} | {cost.projected_total_eur} |",
        "",
        f"Spending cap (ADR-0001): USD {CAP_USD:.2f}. Projection verdict: **{verdict}**.",
        "",
        "Projection method: the slice has the same condition mix as a full run, so one full run "
        f"is the measured cost x (N_eval / slice) x k={K}; prices are the dated ADR-0001 figures.",
        "",
        "## Pipeline",
        "",
        "Every metric function produced output with no error on the slice:",
        "",
        *(f"- {name}" for name in metrics_ran),
        "",
        "## Bugs found and fixed",
        "",
        "_To complete: list any bug this run surfaced and its fix, or state 'none'._",
        "",
        "## Parameter-change confirmation",
        "",
        "_To confirm: no prompt or locked parameter changed because of this run. If one did, it "
        "is a locked-parameter change — link the METHODS.md changelog entry and re-run the "
        "affected conditions (scope)._",
        "",
    ]
    path.write_text("\n".join(body) + "\n", encoding="utf-8")


def _runbook() -> str:
    return (
        "Exploratory run not started: LLM_BASE_URL is not set.\n"
        "To run it (spends money on the provider):\n"
        "  1. Confirm the USD 20 spending cap is set on the provider (ADR-0001).\n"
        "  2. Set LLM_BASE_URL and LLM_MODEL for the hosted model (.env).\n"
        "  3. caffeinate -is uv run python -m thesis.eval.exploratory\n"
        "The run draws the seeded slice, runs every condition at k=1, runs all metrics,\n"
        f"and writes {REPORT_PATH} with the cost; it stops if the projection is over cap."
    )


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - the live run is Roy's
    _argv = sys.argv[1:] if argv is None else argv
    if not os.environ.get("LLM_BASE_URL"):
        print(_runbook(), file=sys.stderr)
        return 2

    # Imported lazily: these pull in the model client and the full assembly pipeline, which the
    # runbook path (and the unit tests of the pure functions above) must not require.
    from thesis.assemble.build_frozen import build
    from thesis.eval.ledger import Ledger
    from thesis.eval.results import ResultRow, build_row
    from thesis.eval.run import RunResult, load_conditions, run_matrix
    from thesis.llm.client import LLMClient
    from thesis.obs.logging import LOG_PATH

    client = LLMClient.from_env()
    conditions = load_conditions(_provenance(client))
    eval_bundles = build().eval_bundles
    eval_hash = bundle_set_hash(eval_bundles)
    slice_bundles = draw_slice(eval_bundles)
    bundles_by_id = {b.bundle_id: b for b in slice_bundles}
    configs_by_hash = {config_hash(c): c for c in conditions}

    # The exploratory run is a fresh pass (its numbers are discarded), so start from an empty
    # ledger — a stale one from an earlier/aborted run would skip items. And snapshot the call log's
    # length now, so cost counts only THIS run's calls, never an earlier run's for the same bundles.
    ledger_path = REPO_ROOT / "data" / "exploratory" / "ledger.jsonl"
    ledger_path.unlink(missing_ok=True)
    log_start = _line_count(LOG_PATH)

    results: list[RunResult] = []
    ledger = Ledger(ledger_path)
    run_matrix(slice_bundles, conditions, client=client, ledger=ledger, sink=results.append, k=1)

    totals = _call_totals_by_item(
        LOG_PATH, set(configs_by_hash), set(bundles_by_id), since_line=log_start
    )
    rows: list[ResultRow] = []
    for result in results:
        item = (result.bundle_id, result.config_hash, result.repetition)
        t_in, t_out, latency = totals.get(item, (0, 0, 0.0))
        rows.append(
            build_row(
                result,
                bundles_by_id[result.bundle_id],
                configs_by_hash[result.config_hash],
                tokens_in=t_in,
                tokens_out=t_out,
                latency_ms=latency,
            )
        )

    row_dicts = [dict(vars(r)) for r in rows]
    metrics_ran = run_all_metrics(row_dicts, conditions)
    cost = project_cost(row_dicts, len(eval_bundles))
    write_report(cost, metrics_ran, eval_hash=eval_hash)
    print(f"exploratory run complete: {cost.n_slice} bundles; {_verdict(cost)}")
    print(f"wrote {REPORT_PATH}")
    return 0 if cost.within_cap else 1


def _provenance(client: LLMClient) -> Provenance:  # pragma: no cover - built for Roy's live run
    """Build the run Provenance from the client's pinned fields and the frozen version constants."""
    from thesis.config import Provenance
    from thesis.llm.client import _is_local
    from thesis.prompts.render import TEMPLATE_VERSION

    provider = os.environ.get(
        "LLM_PROVIDER", "local-ollama" if _is_local(client.base_url) else "deepinfra"
    )
    return Provenance(
        model=client.model,
        model_revision=client.model_revision,
        provider=provider,
        temperature=client.temperature,
        top_p=client.top_p,
        max_tokens=client.max_tokens,
        seed=None,  # ADR-0001: the provider does not honour a seed for this model
        prompt_template_version=TEMPLATE_VERSION,
        graph_version="graph-v1.0",
    )


def _verdict(cost: ExploratoryCost) -> str:
    return (
        f"projected USD {cost.projected_total_usd} "
        f"({'within' if cost.within_cap else 'OVER'} the USD {CAP_USD:.2f} cap)"
    )


def _line_count(path: Path) -> int:
    """The number of lines currently in the call log, used to ignore earlier runs' calls."""
    if not path.exists():
        return 0
    return sum(1 for _ in path.open(encoding="utf-8"))


def _call_totals_by_item(
    log_path: Path, config_hashes: set[str], bundle_ids: set[str], *, since_line: int = 0
) -> dict[tuple[str, str, int], tuple[int, int, float]]:
    """Group the call log's records by (bundle, config, repetition) and sum each item's cost.

    Only lines from index `since_line` onward are read, so a previous or aborted run's calls for the
    same bundles — and unit-test lines — are never double-counted into this run's cost."""
    import json

    from thesis.eval.results import call_totals

    grouped: dict[tuple[str, str, int], list[dict[str, object]]] = defaultdict(list)
    if not log_path.exists():
        return {}
    for line in log_path.read_text(encoding="utf-8").splitlines()[since_line:]:
        if not line.strip():
            continue
        rec = json.loads(line)
        if rec.get("config_hash") in config_hashes and rec.get("bundle_id") in bundle_ids:
            key = (str(rec["bundle_id"]), str(rec["config_hash"]), int(rec["repetition"]))
            grouped[key].append(rec)
    return {key: call_totals(records) for key, records in grouped.items()}


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = [
    "ExploratoryCost",
    "draw_slice",
    "project_cost",
    "run_all_metrics",
    "write_report",
]
