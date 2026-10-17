# Design: console demo simulator

- Date: 2026-10-17
- Status: Draft for review
- Scope: a new "Demo" view in the console (EPIC-10) that replays a captured attack episode end to
  end for the MSc defense, plus an optional live model run. Phase 1 + Phase 2 in one spec.

## 1. Intent

A reliable, compelling demo for the defense that walks examiners through the platform end to end:
raw IoT telemetry streaming in → detectors raising alerts → a bundle being assembled → the agent's
three-step reasoning → a validated verdict → a **recommended** action → the human accept/reject.

The demo must *show how the platform works*, especially how threats are detected, alerted on, and how
actions are recommended — not claim the agent is better than it is.

Audience: the defense committee. Success: in ~3–5 minutes, on a laptop, with no network and no
surprises, the examiners see one attack campaign flow through every stage, can pause/scrub/rewind,
can compare the agent against a baseline on the same incident, and (optionally) watch one bundle run
against the real hosted model.

### What the committee decided (brainstorming, 2026-10-17)

- Mode: **replay backbone + optional live run** on a single bundle.
- Story: **feed + drill-in** — a live-updating incident feed as a window replays, each incident
  drillable into its full lifecycle.
- Unit: **one scenario = one attack episode** (~5 bundles over a time window).
- Scope: **Phase 1 + Phase 2** together.
- Scenarios: SSH/honeypot brute-force, SYN flood, MQTT flood/brute-force, plus a benign window and an
  honest-limitation case (agent wrong/withholds; toggle to Baseline A to show it classifies better).

## 2. Constraints (binding)

From `docs/WORKING_RULES.md` and `METHODS.md`:

- **The agent recommends, never executes.** No demo path acts on a testbed or network, even in
  simulation. The demo shows a recommended action and records a human decision; it does nothing else.
- **The experiment is frozen.** The replay reads frozen artifacts only. The optional live run
  executes the frozen pipeline (same pinned model/config, exactly three calls, fresh context) on one
  bundle; it **never writes `results.parquet`**, retunes a detector, or edits a prompt.
- Localhost only, no auth. **SSE is allowed; WebSockets are not.**
- **No new dependencies.** The replay clock, pipeline strip, feed and transport are plain React +
  Tailwind + `requestAnimationFrame`; rendering reuses `react-markdown` (ADR-0014). The backend uses
  the existing FastAPI / pyarrow / PyYAML. If any new dependency is ever needed, an ADR comes first.
- 16 GB machine; never Ollama + Docker together (not relevant here — the demo runs neither). The
  hosted model costs money under a €/$ cap; the live run is gated and shows an estimate.

### Research integrity

The demo is a view over the frozen run and a re-execution of the frozen instrument. It adds no
measurement and changes no locked parameter. The scenario catalog is presentation config, not a
locked parameter. The live run's output is shown and discarded, never persisted to results.

## 3. Non-goals

- No new attacks, no live testbed, no Docker, no packet generation.
- No action execution or remediation, simulated or real.
- No authentication, multi-user, or remote access.
- No charting/animation/timeline library (would need an ADR; avoided by design).
- No change to the analyst screens (Incidents, Audit) or to `thesis/report`, the detectors, the
  graph, or the experiment harness.

## 4. Scenario model

A **scenario** is one captured attack episode (or a benign window), named in a curated catalog so the
defense is stable. The catalog is `config/demo_scenarios.yaml`:

```yaml
scenarios:
  - id: ssh-bruteforce
    title: "SSH brute-force on the honeypot"
    description: "An external host guesses SSH passwords against hp-ssh-01."
    episode_id: ep-sshbrute-eval-00X        # chosen from the data during implementation
    attack_family: ssh_brute_force
    default_condition: C1
    highlight: null
  - id: syn-flood
    ...
  - id: mqtt-flood
    ...
  - id: benign
    title: "A quiet window"
    description: "No attack present; the agent recommends monitoring, not action."
    ...
    highlight: "No false alarm: the agent recommends no_action/monitor."
  - id: honest-limitation
    title: "Where the agent struggles"
    description: "The agent misclassifies (or withholds); Baseline A classifies it correctly."
    ...
    default_condition: C1
    highlight: "Toggle Brain to Baseline A — it gets the class right (H2/H4)."
```

