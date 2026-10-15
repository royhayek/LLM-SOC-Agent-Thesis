"""Cost and latency per incident analysed (E9-07, SCRUM-101).

Cost per analysed bundle is a publishable result that the comparable LLM-SOC works do not report
(record §4.4). It is read straight from the result rows (E9-02): each row already sums tokens and
latency over **all** the item's LLM calls, rejected attempts included (results.py), so the safety
layer is never made to look free (the gotcha). One row is one analysed bundle at one repetition.

Prices are the dated ADR-0001 figures (DeepInfra standard tier, checked 2026-10-04): USD 0.02 per
million input tokens and USD 0.04 per million output tokens, converted to euros at the ECB reference
rate of 2026-10-02 (1 EUR = 1.1225 USD). The date travels with the number: it is written into the
CSV header so a reader always knows which price produced the euros. This module optimises nothing
and compares no providers (scope out).
"""

from __future__ import annotations

import csv
import statistics
import sys
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import cast

from thesis.eval.run import USD_PER_1M_IN, USD_PER_1M_OUT

# ADR-0001: DeepInfra pricing checked 2026-10-04; euros via the ECB reference rate of 2026-10-02.
PRICE_DATE = "2026-10-04"
EUR_RATE_DATE = "2026-10-02"
USD_PER_EUR = 1.1225  # 1 EUR = 1.1225 USD (ECB, 2026-10-02)

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RESULTS = REPO_ROOT / "results" / "results.parquet"
OUTPUT = REPO_ROOT / "results" / "cost_per_incident.csv"

FIELDS = [
    "config_hash",
    "n",
    "mean_tokens_in",
    "median_tokens_in",
    "mean_tokens_out",
    "median_tokens_out",
    "mean_eur",
    "median_eur",
    "mean_seconds",
    "median_seconds",
]


def row_eur(tokens_in: int, tokens_out: int) -> float:
    """The euro cost of one bundle's calls at the dated ADR-0001 prices."""
    usd = (tokens_in * USD_PER_1M_IN + tokens_out * USD_PER_1M_OUT) / 1_000_000
    return usd / USD_PER_EUR


@dataclass(frozen=True)
class CostRow:
    config_hash: str
    n: int
    mean_tokens_in: float
    median_tokens_in: float
    mean_tokens_out: float
    median_tokens_out: float
    mean_eur: float
    median_eur: float
    mean_seconds: float
    median_seconds: float


def cost_per_incident(rows: Iterable[Mapping[str, object]]) -> list[CostRow]:
    """Mean and median input tokens, output tokens, euros and seconds per bundle, per condition."""
    groups: dict[str, list[Mapping[str, object]]] = defaultdict(list)
    for row in rows:
        groups[str(row["config_hash"])].append(row)

    out: list[CostRow] = []
    for config_hash, group in sorted(groups.items()):
        t_in = [cast("int", r["tokens_in"]) for r in group]
        t_out = [cast("int", r["tokens_out"]) for r in group]
        eur = [row_eur(i, o) for i, o in zip(t_in, t_out, strict=True)]
        seconds = [cast("float", r["latency_ms"]) / 1000.0 for r in group]
        out.append(
            CostRow(
                config_hash=config_hash,
                n=len(group),
                mean_tokens_in=round(statistics.mean(t_in), 1),
                median_tokens_in=statistics.median(t_in),
                mean_tokens_out=round(statistics.mean(t_out), 1),
                median_tokens_out=statistics.median(t_out),
                mean_eur=round(statistics.mean(eur), 6),
                median_eur=round(statistics.median(eur), 6),
                mean_seconds=round(statistics.mean(seconds), 3),
                median_seconds=round(statistics.median(seconds), 3),
            )
        )
    return out


def _price_header() -> str:
    return (
        f"# prices ADR-0001: DeepInfra checked {PRICE_DATE} "
        f"(USD {USD_PER_1M_IN}/1M input, USD {USD_PER_1M_OUT}/1M output); "
        f"euros at ECB {EUR_RATE_DATE}, 1 EUR = {USD_PER_EUR} USD"
    )


def write_cost_csv(cost_rows: Sequence[CostRow], path: Path) -> None:
    """Write the per-condition cost table, with the price date as the first (comment) line."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        handle.write(_price_header() + "\n")
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for cost_row in cost_rows:
            writer.writerow(asdict(cost_row))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    results_path = Path(args[0]) if args else DEFAULT_RESULTS

    if not results_path.exists():
        # No run has produced results yet: write the schema and the price date, zero rows.
        write_cost_csv([], OUTPUT)
        print(f"no results at {results_path}; wrote header-only {OUTPUT}", file=sys.stderr)
        return 0

    from thesis.eval.results import read_results

    rows = read_results(results_path)
    write_cost_csv(cost_per_incident(rows), OUTPUT)
    print(f"wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "CostRow",
    "cost_per_incident",
    "row_eur",
    "write_cost_csv",
]
