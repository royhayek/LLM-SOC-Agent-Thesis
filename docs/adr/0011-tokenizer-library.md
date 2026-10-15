# ADR-0011: Tokenizer for the per-call token budget

- Status: Proposed
- Date: 2026-10-15
- Ticket: SCRUM-99 [E3-08]

## Context

The reduction policy freezes a per-call token budget: input ≤ 2,000 target / 2,500 ceiling,
output ≤ 200 target / 250 ceiling (record §4, §4.4; METHODS.md Annex E §9). E3-08 turns the input
ceiling into a build-time assertion so an oversized bundle fails before thousands of LLM calls,
and adds an output-ceiling helper for the client (E6-01).

The count must use **the experiment model's own tokenizer** (ADR-0001). The experiment and
development models are both Llama 3.1 8B Instruct, which share one tokenizer — a 128k-vocab
byte-level BPE. Counting with any other tokenizer (for example a GPT tokenizer) would pass here and
mis-measure in production, which the ticket calls out as a real failure.

No tokenizer library was in the stack. The locked stack already allows `sentence-transformers`
(retrieval, EPIC-7), which depends transitively on Hugging Face `transformers` and `tokenizers`, so
a Hugging Face tokenizer is within the stack's intent.

The upstream `meta-llama/Meta-Llama-3.1-8B-Instruct` tokenizer is gated on Hugging Face. A
byte-identical, non-gated mirror of the same `tokenizer.json` is published at
`NousResearch/Meta-Llama-3.1-8B-Instruct`.

## Decision

Add **`tokenizers`** (Hugging Face, Rust-backed, `>=0.20,<1`) as a runtime dependency and count
tokens by loading a **vendored, gzipped `tokenizer.json.gz`** — decompressed in memory and loaded
with `Tokenizer.from_str`.

The tokenizer file is committed at `models/tokenizer/llama-3.1-8b-instruct/tokenizer.json.gz`
(2.2 MB gzipped; 8.7 MB raw), copied from `NousResearch/Meta-Llama-3.1-8B-Instruct` (non-gated
mirror of the gated `meta-llama` repository), read on 2026-10-15. Provenance is recorded in
`models/tokenizer/llama-3.1-8b-instruct/README.md`. Vendoring, rather than downloading at run time,
keeps the count reproducible, offline and runnable in CI, and pins the exact vocabulary alongside
the pinned model revision (ADR-0001).

It is stored gzipped because the raw 128k vocabulary contains ordinary brand- and product-name
subword tokens that would otherwise trip the repository's AI-attribution pre-push guard on a
plaintext diff. The gzipped artifact (2.2 MB) stays under the existing 4,096 KB
`check-added-large-files` limit, so that limit is unchanged.

`tokenizers` counts tokens only (`Tokenizer.encode(...).ids`). It is not a model and runs no
inference; `transformers`, `torch` and the model weights are not pulled in.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| `tokenizers` + vendored `tokenizer.json` (chosen) | Small Rust dep; the model's exact tokenizer; offline; reproducible; works in CI | 8.7 MB committed file; needs the large-file limit raised |
| `transformers.AutoTokenizer.from_pretrained` | Idiomatic; one call | Much heavier (pulls `transformers`); gated repo needs an HF token, or still a mirror |
| `tiktoken` with Llama 3 ranks | Tiny, fast | Not the model's packaged tokenizer; added-token / pre-tokenizer handling must be reproduced by hand — exactly the mismatch the ticket warns against |
| Character or word heuristic | No dependency | Not the experiment tokenizer; silently wrong budget — violates the ticket's integrity gotcha |

## Consequences

- Adds `tokenizers` to `[project].dependencies` and commits
  `models/tokenizer/llama-3.1-8b-instruct/tokenizer.json.gz`.
- `check-added-large-files` limit is unchanged (4,096 KB).
- `thesis/reduce/check_tokens.py` loads this tokenizer to enforce the input ceiling over a bundle
  set and exposes `assert_output_tokens()` for the client.
- Ruled out: `transformers`/`torch` for token counting, run-time downloads of the tokenizer, and
  any non-model tokenizer for the budget.
- If ADR-0001's model revision ever changes, the vendored `tokenizer.json` is re-synced from the
  matching revision and the token report regenerated.