Episode selection criteria (applied against `results.parquet` during implementation, recorded in the
catalog):
- One episode per attack family with a clean, emitted C1 verdict and a recommended active action.
- Benign: a window of bundles with `ground_truth` benign where C1 recommends `no_action`/`monitor`.
- Honest-limitation: a bundle where C1's `incident_type` ≠ `ground_truth` (or withheld) **and** C7
  (Baseline A) predicts correctly, so the Brain toggle tells the true H2/H4 story.

The episodes exist: the eval set has 98 episodes, including `ep-syn-eval-*`, `ep-mflood-*`,
`ep-mbrute-*`, `ep-bot-*` (~5 bundles each), plus benign/background bundles.

## 5. Event model (what the backend serves, what the clock plays)

For a `(scenario, condition)`, the backend builds a **time-ordered list of events**:

```
Event = { t: seconds-from-window-start, kind, payload }
kind ∈ { alert, bundle_formed, reasoning, verdict, recommendation }
```

- `alert` — one per alert in the episode's bundles, at the alert's real `ts`. payload: bundle_id,
  source (flows|mqtt|honeypot), alert_id, detector_label, detector_score, one-line summary.
- `bundle_formed` — at each bundle's `window_end`. payload: bundle_id, device, window, sources,
  n_alerts, ground_truth.
- `reasoning` — three per bundle (evidence, classify, recommend), placed just after `bundle_formed`,
  paced by the **real per-node latencies** from the call log (`latency_ms`) when present, else small
  fixed offsets. payload: node, completion (for the drill-in trace).
- `verdict` — after the reasoning. payload: incident_type, severity, affected_device, confidence, or
  `withheld`.
- `recommendation` — after the verdict. payload: recommended_action, severity, evidence ids.

The human decision is interactive, not a timed event.

**Timing model (documented honesty).** Alerts play at their real capture times; bundles form at real
window boundaries. The agent's reasoning happened offline after capture, so the demo places
`reasoning`/`verdict`/`recommendation` a few (real-latency-paced) seconds after each `bundle_formed`
to narrate "bundle forms → agent reasons → recommends". This is a presentation device over real
outputs, stated in the UI ("replayed") and here.

## 6. Backend

A new module `thesis/api/demo.py`, wired into `create_app`. New endpoints (localhost, read-only
except the live run, which is a model call, not a testbed action):

- `GET /demo/scenarios` → the catalog (id, title, description, attack_family, default_condition,
  n_incidents, available conditions).
- `GET /demo/scenarios/{id}?condition=C1` → `{ scenario, window, events: [...] }` for the player.
- `GET /demo/live/{bundle_id}/trace?condition=C1` (SSE, Phase 2) → runs the real three-node graph on
  that bundle against the hosted client and streams `evidence`/`classify`/`recommend` completions,
  then a final `verdict` event and a `cost` event (tokens + estimate). Gated: returns 503 if the
  hosted env is not configured. Never writes results.

### Data assembly (fast, no full build pipeline)

Reconstruct what each endpoint needs from the **persisted parquet**, not `build()` (which reruns the
corpus pipeline and is slow):

- bundles: `data/bundles/v1.0.0/eval.parquet` (bundle_id, device, window_start/end, label,
  episode_id, sources, alert_ids).
- alerts: `data/alerts/{flows,honeypot,mqtt}/*.parquet` (alert_id → ts, source, detector_label,
  detector_score, detail) — indexed once at app start.
- verdicts/recommendations: `results.parquet` via the existing `_load_by_condition` /
  `_verdict_from_row`.
- traces: the call log via the existing `_load_trace`.
- reports: `reports/<report_filename(bundle_id)>` via the existing helper.

A small `bundle_store` reconstructs full `Bundle`/`Alert` objects from the parquet for the live run,
so both replay and live run are fast (no minutes-long `build()`), reusing the existing schema models.

Reused as-is: `_condition_labels`, `_load_by_condition`, `_verdict_from_row`, `_load_trace`,
`report_filename`, the hosted `LLMClient`, `run_graph`.

## 7. Frontend

A new `Demo` view, added to the sidebar. Components (each small, single-purpose):

- `DemoView` — shell: pipeline strip, scenario/Brain controls, feed + drill-in, transport bar.
- `PipelineStrip` — the stage nodes (Telemetry → Detectors → Bundle → Agent[Evidence·Classify·
  Recommend] → Validator → Recommendation → Human); the active stage pulses, driven by the focused
  incident's latest event.
- `ScenarioPicker` + `BrainToggle` (C1 ↔ C6 ↔ C7).
- `TransportBar` — play/pause, scrubber, speed (1×–8×), step, restart; Space = play/pause, ← → =
  step. Keyboard handled at the view.
