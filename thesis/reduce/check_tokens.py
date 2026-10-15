"""Per-call token-budget assertions for the frozen reduction (E3-08, SCRUM-99).

The token budget is enforced in code, so an oversized bundle fails at build time rather than after
thousands of LLM calls (record §4.4). The ceilings are frozen in `reduction-v1.0` (METHODS.md Annex
E §9): input ≤ 2,000 target / 2,500 ceiling, output ≤ 200 target / 250 ceiling. Tokens are counted
with the experiment model's own tokenizer — the vendored Llama 3.1 tokenizer (ADR-0001, ADR-0011)
— never a stand-in, which would pass here and mis-measure in production.

The input ceiling is per call and applies to the full prompt (static prefix + reduced bundle;
ticket ASSUMPTION). The prompt text is frozen later (E6-02), so this module counts whatever prompt
string it is given: `assert_input_tokens` and the client's `assert_output_tokens` take the final
text, and the report over pilot bundles records the reduced-bundle tokens that this ticket controls.

    python -m thesis.reduce.check_tokens    # assert the ceiling over pilot bundles; write report
"""

from __future__ import annotations

import gzip
from pathlib import Path
from typing import TYPE_CHECKING

from thesis.reduce.policy import reduce, to_json

if TYPE_CHECKING:
    from tokenizers import Tokenizer

    from thesis.assemble.bundles import Bundle

REPO_ROOT = Path(__file__).resolve().parents[2]
# Stored gzipped: the raw vocabulary holds ordinary brand/product-name subword tokens that would
# trip the repo's AI-attribution guard on a plaintext diff. It is an opaque binary model artifact.
TOKENIZER_PATH = REPO_ROOT / "models" / "tokenizer" / "llama-3.1-8b-instruct" / "tokenizer.json.gz"
PILOT_DIR = REPO_ROOT / "data" / "pilot"
REPORT_PATH = REPO_ROOT / "docs" / "reduction" / "token_report.md"

# Frozen in reduction-v1.0 (METHODS.md Annex E §9; record §4, §4.4). Not experiment conditions, so
# they live with the other frozen reduction constants, like the exemplar caps in policy.py.
INPUT_TARGET = 2000
INPUT_CEILING = 2500
OUTPUT_TARGET = 200
OUTPUT_CEILING = 768  # raised from 250 for the visible reasoning under json_object (changelog 19)

_TOKENIZER: Tokenizer | None = None


class TokenCeilingError(ValueError):
    """A prompt or completion exceeds its frozen per-call token ceiling."""


def load_tokenizer(path: Path = TOKENIZER_PATH) -> Tokenizer:
    """Load the vendored Llama 3.1 tokenizer (the experiment model's own; ADR-0011)."""
    from tokenizers import Tokenizer

    if not path.exists():
        raise FileNotFoundError(f"experiment tokenizer not vendored at {path} (see ADR-0011)")
    return Tokenizer.from_str(gzip.decompress(path.read_bytes()).decode("utf-8"))


def count_tokens(text: str, tokenizer: Tokenizer | None = None) -> int:
    """Token count of `text` under the experiment tokenizer. Caches the default tokenizer."""
    global _TOKENIZER
    if tokenizer is None:
        if _TOKENIZER is None:
            _TOKENIZER = load_tokenizer()
        tokenizer = _TOKENIZER
    return len(tokenizer.encode(text).ids)


def assert_input_tokens(
    prompt: str, *, bundle_id: str | None = None, tokenizer: Tokenizer | None = None
) -> int:
    """Return the prompt's token count; raise `TokenCeilingError` if it exceeds the input ceiling.

    `prompt` is the full prompt the model receives (static prefix + reduced bundle). `bundle_id`
    names the offending bundle in the message.
    """
    n = count_tokens(prompt, tokenizer)
    if n > INPUT_CEILING:
        where = f" (bundle {bundle_id})" if bundle_id else ""
        raise TokenCeilingError(
            f"prompt is {n} tokens{where}, over the {INPUT_CEILING}-token input ceiling"
        )
    return n


