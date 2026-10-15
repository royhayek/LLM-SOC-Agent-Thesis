"""The condition-matrix runner (E9-01, SCRUM-41).

Runs every (bundle, condition, repetition) of the frozen matrix (record §6.1) over the evaluation
bundles, with bounded concurrency and resume. It is the measurement rig the thesis rests on (§1).

The matrix is the 7 conditions of `config/conditions.yaml` at k = 3 repetitions: 5 agentic (3 LLM
calls each), 1 prompt-only (1 call), 1 ml_classifier (0 calls) = 16 calls per bundle+repetition
(METHODS.md §2). Every condition runs on the same bundles (paired design). A `Ledger` keyed by
(bundle, config hash, repetition) makes the run resumable without repeating finished work; a
dry-run counts the calls and estimates the cost before anything is spent.

    python -m thesis.eval.run --dry-run     # print the call count and estimated cost

Metric computation (E9-03..E9-07) and result persistence (E9-02) are separate; the runner hands
each finished result to a `sink` callback and records the item in the ledger.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

import yaml  # type: ignore[import-untyped]

from thesis.agent.graph import run_graph
from thesis.agent.node_evidence import Completer
from thesis.assemble.bundles import Bundle
from thesis.baselines.baseline_a import baseline_a_verdict
from thesis.baselines.baseline_b import baseline_b_verdict
from thesis.config import ExperimentConfig, Provenance, Safety, Strategy, config_hash
from thesis.eval.ledger import Ledger, LedgerKey
from thesis.reduce.policy import reduce
from thesis.schema.alert import Source

REPO_ROOT = Path(__file__).resolve().parents[2]
CONDITIONS_PATH = REPO_ROOT / "config" / "conditions.yaml"
EVAL_BUNDLES = REPO_ROOT / "data" / "bundles" / "v1.0.0" / "eval.parquet"

K = 3  # repetitions (METHODS.md §2, C-03)
CONCURRENCY = (
    8  # ADR-001 A5 (UNVERIFIED rate limit); bounded so a 429 storm can't look like failure
)
CALLS = {Strategy.AGENTIC: 3, Strategy.PROMPT_ONLY: 1, Strategy.ML_CLASSIFIER: 0}

# DeepInfra prices (USD per 1M tokens, ADR-001). Dry-run token averages are estimates, overridable.
USD_PER_1M_IN = 0.02
USD_PER_1M_OUT = 0.04
AVG_IN_TOKENS = 1400  # ~ the measured worst-case reduced prompt (E8-03); conservative average
AVG_OUT_TOKENS = 200


@dataclass(frozen=True)
class RunItem:
    bundle: Bundle
    config: ExperimentConfig
    repetition: int

    def key(self) -> LedgerKey:
        return LedgerKey(self.bundle.bundle_id, config_hash(self.config), self.repetition)


@dataclass(frozen=True)
class RunResult:
    bundle_id: str
    config_hash: str
    repetition: int
    strategy: str
    payload: object  # GraphTrace | Verdict | None — persisted by E9-02


def load_conditions(provenance: Provenance, path: Path = CONDITIONS_PATH) -> list[ExperimentConfig]:
    """Load the 7 frozen conditions; provenance goes on the LLM strategies, not Baseline A."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    configs = []
    for cond in data["conditions"]:
        strategy = Strategy(cond["strategy"])
        configs.append(
            ExperimentConfig(
                sources=frozenset(Source(s) for s in cond["sources"]),
                strategy=strategy,
                safety=Safety(cond["safety"]),
                provenance=None if strategy is Strategy.ML_CLASSIFIER else provenance,
            )
        )
    return configs


def calls_per_bundle_rep(conditions: Iterable[ExperimentConfig]) -> int:
    return sum(CALLS[c.strategy] for c in conditions)