- `useReplayClock(events, speed)` — a `requestAnimationFrame` virtual clock exposing `nowT`,
  `visibleEvents`, and controls (play/pause/seek/step/restart). Pure and unit-testable.
- `TelemetryFeed` — alerts appearing by source as the clock passes their `t`.
- `IncidentFeed` — incident cards filling as `bundle_formed` events arrive; click to focus.
- `IncidentLifecycle` — the drill-in; **reuses** the report markdown renderer, the beautified
  reasoning trace, and the recommendation/decision components from `IncidentDetail`.
- `LiveRunButton` (Phase 2) — confirm → open the live SSE → stream steps, show elapsed + cost,
  labelled "LIVE · <model>"; result shown, never persisted.
- `Scoreboard` (Phase 2) — running tally: alerts, incidents, recommended (by action), withheld.
- `PresenterMode` (Phase 2) — a toggle that enlarges type and hides sidebar chrome for projection.
- `api/demo.ts` — typed client for `/demo/*`, types from the regenerated OpenAPI.

Shared extraction: the drill-in reuses `IncidentDetail`'s report/trace/recommendation rendering;
where needed, those are factored into small shared components so both screens use one implementation.

## 8. Data flow

```
DemoView mount → GET /demo/scenarios → ScenarioPicker
pick scenario (+Brain) → GET /demo/scenarios/{id}?condition → events[]
useReplayClock(events) → nowT advances → visibleEvents →
  TelemetryFeed (alerts)  +  IncidentFeed (bundles)  +  PipelineStrip (stage)
click incident → IncidentLifecycle (alerts, trace, report, recommendation, decision)
  optional: Run live → GET /demo/live/{bundle_id}/trace (SSE) → steps + cost
```

## 9. Testing

- Backend (`tests/test_demo.py`): scenario catalog load; event assembly from small fixtures —
  ordering by `t`, one `alert` per alert, `bundle_formed` at window_end, three `reasoning` + `verdict`
  + `recommendation` per emitted bundle, `withheld` handled; `/demo/scenarios` and
  `/demo/scenarios/{id}` responses; the live endpoint returns 503 without hosted env (wiring only,
  no model output asserted).
- Frontend: `useReplayClock` reveals events by time and supports pause/seek/step/restart;
  `IncidentFeed` fills on `bundle_formed`; `PipelineStrip` reflects the focused stage; `BrainToggle`
  refetches; drill-in renders report/trace safely (XSS-safe rendering reused). LLM output never
  asserted.
- `pytest -m "not slow"`, `mypy`, `ruff`, frontend `typecheck`/`test`/`build` all green; types
  regenerated from OpenAPI.

## 10. Phasing

- **Phase 1 (core demo):** catalog + `/demo/scenarios(/{id})`, `DemoView`, `useReplayClock`,
  `TransportBar`, `PipelineStrip`, `TelemetryFeed`, `IncidentFeed`, `IncidentLifecycle`, `BrainToggle`.
  Fully from frozen data — this alone is the defense demo.
- **Phase 2:** `LiveRunButton` + `/demo/live/{bundle_id}/trace`, `Scoreboard`, `PresenterMode`,
  keyboard shortcuts.

Both phases are in this spec; the implementation plan will sequence them so Phase 1 is demoable before
Phase 2 starts.

## 11. Risks and mitigations

- **Live demo fragility** → replay is deterministic, offline, pausable/scrubbable; the live run is
  optional and gated.
- **Slow bundle reconstruction** → load from persisted parquet, not `build()`; index alerts once at
  start.
- **Over-selling the agent** → a mandatory benign scenario (no false alarm) and an honest-limitation
  scenario with the Brain toggle to Baseline A (matches H1 held / H2–H4 as found).
- **Scope creep** → no new dependency; reuse existing components and API helpers; Phase 2 is cleanly
  separable.
- **XSS** → all dynamic/attacker-influenced text rendered via the existing escaped/no-raw-HTML path.

## 12. Open questions (for Roy)

1. Exact episode ids for the five scenarios — chosen from the data during implementation against the
   §4 criteria, then written into the catalog for your confirmation.
2. Playback default speed (proposed: 4×) and whether the window should auto-compress very long gaps
   between alerts (proposed: cap idle gaps at ~2 s of playback so the demo never stalls).
3. Whether the live run should default to the shown eval bundle or a pilot bundle (proposed: the shown
   bundle, since it only re-executes the frozen pipeline and persists nothing).