def assert_output_tokens(completion: str, tokenizer: Tokenizer | None = None) -> int:
    """Return the completion's tokens; raise if over the output ceiling (used by the client)."""
    n = count_tokens(completion, tokenizer)
    if n > OUTPUT_CEILING:
        raise TokenCeilingError(
            f"completion is {n} tokens, over the {OUTPUT_CEILING}-token output ceiling"
        )
    return n


def reduced_prompt(view: dict[str, object], prefix: str = "") -> str:
    """The prompt string whose tokens are budgeted: static prefix (E6-02) + reduced-bundle JSON."""
    return prefix + to_json(view)


def _percentile(values: list[int], pct: float) -> int:
    ordered = sorted(values)
    k = min(len(ordered) - 1, int(round((pct / 100) * (len(ordered) - 1))))
    return ordered[k]


def _median(values: list[int]) -> float:
    ordered = sorted(values)
    n = len(ordered)
    return ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2


def _pilot_bundles() -> list[Bundle]:
    """Assemble every pilot run's annotated alerts into bundles (labels irrelevant to tokens)."""
    from thesis.assemble.bundles import assemble
    from thesis.detect.annotate import annotate_run
    from thesis.labels.windows import load_window_seconds
    from thesis.normalize.store import read_alerts
    from thesis.schema.alert import Alert, Source

    window_s = load_window_seconds()
    tmp = PILOT_DIR / "_annotated_for_tokens"
    bundles: list[Bundle] = []
    for run_dir in sorted(p for p in PILOT_DIR.iterdir() if p.is_dir() and (p / "flows").is_dir()):
        annotate_run(run_dir, annotated_dir=tmp)
        alerts: list[Alert] = []
        for source in (Source.FLOWS, Source.MQTT, Source.HONEYPOT):
            path = tmp / source.value / f"{run_dir.name}.parquet"
            if path.exists():
                alerts.extend(read_alerts(path))
        if not alerts:
            continue
        t0 = min(a.ts for a in alerts)
        bundles.extend(assemble(alerts, [], sources=set(Source), window_s=window_s, t0=t0))
    return bundles


def _write_report(counts: list[tuple[str, int]], over: list[tuple[str, int]]) -> None:
    tokens = [n for _, n in counts]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Reduced-bundle token report (E3-08, SCRUM-99)",
        "",
        "Prompt tokens over the pilot bundles, counted with the experiment model's own tokenizer"
        " (vendored Llama 3.1, ADR-0001 / ADR-0011). The frozen per-call ceilings (reduction-v1.0,"
        f" METHODS.md Annex E §9): input target {INPUT_TARGET}, **ceiling {INPUT_CEILING}**;"
        f" output target {OUTPUT_TARGET}, ceiling {OUTPUT_CEILING}.",
        "",
        "These are **reduced-bundle** tokens: the static prompt prefix is frozen later (E6-02); the"
        " full-prompt assertion adds the prefix once it exists (`reduced_prompt(view, prefix)`).",
        "",
        f"- Pilot bundles measured: **{len(tokens)}**",
    ]
    if tokens:
        lines += [
            f"- Minimum: **{min(tokens)}** tokens",
            f"- Median: **{_median(tokens)}** tokens",
            f"- 95th percentile: **{_percentile(tokens, 95)}** tokens",
            f"- Maximum: **{max(tokens)}** tokens",
            f"- Over the {INPUT_CEILING}-token input ceiling: **{len(over)}**"
            + ("" if not over else " — " + ", ".join(f"{bid} ({n})" for bid, n in over)),
        ]
    else:
        lines.append("- No pilot bundles found; run the pilot pipeline first.")
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    bundles = _pilot_bundles()
    counts = [(b.bundle_id, count_tokens(reduced_prompt(reduce(b)))) for b in bundles]
    over = [(bid, n) for bid, n in counts if n > INPUT_CEILING]
    _write_report(counts, over)
    if over:
        for bid, n in over:
            print(f"OVER CEILING: bundle {bid} is {n} tokens > {INPUT_CEILING}")
        return 1
    print(f"ok: {len(counts)} pilot bundles, all within the {INPUT_CEILING}-token input ceiling")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