def dry_run(
    n_bundles: int,
    conditions: list[ExperimentConfig],
    k: int = K,
    *,
    avg_in: int = AVG_IN_TOKENS,
    avg_out: int = AVG_OUT_TOKENS,
) -> dict[str, float]:
    """Return the total LLM-call count and the estimated USD cost, without running anything."""
    per = calls_per_bundle_rep(conditions)
    n_calls = n_bundles * per * k
    usd = n_calls * (avg_in * USD_PER_1M_IN + avg_out * USD_PER_1M_OUT) / 1_000_000
    return {"calls": float(n_calls), "usd": round(usd, 4), "calls_per_bundle_rep": float(per)}


def run_one(
    bundle: Bundle, config: ExperimentConfig, *, client: Completer, repetition: int
) -> RunResult:
    """Dispatch one item to its strategy. Agentic = 3 calls, prompt-only = 1, ml_classifier = 0."""
    ch = config_hash(config)
    if config.strategy is Strategy.AGENTIC:
        payload: object = run_graph(bundle, config, client=client, repetition=repetition)
    elif config.strategy is Strategy.PROMPT_ONLY:
        view = reduce(bundle, sources=config.sources)
        payload = baseline_b_verdict(
            view, client=client, bundle_id=bundle.bundle_id, config_hash=ch, repetition=repetition
        )
    else:  # ml_classifier: deterministic, no LLM call
        payload = baseline_a_verdict(reduce(bundle, sources=config.sources))
    return RunResult(bundle.bundle_id, ch, repetition, config.strategy.value, payload)


def _items(bundles: list[Bundle], conditions: list[ExperimentConfig], k: int) -> Iterator[RunItem]:
    for bundle in bundles:
        for config in conditions:
            for repetition in range(k):
                yield RunItem(bundle, config, repetition)


def run_matrix(
    bundles: list[Bundle],
    conditions: list[ExperimentConfig],
    *,
    client: Completer,
    ledger: Ledger,
    sink: Callable[[RunResult], None],
    k: int = K,
    max_workers: int = CONCURRENCY,
    run_one_fn: Callable[..., RunResult] = run_one,
) -> int:
    """Run every not-yet-finished item concurrently; `sink` then ledger-`mark` each result. Returns
    the number of items run this call. Finished items (in the ledger) are skipped, so a restart
    after an interruption never re-runs completed work."""
    todo = [it for it in _items(bundles, conditions, k) if not ledger.is_done(it.key())]
    executor = ThreadPoolExecutor(max_workers=max_workers)
    try:
        futures = {
            executor.submit(
                run_one_fn, it.bundle, it.config, client=client, repetition=it.repetition
            ): it
            for it in todo
        }
        # Mark each item only once its result is safely handed to the sink, so an interruption
        # leaves finished items recorded and everything else simply un-run (re-run on resume).
        for future in as_completed(futures):
            it = futures[future]
            sink(future.result())  # raises here if run_one_fn raised; pending items are cancelled
            ledger.mark(it.key())
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
    return len(todo)


def _placeholder_provenance() -> Provenance:
    return Provenance(
        model="dry-run",
        model_revision="dry-run",
        provider="dry-run",
        temperature=0.6,
        top_p=0.9,
        max_tokens=250,
        seed=None,
        prompt_template_version="prompts-v1.0",
        graph_version="graph-v1.0",
    )


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if "--dry-run" not in args:
        print("usage: python -m thesis.eval.run --dry-run", file=sys.stderr)
        return 2
    conditions = load_conditions(_placeholder_provenance())
    import pyarrow.parquet as pq  # type: ignore[import-untyped]

    n_bundles = pq.read_table(EVAL_BUNDLES, columns=["bundle_id"]).num_rows
    est = dry_run(n_bundles, conditions)
    print(
        f"eval bundles: {n_bundles}; conditions: {len(conditions)}; k={K}; "
        f"calls/bundle/rep: {int(est['calls_per_bundle_rep'])}; total calls: {int(est['calls'])}; "
        f"estimated cost: USD {est['usd']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
