# ADR-0010: Parquet library

- Status: Proposed
- Date: 2026-10-10
- Ticket: SCRUM-40 [E2-04]

## Context

The locked stack stores normalized alerts, bundles and experiment results as **Parquet**
(`docs/WORKING_RULES.md`; record §6.7: "Normalized alerts, bundles → Parquet", "Experiment
results → Parquet, one row per (bundle, condition, repetition)"). The format is decided; the
**library** that reads and writes it is not, and it is a new dependency, so it needs an ADR
before it is added (WORKING_RULES, "Any other new dependency … needs an accepted ADR").

E2-04 is the first ticket that must write Parquet: `label_windows()` writes
`data/labels/<run_id>.parquet`. Later tickets write alerts (EPIC-3), bundles (EPIC-3) and
results (EPIC-9) the same way. There is no Parquet writer in the Python standard library, so a
third-party library is required.

Criteria. The library must: (C1) read and write Parquet files; (C2) be deterministic, so a
re-run gives a byte-identical file for the same input (record §4.2, reproducibility); (C3) add
as little as possible to the locked, minimal dependency set (currently `pydantic`, `pyyaml`,
`structlog`); (C4) not pull in a service or native component that needs its own characterisation.

The statistical analysis of EPIC-9 (McNemar, Wilcoxon, the episode block bootstrap, §4) will
separately need `numpy`/`scipy` and possibly a dataframe library; that is a different choice for
a different epic and is **out of scope here**. This ADR fixes only the Parquet read/write library.

## Decision

Proposed: **pyarrow** (Apache Arrow's Python bindings). Roy accepts or changes it.

- Write with `pyarrow.Table.from_pydict(...)` + `pyarrow.parquet.write_table(...)`; read with
  `pyarrow.parquet.read_table(...)`. No pandas is pulled in: the thesis code builds tables from
  plain Python columns, which keeps the dependency to one wheel.
- Pin a major version in `pyproject.toml` (for example `pyarrow>=17,<22`) and let `uv.lock`
  record the exact build.
- Writing is deterministic for a fixed schema and row order (the code sorts rows before writing),
  which satisfies the re-run-identical requirement; where the exact bytes must match, compare the
  logical table (schema + rows), not the file bytes, because Parquet can embed a library version.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| **pyarrow** (proposed) | The reference Parquet implementation; one wheel; no pandas needed; used by pandas/polars under the hood, so files interoperate | A large wheel (tens of MB); its API is lower-level than a dataframe library |
| **pandas + pyarrow** | Familiar dataframe API; convenient for the EPIC-9 stats | Two heavy dependencies now, for a job (writing a few columns) that does not need a dataframe yet; the stats library choice belongs to EPIC-9, not here |
| **polars** | Fast, single wheel, native Parquet read/write, good for later filtering of bundles/results | Still needs `scipy` for the stats; a second dataframe engine if EPIC-9 later picks pandas; larger conceptual surface than pyarrow for this ticket's one write |
| **fastparquet** | Parquet-only, lighter than pyarrow | Less widely used and less interoperable than the Arrow implementation; would likely be replaced once a dataframe library is added anyway |

## Consequences

- `pyproject.toml` gains `pyarrow`; `uv.lock` is updated. It is the fourth runtime dependency.
- `thesis/labels/windows.py` (E2-04) and the later alert/bundle/result writers use pyarrow to
  read and write Parquet. A thin helper (schema + sorted rows → Parquet) keeps the call sites
  small and the output reproducible.
- The EPIC-9 statistical-analysis libraries (`numpy`/`scipy`, and any dataframe library) remain
  an open choice, to be fixed by their own ADR when that epic starts.
- Ruled out for now: pandas as a runtime dependency, polars, fastparquet.
