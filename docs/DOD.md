# Definition of Done and Definition of Ready — v1.0

Every ticket on the board inherits both. Version 1.0, 1 October 2026.

## Definition of Done

### Core — every ticket
- [ ] Every acceptance criterion is checked, and every deliverable exists at the path the ticket names.
- [ ] Any ASSUMPTION made while working is written down: in METHODS.md if it affects measurement, otherwise as a Jira comment.
- [ ] Leftover work becomes a new ticket. A ticket is never closed "mostly done".
- [ ] If a decision changed, `thesis_project_full_record.md` is updated.
- [ ] If the ticket produced a decision, number or figure the thesis will cite, one line is appended to `docs/thesis_notes.md` with the ticket key, chapter, value and source file.
- [ ] Actual effort is noted in a comment when it was more than twice the estimate.

### Code tickets — also
- [ ] Merged to `main`; pre-commit and CI pass (ruff, mypy strict on `thesis/`, pytest).
- [ ] Tests follow record §6.9: parsers, assembly, reduction and validators are tested; reduction changes update the golden files; validator changes keep the property tests passing; anything calling Ollama is marked `slow`; LLM output quality is never unit-tested; there is no coverage target.
- [ ] Every LLM call goes through the single client (E6-01) and logs every §6.10 field.
- [ ] Result-producing code writes the config, its hash and the full §4.2 provenance in every row.
- [ ] Code producing bundles, labels or metrics is seeded, and a re-run gives an identical output hash.
- [ ] No new dependency, service or infrastructure without an ADR in `docs/adr/`.
- [ ] No secret appears in the repo or the logs.
- [ ] No code path can act on the testbed or any network. The system only recommends.

### Research and freeze tickets — also
- [ ] The frozen document is dated, version-tagged in git and referenced from METHODS.md.
- [ ] Every rule defining correct, acceptable or unsafe carries a citation or a stated rationale.

### Change control — any ticket that alters a locked parameter
Locked parameters: W; the reduction policy and token ceilings; the alert schema after the freeze; the action catalog and action sets; the rejection policy and safety scoring; reliability and robustness definitions; target N and k; the condition matrix; the model and its revision; prompt templates after the first experiment; retrieval k; device criticality.
- [ ] A METHODS.md changelog entry is appended (never an edit of old text): date, what changed, why, which results are invalidated.
- [ ] An ADR only if a technology or architecture decision changed.
- [ ] If results already exist, every affected condition is re-run.

### Run tickets — also
- [ ] The isolation check passed and is logged.
- [ ] `verify_corpus` passes.
- [ ] The spending cap was active, and the actual cost is recorded.

### Writing tickets — also
- [ ] Text is in `docs/thesis/`, and every figure and number traces to `docs/thesis_notes.md` or a results file.
- [ ] References are in IEEE style.

### Spike tickets
Only the Core section and the ticket's own criteria apply. Throwaway code stays in `spikes/`.

## Definition of Ready

A ticket can start only when all of these are true:
- [ ] It traces to at least one inventory ID (R-xxx) and to an H1–H4 or a risk number.
- [ ] Every "Depends on" ticket is Done, or a ticket-level exception is written in it.
- [ ] It is 5 points or less, and every acceptance criterion names something checkable.
- [ ] Every blocking §10 open question is answered, or this ticket answers it.
- [ ] Integrity gate: if it produces agent or baseline outputs on corpus bundles, every `freeze-before-results` ticket is Done.
- [ ] The versions of its inputs are named: corpus tag, METHODS.md version, catalog version, model revision.
- [ ] If it carries `needs-refinement`, the spike findings have been read, the ticket updated, and the label removed.
- [ ] If it changes a locked parameter after the freeze, a changelog entry is part of its acceptance criteria.
- [ ] Required resources are in place: the spending cap before the first hosted call, Ollama stopped before any testbed run.
