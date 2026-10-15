# Golden files

Golden files fix the **exact** output of a frozen step for a set of committed inputs (record
§6.9). The test re-runs the step on each input and compares byte-for-byte against the committed
expected output. Any change to the output — even one character of format — fails CI instead of
silently shifting experiment results.

## `reduce/`

Golden pairs for the frozen reduction policy (`reduction-v1.0`, E3-06). Each case is two files:

- `<case>.input.json` — the input: `{"sources": [...], "bundle": {...}}`, a serialized
  `thesis.assemble.bundles.Bundle` plus the configured sources.
- `<case>.expected.json` — the reduced view as compact JSON, one line, exactly as the agent and
  both baselines receive it.

Four source mixes are covered: `all_sources` (flows + MQTT + honeypot), `flows_only`,
`flows_honeypot`, and `exemplar_cap` (more flow alerts than the exemplar cap, so the overflow
spills into `other_ids`).

The test is `tests/test_reduce_golden.py`.

## Updating a golden

**A golden changes only when the reduction policy changes.** The policy is frozen (METHODS.md
Annex E) as of the E2-09 freeze. Updating a golden after that freeze is a locked-parameter change
under the Definition of Done's change control:

1. First land the reviewed policy change with an appended **METHODS.md changelog entry** (frozen
   text is never edited). If results already exist, the affected conditions are re-run.
2. Only then regenerate the goldens:

   ```
   python -m tests.test_reduce_golden
   ```

3. Review every regenerated `*.expected.json` by eye against the policy before committing. A
   golden regenerated without review just freezes whatever the code does today.

Never regenerate a golden to make a failing test pass without going through step 1.
