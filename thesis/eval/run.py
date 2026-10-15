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

import structlog
import yaml  # type: ignore[import-untyped]

from thesis.agent.graph import run_graph
from thesis.agent.node_classify import ClassifyParseError
from thesis.agent.node_evidence import Completer, EvidenceParseError
from thesis.agent.node_recommend import RecommendParseError
from thesis.assemble.bundles import Bundle
from thesis.baselines.baseline_a import baseline_a_verdict
from thesis.baselines.baseline_b import baseline_b_verdict
from thesis.config import ExperimentConfig, Provenance, Safety, Strategy, config_hash
from thesis.eval.ledger import Ledger, LedgerKey
from thesis.llm.client import LLMError
from thesis.prompts.render import TEMPLATE_VERSION
from thesis.reduce.check_tokens import OUTPUT_CEILING, TokenCeilingError
from thesis.reduce.policy import reduce
from thesis.schema.alert import Source

_log = structlog.get_logger("thesis.eval.run")

# A per-item failure the runner absorbs: a call that failed after the client's own retries, an
# output over the ceiling, or a node output that did not conform to its schema (common under
# json_object, where decoding no longer enforces structure — ADR-0012). The item is recorded as an
# unusable verdict (scored wrong, like any withheld or unparsed output, §3.1), never repaired and
# never allowed to abort the whole matrix. Other exceptions still propagate as real bugs.
_ITEM_FAILURE = (
    LLMError,
    TokenCeilingError,
    EvidenceParseError,
    ClassifyParseError,
    RecommendParseError,
)

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
    failure: str | None = None  # category of an absorbed per-item failure, else None (diagnostic)


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


_FAILURE_CATEGORY: tuple[tuple[type[Exception], str], ...] = (
    (TokenCeilingError, "ceiling"),
    (EvidenceParseError, "node1_parse"),
    (ClassifyParseError, "node2_parse"),
    (RecommendParseError, "node3_parse"),
    (LLMError, "call_error"),
)


def _failure_category(error: Exception) -> str:
    for exc_type, name in _FAILURE_CATEGORY:
        if isinstance(error, exc_type):
            return name
    return "other"


def _failed_result(item: RunItem, error: Exception) -> RunResult:
    """A result for an item whose run failed at the client (after retries), exceeded the output
    ceiling, or produced a node output that did not conform. `payload=None` makes it an unusable
    verdict downstream: scored wrong, never dropped. `failure` records the category (diagnostic)."""
    return RunResult(
        item.bundle.bundle_id,
        config_hash(item.config),
        item.repetition,
        item.config.strategy.value,
        None,
        failure=_failure_category(error),
    )


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
        # leaves finished items recorded and everything else simply un-run (re-run on resume). A
        # per-item call failure or over-ceiling output becomes an unusable result for that item
        # (§3.1), so one bad bundle cannot abort the whole run; other errors still propagate.
        for future in as_completed(futures):
            it = futures[future]
            try:
                result = future.result()
            except _ITEM_FAILURE as error:
                _log.warning(
                    "item_failed",
                    bundle_id=it.bundle.bundle_id,
                    config_hash=config_hash(it.config),
                    repetition=it.repetition,
                    error=str(error),
                )
                result = _failed_result(it, error)
            sink(result)
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
        max_tokens=OUTPUT_CEILING,
        seed=None,
        prompt_template_version=TEMPLATE_VERSION,
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
