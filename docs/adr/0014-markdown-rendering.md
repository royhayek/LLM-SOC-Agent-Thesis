# ADR-0014: Markdown rendering for the console report

- Status: Accepted (2026-10-16)
- Date: 2026-10-16
- Ticket: — (post-audit console UX; EPIC-10)

## Context

The console's incident detail (E10-05) shows the E7-08 report. The report is Markdown — a heading,
a field table, an evidence list, a key-findings list and a recommend-only footer (`thesis/report/
template.md`). The console first showed it as raw Markdown source in a `<pre>` block, which reads as
source, not a report.

The report is a human-facing summary meant to be read in under a minute (Arch §2, §5 step 8), so it
should render as Markdown. The hard constraint is the console's XSS rule (E10-05 gotcha, §1.1): any
attacker-influenced bundle text that reaches the report — the model's free-text findings, the alert
summaries — must never become active markup in a security tool. The report renderer already escapes
Markdown specials in those fields (`thesis/report/render.py:_md_escape`), so the only Markdown
*structure* in a report is the template's own; the untrusted leaves are inert text.

## Decision

Render the report with **react-markdown** (^10) plus **remark-gfm** (^4), in the console frontend
only.

- react-markdown emits React elements, never `dangerouslySetInnerHTML`.
- Raw HTML is **not** rendered: `rehype-raw` is not added, so any HTML in the Markdown appears as
  literal text (an `<img onerror=…>` in bundle text is shown, not executed). This preserves the
  E10-05 guarantee.
- remark-gfm is required for the report's pipe **table** (GFM); it adds no HTML.
- Link URLs use react-markdown's default sanitising `urlTransform` (drops `javascript:` etc.); the
  report renderer also escapes `[` `]` `(` `)` in untrusted text, so a link cannot be injected.
- Elements are styled with Tailwind classes via the `components` map, to match the console. No
  Tailwind Typography plugin is added.

## Alternatives considered

| Option | For | Against |
|---|---|---|
| react-markdown + remark-gfm (chosen) | Safe by default (no raw HTML, no dangerouslySetInnerHTML); standard, maintained; handles the GFM table | Two small frontend dependencies |
| In-house Markdown subset renderer | No dependency | Reinvents Markdown (table + inline escapes are fiddly); more code to own and a larger surface for a parsing bug |
| marked / markdown-it + DOMPurify | Fast | Produces an HTML string needing `dangerouslySetInnerHTML` + a sanitiser; more XSS surface than a React-element renderer |
| Leave as `<pre>` source | Simplest, already safe | Reads as source, not a report |

## Consequences

- `frontend` gains `react-markdown` and `remark-gfm`. No backend or experiment change; the report
  content and `thesis/report/render.py` are unchanged.
- The report renders as a formatted document in the detail view; raw HTML stays inert.
- Ruled out: rendering the report via `dangerouslySetInnerHTML`, and adding `rehype-raw` or a
  Tailwind Typography plugin.
