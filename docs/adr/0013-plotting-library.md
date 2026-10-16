# ADR-0013: Plotting library for the results figures (matplotlib)

- Status: Accepted (2026-10-16)
- Date: 2026-10-16
- Ticket: SCRUM-118 [E9-11]

## Context

E9-11 regenerates every results figure from the hashed results (E9-09) so no figure is drawn by
hand (ticket gotcha: "a figure edited by hand after generation breaks traceability"). The tables are
plain Markdown and need nothing, but the figures need a plotting library, which is a new dependency
and so needs an accepted ADR (`docs/WORKING_RULES.md`). The thesis cites a small number of static
figures (bar charts of detection and classification by condition for H1/H2/H4); no interactivity is
needed, and they render headless in CI.

## Decision

Accepted by Roy El Hayek on 2026-10-16: add **matplotlib** (3.11.2, pinned in `uv.lock`) as a
dependency, used only in `thesis/eval/report.py` with the
non-interactive `Agg` backend to write PNGs under `docs/thesis/figures/`. The report already runs
without it — it writes the tables and skips the figures with a notice — so the dependency is additive
and the tables never depend on it. Pin the version in the lock file as usual.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| matplotlib (Agg) | The standard, stable, headless; one dependency; well understood | A sizeable dependency tree (numpy already present; adds pillow, contourpy, fonttools, kiwisolver) |
| plotly / bokeh | Interactive, nice defaults | Heavier, aimed at HTML interactivity the static thesis does not use; larger install |
| Hand-written SVG from the tables | No new dependency | Re-implements axes, ticks and layout; more code to maintain than it saves; error-prone |
| No figures, tables only | Zero new dependency | The ticket requires figures; a results chapter with only tables is weaker |

## Consequences

- `report.py` can write the figures; without this accepted, it writes the tables and `outputs.md`
  and skips the figures (already implemented), so E9-11's tables are complete regardless.
- numpy is already a dependency (retrieval, bootstrap); matplotlib adds its usual support packages.
- Figures are deterministic in content; PNG bytes may differ across matplotlib versions, so only the
  tables carry the "byte-identical on re-run" guarantee (E9-11 AC), not the figures.
