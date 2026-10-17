# Console Demo Simulator Implementation Plan

> Implement task-by-task, in order. Each task ends with a passing test and a commit. Steps use
> checkbox (`- [ ]`) syntax for tracking progress.

**Goal:** Add a "Demo" view to the console that replays a captured attack episode end to end (telemetry → detectors → bundle → agent reasoning → verdict → recommended action → human decision) from frozen data, with an optional live model run on one bundle.

**Architecture:** A thin backend "scenarios" layer assembles a time-ordered event list for one episode under one condition from the persisted parquet + call log + reports; three FastAPI endpoints serve it. The frontend owns a virtual replay clock (`requestAnimationFrame`) that reveals events by their timestamp, animating a pipeline strip, a telemetry feed, an incident feed and a drill-in lifecycle. The optional live run reconstructs one bundle from parquet and streams the real three-node graph over SSE.

**Tech Stack:** Python 3.12, FastAPI, pyarrow, PyYAML, pydantic (existing); React 19 + TypeScript + Tailwind + `requestAnimationFrame` + `react-markdown` (existing). **No new dependencies.**

**Spec:** `docs/design/2026-10-17-demo-simulator.md` (read it alongside this plan).

## Global Constraints

Copied from the spec and `docs/WORKING_RULES.md` — every task must honor these:

- **The agent recommends, never executes.** No demo code path acts on a testbed or network. The only write is the existing human accept/reject into SQLite. The live run calls the model only.
- **Frozen experiment.** The replay reads frozen artifacts only. The live run executes the frozen pipeline (pinned model/config, exactly three calls, fresh context) and **never writes `results.parquet`** or any experiment artifact.
- **No new dependencies.** If one seems needed, stop and raise an ADR; do not add it.
- **SSE only, never WebSockets.** Localhost only (`127.0.0.1`), no auth.
- **No assistant tooling reaches git** (per the repo's local commit rules): no tool names, assistant attribution, or extra authorship trailers in any commit message, branch name, PR title/body, comment or tracked file. Commit with the configured identity. Never use `--no-verify`; if a hook blocks, stop and report.
- **Workflow.** Implement on branch `demo-simulator` (Phase 1) then `demo-simulator-live` (Phase 2); one PR per phase, self-merged after CI is green. Commit per task. Run `uv run pre-commit run --all-files` and `uv run pytest -m "not slow"` before pushing backend changes; `npm run typecheck && npm test && npm run build` before pushing frontend changes. Regenerate OpenAPI types (`npm run gen:types`) whenever an endpoint or response model changes.
- **XSS.** All dynamic/attacker-influenced text renders via the existing escaped / no-raw-HTML path (React text nodes; `react-markdown` without `rehype-raw`). Never `dangerouslySetInnerHTML`.

## Review Focus

Inputs the spec implies but that a task's happy-path tests may miss — each is pinned to a test in the owning task:

- **A bundle withheld by the agent** (no verdict): the event stream must still emit `bundle_formed` and a `verdict{withheld:true}`, and the feed/lifecycle must render it without crashing. → Task 3, Task 10.
- **A bundle whose node output failed to parse** (no trace / no verdict in the call log): assembly must skip reasoning/verdict gracefully, not raise. → Task 3.
- **An episode with a long idle gap between alerts**: the clock must compress idle gaps so playback never stalls. → Task 7.
- **The live endpoint with no hosted env configured**: returns 503, and the button is disabled — never a 500 or a hang. → Task 13, Task 14.
- **Attacker markup inside an alert summary / report / trace** shown in the Demo view: renders as inert text, no element created. → Task 9, Task 10.

---

## PHASE 1 — Replay demo (a complete, demoable deliverable)

### Task 1: Scenario catalog and loader

**Files:**
- Create: `config/demo_scenarios.yaml`
- Create: `thesis/api/demo.py`
- Create: `tests/test_demo.py`
- Create (throwaway helper, not committed): a selection query run once to fill the catalog.

**Interfaces:**
- Produces: `Scenario` (pydantic: `id,title,description,episode_id,attack_family,default_condition,highlight`), `load_scenarios(path=SCENARIOS_PATH) -> list[Scenario]`, `SCENARIOS_PATH`.

- [ ] **Step 1: Select the episodes.** Run this query once and record the chosen ids in the catalog (Step 3). It applies the spec §4 criteria against the frozen results; pick the first good candidate per family, one benign, one honest-limitation.

```python
# run: uv run python - <<'PY'
import pyarrow.parquet as pq
from collections import defaultdict
rows=[r for r in pq.read_table('results/results.parquet').to_pylist() if int(r['repetition'])==0]
def label(r): return (str(r['strategy']),str(r['safety']),frozenset(str(s) for s in r['sources']))
C1=lambda r: label(r)==('agentic','enforcing',frozenset({'flows','honeypot','mqtt'}))
C7=lambda r: str(r['strategy'])=='ml_classifier'
c1={str(r['bundle_id']):r for r in rows if C1(r)}
c7={str(r['bundle_id']):r for r in rows if C7(r)}
# families with a clean emitted C1 verdict + an attack ground truth
fam=defaultdict(list)
for bid,r in c1.items():
    if r['emitted'] and r['episode_id'] and r['incident_type']==r['ground_truth']:
        fam[str(r['ground_truth'])].append(str(r['episode_id']))
for k in sorted(fam): print('FAMILY',k, sorted(set(fam[k]))[:3])
# benign episodes: ground_truth benign, C1 recommends no_action/monitor
benign=sorted({str(r['episode_id']) for bid,r in c1.items()
    if str(r['ground_truth'])=='benign' and str(r['recommended_action']) in ('no_action','monitor') and r['episode_id']})
print('BENIGN', benign[:5])
# honest-limitation: C1 wrong/withheld but C7 right, in a named episode
honest=[str(r['episode_id']) for bid,r in c1.items()
    if r['episode_id'] and (not r['emitted'] or r['incident_type']!=r['ground_truth'])
    and bid in c7 and str(c7[bid]['incident_type'])==str(r['ground_truth'])]
print('HONEST', sorted(set(honest))[:5])
PY
```

- [ ] **Step 2: Write the failing test** for the loader:

```python
# tests/test_demo.py
from thesis.api.demo import load_scenarios

def test_load_scenarios_returns_the_catalog() -> None:
    scenarios = load_scenarios()
    ids = {s.id for s in scenarios}
    assert {"ssh-bruteforce", "syn-flood", "mqtt-flood", "benign", "honest-limitation"} <= ids
    for s in scenarios:
        assert s.episode_id and s.default_condition.startswith("C")
```

- [ ] **Step 3: Create the catalog** `config/demo_scenarios.yaml`, filling `episode_id` from Step 1 (example values shown; replace with the query's output):

```yaml
scenarios:
  - id: ssh-bruteforce
    title: "SSH brute-force on the honeypot"
    description: "An external host guesses SSH passwords against the honeypot."
    episode_id: ep-sshbrute-eval-001
    attack_family: ssh_brute_force
    default_condition: C1
    highlight: null
  - id: syn-flood
    title: "SYN flood on an IoT device"
    description: "A volumetric TCP SYN flood, seen in the network flows."
    episode_id: ep-syn-eval-001
    attack_family: syn_flood
    default_condition: C1
    highlight: null
  - id: mqtt-flood
    title: "MQTT publish flood on the broker"
    description: "A device floods the MQTT broker with PUBLISH messages."
    episode_id: ep-mflood-eval-001
    attack_family: mqtt_publish_flood
    default_condition: C1
    highlight: null
  - id: benign
    title: "A quiet window"
    description: "No attack present; the agent recommends monitoring, not action."
    episode_id: ep-benign-eval-001
    attack_family: benign
    default_condition: C1
    highlight: "No false alarm: the agent recommends no_action or monitor."
  - id: honest-limitation
    title: "Where the agent struggles"
    description: "The agent misclassifies or withholds; Baseline A classifies it correctly."
    episode_id: ep-honest-eval-001
    attack_family: null
    default_condition: C1
    highlight: "Toggle Brain to Baseline A (C7) — it gets the class right (H2/H4)."
```

- [ ] **Step 4: Implement the loader** in `thesis/api/demo.py`:

```python
"""Demo-simulator support: a curated scenario catalog and the replay event assembly (read-only
over the frozen run). No model call here (the live run lives in app.py). Recommend-only: nothing
acts on a testbed or network."""
from __future__ import annotations
from pathlib import Path
import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel

REPO_ROOT = Path(__file__).resolve().parents[2]
SCENARIOS_PATH = REPO_ROOT / "config" / "demo_scenarios.yaml"

class Scenario(BaseModel):
    id: str
    title: str
    description: str
    episode_id: str
    attack_family: str | None
    default_condition: str
    highlight: str | None

def load_scenarios(path: Path = SCENARIOS_PATH) -> list[Scenario]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [Scenario.model_validate(s) for s in data["scenarios"]]
```

- [ ] **Step 5: Run** `uv run pytest tests/test_demo.py -v` → PASS. **Commit** (`git add config/demo_scenarios.yaml thesis/api/demo.py tests/test_demo.py && git commit -m "Add demo scenario catalog and loader"`).

---

### Task 2: Labeled-alert index and bundle metadata loaders

**Files:**
- Modify: `thesis/api/demo.py`
- Modify: `tests/test_demo.py`

**Interfaces:**
- Produces:
  - `load_bundle_meta(eval_path=EVAL_PARQUET) -> dict[str, BundleMeta]` where `BundleMeta` has `bundle_id, device, window_start: datetime, window_end: datetime, label, episode_id, sources: list[str], alert_ids: list[str]`.
  - `AlertRow` (dataclass: `alert_id, source, ts: datetime, detector_label: str|None, detector_score: float|None, summary: str, alert_json: dict`).
  - `load_alert_index(dirs=ANNOTATED_DIRS) -> dict[str, AlertRow]` keyed by alert_id, from `data/bundles/_annotated/{flows,honeypot,mqtt}/*.parquet`.

- [ ] **Step 1: Write the failing test** (uses the real persisted data; skip if absent, like `test_eval_flow.py`):

```python
import pytest
from thesis.api.demo import EVAL_PARQUET, load_bundle_meta, load_alert_index

@pytest.mark.skipif(not EVAL_PARQUET.exists(), reason="bundle parquet not on disk")
def test_bundle_meta_and_alert_index_join() -> None:
    meta = load_bundle_meta()
    alerts = load_alert_index()
    b = next(iter(meta.values()))
    assert b.window_start <= b.window_end and b.alert_ids
    # every alert id a bundle cites resolves in the index
    assert any(aid in alerts for aid in b.alert_ids)
    a = alerts[next(aid for aid in b.alert_ids if aid in alerts)]
    assert a.ts is not None and a.summary
```

- [ ] **Step 2: Run** → FAIL (names undefined).

- [ ] **Step 3: Implement** in `thesis/api/demo.py`:

```python
import json
from dataclasses import dataclass
from datetime import datetime

EVAL_PARQUET = REPO_ROOT / "data" / "bundles" / "v1.0.0" / "eval.parquet"
ANNOTATED_DIRS = [REPO_ROOT / "data" / "bundles" / "_annotated" / s for s in ("flows", "honeypot", "mqtt")]

class BundleMeta(BaseModel):
    bundle_id: str
    device: str
    window_start: datetime
    window_end: datetime
    label: str
    episode_id: str | None
    sources: list[str]
    alert_ids: list[str]

@dataclass(frozen=True)
class AlertRow:
    alert_id: str
    source: str
    ts: datetime
    detector_label: str | None
    detector_score: float | None
    summary: str
    alert_json: dict

def load_bundle_meta(eval_path: Path = EVAL_PARQUET) -> dict[str, BundleMeta]:
    import pyarrow.parquet as pq
    out: dict[str, BundleMeta] = {}
    for r in pq.read_table(eval_path).to_pylist():
        out[str(r["bundle_id"])] = BundleMeta(
            bundle_id=str(r["bundle_id"]), device=str(r["device"]),
            window_start=r["window_start"], window_end=r["window_end"],
            label=str(r["label"]), episode_id=(str(r["episode_id"]) or None),
            sources=[str(s) for s in r["sources"]],
            alert_ids=[str(a) for a in r["alert_ids"]],
        )
    return out

def _alert_summary(source: str, detail: dict) -> str:
    if source == "flows":
        return f"flow {detail.get('src_ip')}:{detail.get('src_port')}->{detail.get('dst_ip')}:{detail.get('dst_port')} {detail.get('protocol')}"
    if source == "mqtt":
        return f"mqtt {detail.get('event')} topic={detail.get('topic')}"
    if source == "honeypot":
        return f"honeypot {detail.get('event')} session={detail.get('session_id')}"
    return source

def load_alert_index(dirs: list[Path] = ANNOTATED_DIRS) -> dict[str, AlertRow]:
    import pyarrow.parquet as pq
    out: dict[str, AlertRow] = {}
    for d in dirs:
        for f in sorted(d.glob("*.parquet")):
            for r in pq.read_table(f).to_pylist():
                aj = json.loads(r["alert_json"])
                out[str(r["alert_id"])] = AlertRow(
                    alert_id=str(r["alert_id"]), source=str(r["source"]), ts=r["ts"],
                    detector_label=aj.get("detector_label"), detector_score=aj.get("detector_score"),
                    summary=_alert_summary(str(r["source"]), aj.get("detail", {})),
                    alert_json=aj,
                )
    return out
```

- [ ] **Step 4: Run** `uv run pytest tests/test_demo.py -v` → PASS. **Commit** ("Load bundle metadata and the labeled-alert index for the demo").

---

### Task 3: Event assembly

**Files:**
- Modify: `thesis/api/demo.py`
- Modify: `tests/test_demo.py`

**Interfaces:**
- Consumes: Task 1 `Scenario`, Task 2 `BundleMeta`/`AlertRow`, existing `thesis.api.app._load_by_condition`, `_condition_labels`, `_verdict_from_row`, `_load_trace`.
- Produces:
  - `DemoEvent` (pydantic: `t: float`, `kind: Literal["alert","bundle_formed","reasoning","verdict","recommendation"]`, `bundle_id: str`, `payload: dict`).
  - `build_scenario_events(scenario, condition, *, meta, alerts, rows_by_bundle, call_log_path) -> list[DemoEvent]` — time-ordered, `t` = seconds from the episode window start.

- [ ] **Step 1: Write the failing tests** (pure, with small synthetic inputs — no real data):

```python
from datetime import UTC, datetime, timedelta
from thesis.api.demo import DemoEvent, Scenario, BundleMeta, AlertRow, build_scenario_events

T0 = datetime(2026, 1, 1, tzinfo=UTC)

def _meta(bid, start_s, end_s, alert_ids, episode="ep-x"):
    return BundleMeta(bundle_id=bid, device="d", window_start=T0+timedelta(seconds=start_s),
        window_end=T0+timedelta(seconds=end_s), label="syn_flood", episode_id=episode,
        sources=["flows"], alert_ids=alert_ids)

def _alert(aid, ts_s):
    return AlertRow(aid, "flows", T0+timedelta(seconds=ts_s), "syn_flood", 1.0, f"sum {aid}", {})

def _row(bid, emitted=True):
    return {"bundle_id": bid, "emitted": emitted, "incident_type": "syn_flood" if emitted else None,
        "confidence": 0.8 if emitted else None, "severity": "high" if emitted else None,
        "affected_device": "d" if emitted else None,
        "recommended_action": "rate_limit_source" if emitted else None,
        "evidence": ["a1"] if emitted else [], "config_hash": "h", "ground_truth": "syn_flood"}

def test_events_are_time_ordered_with_one_alert_each() -> None:
    meta = {"b1": _meta("b1", 0, 60, ["a1", "a2"])}
    alerts = {"a1": _alert("a1", 5), "a2": _alert("a2", 40)}
    scenario = Scenario(id="s", title="t", description="d", episode_id="ep-x",
        attack_family="syn_flood", default_condition="C1", highlight=None)
    events = build_scenario_events(scenario, "C1", meta=meta, alerts=alerts,
        rows_by_bundle={"b1": _row("b1")}, call_log_path=None)
    kinds = [e.kind for e in events]
    assert kinds.count("alert") == 2
    assert "bundle_formed" in kinds and "verdict" in kinds and "recommendation" in kinds
    assert [e.t for e in events] == sorted(e.t for e in events)  # ordered

def test_withheld_bundle_emits_bundle_formed_and_withheld_verdict() -> None:
    meta = {"b1": _meta("b1", 0, 60, ["a1"])}
    alerts = {"a1": _alert("a1", 5)}
    scenario = Scenario(id="s", title="t", description="d", episode_id="ep-x",
        attack_family=None, default_condition="C1", highlight=None)
    events = build_scenario_events(scenario, "C1", meta=meta, alerts=alerts,
        rows_by_bundle={"b1": _row("b1", emitted=False)}, call_log_path=None)
    verdict = next(e for e in events if e.kind == "verdict")
    assert verdict.payload["withheld"] is True
    assert any(e.kind == "bundle_formed" for e in events)
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** in `thesis/api/demo.py`:

```python
from typing import Literal

class DemoEvent(BaseModel):
    t: float
    kind: Literal["alert", "bundle_formed", "reasoning", "verdict", "recommendation"]
    bundle_id: str
    payload: dict

_REASON_GAP = 2.0  # seconds of synthetic spacing for the agent's three steps after a bundle forms

def build_scenario_events(scenario, condition, *, meta, alerts, rows_by_bundle, call_log_path):
    # episode bundles, by the scenario's episode
    bundles = sorted((m for m in meta.values() if m.episode_id == scenario.episode_id),
                     key=lambda m: m.window_start)
    if not bundles:
        return []
    t0 = bundles[0].window_start
    secs = lambda dt: (dt - t0).total_seconds()
    events: list[DemoEvent] = []
    for b in bundles:
        for aid in b.alert_ids:
            a = alerts.get(aid)
            if a is None:
                continue
            events.append(DemoEvent(t=secs(a.ts), kind="alert", bundle_id=b.bundle_id, payload={
                "alert_id": a.alert_id, "source": a.source, "detector_label": a.detector_label,
                "detector_score": a.detector_score, "summary": a.summary}))
        bt = secs(b.window_end)
        events.append(DemoEvent(t=bt, kind="bundle_formed", bundle_id=b.bundle_id, payload={
            "device": b.device, "sources": b.sources, "n_alerts": len(b.alert_ids),
            "ground_truth": b.label}))
        row = rows_by_bundle.get(b.bundle_id)
        if row is None:
            continue
        # reasoning steps (from the call log if available), paced after the bundle forms
        trace = []
        if call_log_path is not None:
            from thesis.api.app import _load_trace
            trace = _load_trace(call_log_path, b.bundle_id, str(row["config_hash"]))
        for i, step in enumerate(trace, start=1):
            events.append(DemoEvent(t=bt + i * _REASON_GAP, kind="reasoning", bundle_id=b.bundle_id,
                payload={"node": step["node"], "event": step["event"], "completion": step["completion"]}))
        vt = bt + (len(trace) + 1) * _REASON_GAP
        emitted = bool(row["emitted"]) and row["incident_type"] is not None
        events.append(DemoEvent(t=vt, kind="verdict", bundle_id=b.bundle_id, payload=(
            {"withheld": True} if not emitted else {
                "withheld": False, "incident_type": row["incident_type"], "severity": row["severity"],
                "affected_device": row["affected_device"], "confidence": row["confidence"]})))
        if emitted:
            events.append(DemoEvent(t=vt + _REASON_GAP, kind="recommendation", bundle_id=b.bundle_id,
                payload={"recommended_action": row["recommended_action"], "severity": row["severity"],
                         "evidence": list(row["evidence"] or [])}))
    return sorted(events, key=lambda e: e.t)
```

- [ ] **Step 4: Run** `uv run pytest tests/test_demo.py -v` → PASS. **Commit** ("Assemble the time-ordered demo event stream").

---

### Task 4: Demo scenario endpoints

**Files:**
- Modify: `thesis/api/app.py` (add endpoints + response models)
- Modify: `tests/test_api.py`

**Interfaces:**
- Consumes: Task 1–3 `load_scenarios`, `load_bundle_meta`, `load_alert_index`, `build_scenario_events`; existing `_load_by_condition`, `_condition_labels`, `_rows_for`.
- Produces: `GET /demo/scenarios -> list[Scenario]`; `GET /demo/scenarios/{scenario_id}?condition=C1 -> ScenarioEvents` where `ScenarioEvents` has `scenario: Scenario`, `condition: str`, `window_seconds: float`, `events: list[DemoEvent]`.

- [ ] **Step 1: Write the failing test** in `tests/test_api.py` (extend the fixture to include a demo scenario + its episode bundles; use a tmp catalog). Add a `demo_scenarios.yaml` tmp file and two episode bundles to the results fixture, then:

```python
def test_demo_scenarios_list_and_events(tmp_path: Path) -> None:
    client = _demo_client(tmp_path)  # new fixture: results with an ep-x episode + a catalog
    scenarios = client.get("/demo/scenarios").json()
    assert any(s["id"] == "demo-x" for s in scenarios)
    ev = client.get("/demo/scenarios/demo-x", params={"condition": "C1"}).json()
    assert ev["condition"] == "C1" and ev["window_seconds"] >= 0
    kinds = {e["kind"] for e in ev["events"]}
    assert {"bundle_formed", "verdict"} <= kinds
    assert client.get("/demo/scenarios/nope").status_code == 404
```

Write `_demo_client` modeled on `_client`: write a `demo_scenarios.yaml` (one scenario, `episode_id: ep-x`), results rows for two `ep-x` C1 bundles, and pass a `scenarios_path`, `eval_path`, `annotated_dirs` through to `create_app` (add these params, defaulting to the real paths). For alerts, write a tiny annotated parquet the loader can read, or inject a prebuilt alert index via a param — prefer adding `demo_alert_index`/`demo_bundle_meta` override params to `create_app` for testability.

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** in `thesis/api/app.py`: import the demo module; in `create_app` load the catalog, bundle meta and alert index once (guarded: if the parquet is absent, serve an empty catalog so the app still starts); add:

```python
from thesis.api import demo

class ScenarioEvents(BaseModel):
    scenario: demo.Scenario
    condition: str
    window_seconds: float
    events: list[demo.DemoEvent]

# inside create_app, after by_condition is built:
scenarios = {s.id: s for s in demo.load_scenarios(scenarios_path)} if scenarios_path.exists() else {}
try:
    bundle_meta = demo.load_bundle_meta(eval_path)
    alert_index = demo.load_alert_index(annotated_dirs)
except FileNotFoundError:
    bundle_meta, alert_index = {}, {}

@app.get("/demo/scenarios")
def list_scenarios() -> list[demo.Scenario]:
    return list(scenarios.values())

@app.get("/demo/scenarios/{scenario_id}")
def scenario_events(scenario_id: str, condition: str = DEFAULT_CONDITION) -> ScenarioEvents:
    scenario = scenarios.get(scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="unknown scenario")
    rows = _rows_for(condition)
    events = demo.build_scenario_events(scenario, condition, meta=bundle_meta, alerts=alert_index,
        rows_by_bundle=rows, call_log_path=call_log_path)
    window = max((e.t for e in events), default=0.0)
    return ScenarioEvents(scenario=scenario, condition=condition, window_seconds=window, events=events)
```

Add `scenarios_path`, `eval_path`, `annotated_dirs`, and optional `demo_bundle_meta`/`demo_alert_index` params to `create_app` (default to the real paths / `None`). Keep `post_decision` the only non-GET route (the § test still passes — `/demo/*` are GET).

- [ ] **Step 4: Run** `uv run pytest tests/test_api.py -v` → PASS. Run `uv run pre-commit run --all-files` → PASS. **Commit** ("Serve demo scenarios and their event streams"). Push, open the Phase 1 PR later after the frontend tasks.

---

### Task 5: Extract shared report/trace rendering

**Files:**
- Create: `frontend/src/components/ReportMarkdown.tsx`
- Create: `frontend/src/components/TraceSteps.tsx`
- Create: `frontend/src/lib/format.ts`
- Modify: `frontend/src/screens/IncidentDetail.tsx` (use the extracted pieces)

**Interfaces:**
- Produces: `ReportMarkdown({ markdown }: { markdown: string })`; `TraceSteps({ steps }: { steps: { event: string; completion: string }[] })`; `beautifyJson(text: string): string`.

- [ ] **Step 1: Create `lib/format.ts`** with `beautifyJson` (moved verbatim from `IncidentDetail.tsx`):

```ts
export function beautifyJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}
```

- [ ] **Step 2: Create `components/ReportMarkdown.tsx`** — move the `REPORT_MD` components map and the `<ReactMarkdown remarkPlugins={[remarkGfm]} components={REPORT_MD}>` wrapper out of `IncidentDetail.tsx` verbatim into a component that takes `markdown`.

- [ ] **Step 3: Create `components/TraceSteps.tsx`** — the numbered `<ol>` of reasoning steps (the STEP_TITLE map + `.sr-only` raw event + `<pre>{beautifyJson(step.completion)}</pre>`), moved from `IncidentDetail.tsx`, taking `steps`.

- [ ] **Step 4: Update `IncidentDetail.tsx`** to import and use `ReportMarkdown`, `TraceSteps`, and `beautifyJson` from the new modules; delete the now-duplicated inline code.

- [ ] **Step 5: Run** `npm run typecheck && npm test` → the existing `IncidentDetail.test.tsx` still passes (same DOM). **Commit** ("Extract shared report and trace rendering for reuse").

---

### Task 6: Typed demo API client

**Files:**
- Create: `frontend/src/api/demo.ts`
- Regenerate: `frontend/src/api/types.ts` (`npm run gen:types`)

**Interfaces:**
- Produces: `Scenario`, `DemoEvent`, `ScenarioEvents` type aliases; `getScenarios(): Promise<Scenario[]>`, `getScenarioEvents(id, condition): Promise<ScenarioEvents>`, `liveTraceUrl(bundleId, condition): string`.

- [ ] **Step 1: Run** `npm run gen:types` (after Task 4 is merged/available) so the demo schemas appear in `types.ts`.
- [ ] **Step 2: Create `api/demo.ts`**:

```ts
import type { components } from "./types";
export type Scenario = components["schemas"]["Scenario"];
export type DemoEvent = components["schemas"]["DemoEvent"];
export type ScenarioEvents = components["schemas"]["ScenarioEvents"];
import { BASE } from "./client";

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`${path} failed: ${res.status}`);
  return (await res.json()) as T;
}
export const getScenarios = (): Promise<Scenario[]> => getJson<Scenario[]>("/demo/scenarios");
export const getScenarioEvents = (id: string, condition: string): Promise<ScenarioEvents> =>
  getJson<ScenarioEvents>(`/demo/scenarios/${encodeURIComponent(id)}?condition=${encodeURIComponent(condition)}`);
export const liveTraceUrl = (bundleId: string, condition: string): string =>
  `${BASE}/demo/live/${encodeURIComponent(bundleId)}/trace?condition=${encodeURIComponent(condition)}`;
```

Export `BASE` from `client.ts` if not already exported.

- [ ] **Step 3:** `npm run typecheck` → PASS. **Commit** ("Add typed demo API client").

---

### Task 7: The replay clock hook

**Files:**
- Create: `frontend/src/hooks/useReplayClock.ts`
- Create: `frontend/src/hooks/useReplayClock.test.ts`

**Interfaces:**
- Produces: `useReplayClock(events: DemoEvent[], opts?: { speed?: number; maxGap?: number }) -> { nowT: number; playing: boolean; visible: DemoEvent[]; duration: number; play(): void; pause(): void; toggle(): void; seek(t: number): void; step(dir: 1 | -1): void; restart(): void; setSpeed(x: number): void }`.
- The clock maps event `t` to a **compressed timeline**: idle gaps longer than `maxGap` (default 2s) are shrunk to `maxGap`, so playback never stalls. `visible` are events whose compressed time ≤ `nowT`.

- [ ] **Step 1: Write failing tests** (vitest, fake timers):

```ts
import { renderHook, act } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { useReplayClock } from "./useReplayClock";

const ev = (t: number) => ({ t, kind: "alert", bundle_id: "b", payload: {} }) as any;

beforeEach(() => vi.useFakeTimers());
afterEach(() => vi.useRealTimers());

describe("useReplayClock", () => {
  it("reveals events up to nowT and supports seek/step", () => {
    const { result } = renderHook(() => useReplayClock([ev(0), ev(10), ev(100)], { maxGap: 2 }));
    expect(result.current.visible.length).toBe(1);        // t=0 visible at start
    act(() => result.current.step(1));
    expect(result.current.visible.length).toBe(2);        // step to next event
    act(() => result.current.seek(result.current.duration));
    expect(result.current.visible.length).toBe(3);        // seek to end reveals all
  });

  it("compresses idle gaps so duration is bounded", () => {
    const { result } = renderHook(() => useReplayClock([ev(0), ev(1000)], { maxGap: 2 }));
    expect(result.current.duration).toBeLessThanOrEqual(2); // 1000s gap compressed to <=2s
  });
});
```

- [ ] **Step 2: Run** → FAIL.

- [ ] **Step 3: Implement** `useReplayClock.ts`. Precompute a compressed time `ct[i]` for each event: `ct[0]=0`, `ct[i]=ct[i-1]+min(t[i]-t[i-1], maxGap)`. `duration = last ct`. Advance `nowT` via `requestAnimationFrame` by `dt*speed` while `playing`; `visible = events.filter((_,i)=>ct[i] <= nowT)`. `step(dir)` sets `nowT` to the next/prev `ct`. `seek` clamps to `[0,duration]`. Use `useRef` for the rAF handle and last-timestamp; `useState` for `nowT`, `playing`, `speed`. Stop the rAF at `duration`.

```ts
import { useEffect, useMemo, useRef, useState } from "react";
import type { DemoEvent } from "../api/demo";

export function useReplayClock(events: DemoEvent[], opts: { speed?: number; maxGap?: number } = {}) {
  const maxGap = opts.maxGap ?? 2;
  const ct = useMemo(() => {
    const out: number[] = [];
    events.forEach((e, i) => {
      out[i] = i === 0 ? 0 : out[i - 1] + Math.min(Math.max(e.t - events[i - 1].t, 0), maxGap);
    });
    return out;
  }, [events, maxGap]);
  const duration = ct.length ? ct[ct.length - 1] : 0;
  const [nowT, setNowT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(opts.speed ?? 4);
  const raf = useRef<number | null>(null);
  const last = useRef<number | null>(null);

  useEffect(() => {
    if (!playing) return;
    const tick = (ts: number) => {
      if (last.current != null) {
        setNowT((t) => {
          const next = t + ((ts - last.current!) / 1000) * speed;
          if (next >= duration) { setPlaying(false); return duration; }
          return next;
        });
      }
      last.current = ts;
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => { if (raf.current) cancelAnimationFrame(raf.current); last.current = null; };
  }, [playing, speed, duration]);

  const visible = useMemo(() => events.filter((_, i) => ct[i] <= nowT + 1e-9), [events, ct, nowT]);
  const seek = (t: number) => setNowT(Math.max(0, Math.min(duration, t)));
  const step = (dir: 1 | -1) => {
    const future = dir === 1 ? ct.filter((c) => c > nowT + 1e-9) : ct.filter((c) => c < nowT - 1e-9);
    if (future.length) seek(dir === 1 ? Math.min(...future) : Math.max(...future));
  };
  return {
    nowT, playing, visible, duration, speed,
    play: () => setPlaying(true), pause: () => setPlaying(false),
    toggle: () => setPlaying((p) => !p), seek, step,
    restart: () => { setNowT(0); setPlaying(true); }, setSpeed,
  };
}
```

- [ ] **Step 4: Run** `npm test -- useReplayClock` → PASS. **Commit** ("Add the replay clock hook").

---

### Task 8: Pipeline strip

**Files:**
- Create: `frontend/src/screens/demo/PipelineStrip.tsx`

**Interfaces:**
- Produces: `PipelineStrip({ activeStage }: { activeStage: Stage })` where `Stage = "telemetry"|"detectors"|"bundle"|"evidence"|"classify"|"recommend"|"validator"|"recommendation"|"human"|null`.

- [ ] **Step 1: Implement** a horizontal row of labelled nodes; the `activeStage` node gets `bg-accent-soft text-accent` + a pulse (`animate-pulse` guarded by reduced-motion), others `text-muted`. Connectors are `→`. Use Tailwind + tokens; no new dep. (Map the agent's three nodes under an "Agent" group.)
- [ ] **Step 2:** `npm run typecheck` → PASS. **Commit** ("Add the pipeline strip").

(No test beyond typecheck — purely presentational; its behavior is exercised via Task 12's view test asserting the active stage class.)

---

### Task 9: Telemetry feed and incident feed

**Files:**
- Create: `frontend/src/screens/demo/TelemetryFeed.tsx`
- Create: `frontend/src/screens/demo/IncidentFeed.tsx`
- Create: `frontend/src/screens/demo/IncidentFeed.test.tsx`

**Interfaces:**
- `TelemetryFeed({ alerts }: { alerts: DemoEvent[] })` — the `alert`-kind visible events, newest first: source chip, detector label/score, mono summary (as **text**).
- `IncidentFeed({ incidents, focusedId, onFocus })` where `incidents: { bundle_id, device, status, verdict? , recommendation? }[]` derived by the view from visible `bundle_formed`/`verdict`/`recommendation` events.

- [ ] **Step 1: Write failing test** for `IncidentFeed`: renders a card per incident, clicking calls `onFocus(bundle_id)`, an attacker-markup device/summary renders as text (no element). Assert `screen.getByText("<img src=x>")` present and `document.querySelector("img")` null.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** both. Cards use `Panel`/`SeverityBadge`/`cn` from the existing UI kit; all dynamic text in `{}` (React-escaped). Status derives from the latest event seen for that bundle ("detecting" → "reasoning" → "recommended" → "withheld").
- [ ] **Step 4: Run** `npm test -- IncidentFeed` → PASS. **Commit** ("Add the telemetry and incident feeds").

---

### Task 10: Incident lifecycle (drill-in)

**Files:**
- Create: `frontend/src/screens/demo/IncidentLifecycle.tsx`

**Interfaces:**
- `IncidentLifecycle({ bundleId, condition, events })` — builds, from the scenario `events` for this `bundleId`: the alerts list, the reasoning `TraceSteps` (from `reasoning` events revealed so far), the verdict header, the recommendation, and the report (fetched via existing `getReport(bundleId)` → `ReportMarkdown`). Reuses `ReportMarkdown`, `TraceSteps`, `SeverityBadge`.

- [ ] **Step 1: Implement** by composing the shared components; fetch the report with the existing client; render withheld verdicts (`payload.withheld`) as "Withheld". Accept/Reject reuses the existing `Recommendation` component wired to the demo's condition. All attacker text via the escaped path.
- [ ] **Step 2:** `npm run typecheck && npm test` → PASS. **Commit** ("Add the incident lifecycle drill-in").

---

### Task 11: Transport bar, scenario picker, brain toggle

**Files:**
- Create: `frontend/src/screens/demo/TransportBar.tsx`
- Create: `frontend/src/screens/demo/ScenarioPicker.tsx`

**Interfaces:**
- `TransportBar({ playing, nowT, duration, speed, onToggle, onSeek, onStep, onRestart, onSpeed })` — play/pause button, a range `<input type="range">` bound to `nowT`/`duration` calling `onSeek`, a speed `Select` (1/2/4/8), step buttons, restart.
- `ScenarioPicker({ scenarios, scenarioId, onScenario, condition, onCondition })` — a `Select` of scenarios and a "Brain" `Select` (C1 / C6 / C7 with human labels).

- [ ] **Step 1: Implement** both with the existing `Button`/`Select`. Range input styled with Tailwind.
- [ ] **Step 2:** `npm run typecheck` → PASS. **Commit** ("Add the transport bar and scenario picker").

---

### Task 12: Demo view + navigation

**Files:**
- Create: `frontend/src/screens/Demo.tsx`
- Create: `frontend/src/screens/Demo.test.tsx`
- Modify: `frontend/src/App.tsx` (add the "Demo" nav item + view)

**Interfaces:**
- Consumes: Tasks 6–11.
- `Demo()` — owns scenario/condition state, fetches `getScenarioEvents`, runs `useReplayClock(events)`, derives the incident list + `activeStage` from `clock.visible`, and lays out PipelineStrip / TelemetryFeed / IncidentFeed / IncidentLifecycle / TransportBar. Keyboard: Space = toggle, ←/→ = step (added in Task 16; leave a `// TODO keyboard` seam here is NOT allowed — wire the handlers now with a `useEffect` keydown listener).

- [ ] **Step 1: Write failing test** `Demo.test.tsx`: mock `api/demo`, return a scenario + an event list with one `bundle_formed` + `verdict`; render `<Demo/>`, pick the scenario, assert an incident card appears after seeking to the end (drive the clock by clicking the transport's end or calling seek via the range input), and that the pipeline strip shows an active stage. Mock `getReport`.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `Demo.tsx` and wire the keydown `useEffect` (Space/←/→). Derive `incidents` by folding `clock.visible`: a map bundle_id → latest status/verdict/recommendation. `activeStage` from the newest visible event's kind. Focus the newest incident unless the user clicked one.
- [ ] **Step 4: Add nav** in `App.tsx`: extend the `View` union with `{ name: "demo" }`, add a `NavItem` (icon `Activity` or `PlayCircle` from lucide), render `<Demo/>` when `current === "demo"`.
- [ ] **Step 5: Run** `npm run typecheck && npm test && npm run build` → PASS. **Commit** ("Add the demo replay view and navigation").
- [ ] **Step 6:** Open the **Phase 1 PR** (`demo-simulator` → main); ensure CI green; self-merge. The replay demo is now complete and demoable from frozen data.

---

## PHASE 2 — Live run, scoreboard, presenter mode

### Task 13: Bundle reconstruction + live-run endpoint

**Files:**
- Modify: `thesis/api/demo.py` (bundle reconstruction)
- Modify: `thesis/api/app.py` (SSE live endpoint)
- Modify: `tests/test_demo.py`, `tests/test_api.py`

**Interfaces:**
- Produces: `reconstruct_bundle(bundle_id, *, meta, alerts) -> Bundle` (uses `Alert.model_validate(alert_row.alert_json)` for each cited alert + `BundleMeta` for the window/device/sources); `GET /demo/live/{bundle_id}/trace?condition=C1` (SSE) streaming `evidence`/`classify`/`recommend` completions, then a `verdict` event and a `cost` event; `503` if the hosted env is not configured.

- [ ] **Step 1: Write failing test** (`tests/test_demo.py`): `reconstruct_bundle` returns a `Bundle` whose `.bundle_id` and `.alerts` (tuple of `Alert`) match the metadata; alert count equals `len(alert_ids)` present in the index.
- [ ] **Step 2: Run** → FAIL.
- [ ] **Step 3: Implement** `reconstruct_bundle` in `demo.py`:

```python
from thesis.assemble.bundles import Bundle
from thesis.schema.alert import Alert

def reconstruct_bundle(bundle_id, *, meta, alerts) -> Bundle:
    m = meta[bundle_id]
    objs = tuple(Alert.model_validate(alerts[a].alert_json) for a in m.alert_ids if a in alerts)
    return Bundle(bundle_id=m.bundle_id, device=m.device, window_start=m.window_start,
        window_end=m.window_end, label=m.label, episode_id=m.episode_id,
        sources=tuple(m.sources), alerts=objs)
```

- [ ] **Step 4: Write failing test** (`tests/test_api.py`): with no hosted env, `GET /demo/live/{bid}/trace` returns 503.
- [ ] **Step 5: Implement** the endpoint in `app.py`. Gate on `os.environ.get("LLM_BASE_URL")`; build the hosted `LLMClient.from_env(...)` lazily; run the real graph and stream:

```python
@app.get("/demo/live/{bundle_id}/trace")
def live_trace(bundle_id: str, condition: str = DEFAULT_CONDITION) -> StreamingResponse:
    if not os.environ.get("LLM_BASE_URL"):
        raise HTTPException(status_code=503, detail="hosted model not configured")
    if bundle_id not in bundle_meta:
        raise HTTPException(status_code=404, detail="unknown incident")
    # run the real three-node graph; stream each node completion, then verdict + cost.
    # IMPLEMENTATION: reuse run_graph with a Completer that tees completions into the SSE queue;
    # never write results. Mark events: evidence|classify|recommend, then verdict, then cost.
    ...
```

Because `run_graph` logs calls but returns only the final `GraphTrace`, stream by wrapping the client: a small `Completer` that calls the real client and `yield`s each node's completion as it is produced (the three nodes run in order). Pace is natural (real latency). The `cost` event sums `tokens_in/out` from the `GraphTrace`/call counter and multiplies by the ADR-0001 price. Keep it under the one-bundle, three-call contract.

> This task has genuine integration complexity (teeing completions out of `run_graph` over SSE). If a clean tee is not available, the fallback is: run the graph to completion, then stream the three recorded completions from the fresh call-log lines for this bundle in order, followed by verdict + cost — still a real live run, just streamed after it finishes. Choose the fallback if the tee needs changes to `thesis/agent/graph.py` (out of scope).

- [ ] **Step 6: Run** `uv run pytest tests/test_demo.py tests/test_api.py -v` and `uv run pre-commit run --all-files` → PASS. **Commit** ("Add the live-run bundle reconstruction and SSE endpoint").

---

### Task 14: Live-run button

**Files:**
- Create: `frontend/src/screens/demo/LiveRunButton.tsx`
- Modify: `frontend/src/screens/demo/IncidentLifecycle.tsx` (mount the button)

**Interfaces:**
- `LiveRunButton({ bundleId, condition })` — a confirm, then opens `EventSource(liveTraceUrl(...))`, streams steps into a labelled "LIVE · <model>" panel, shows elapsed time and the `cost` payload; on 503 the button is disabled with a tooltip "hosted model not configured" (probe with a `HEAD`/`GET` once on mount, or disable unless a prop says configured).

- [ ] **Step 1: Implement** reusing the `EventSource` pattern from `IncidentDetail` and `TraceSteps` for rendering; the panel is clearly badged LIVE; nothing is persisted.
- [ ] **Step 2:** `npm run typecheck && npm test` → PASS. **Commit** ("Add the live-run button").

---

### Task 15: Scoreboard

**Files:**
- Create: `frontend/src/screens/demo/Scoreboard.tsx`
- Modify: `frontend/src/screens/Demo.tsx` (mount it)

**Interfaces:**
- `Scoreboard({ events }: { events: DemoEvent[] })` — tallies from the visible events: alerts, incidents (`bundle_formed`), recommended (by action), withheld. Pure derivation; updates live as the clock advances.

- [ ] **Step 1: Write failing test**: given a visible-events array, renders the right counts.
- [ ] **Step 2: Run** → FAIL. **Step 3: Implement** (a small `useMemo` reducer + stat chips). **Step 4: Run** → PASS. **Commit** ("Add the demo scoreboard").

---

### Task 16: Presenter mode + keyboard shortcuts

**Files:**
- Modify: `frontend/src/screens/Demo.tsx`
- Modify: `frontend/src/App.tsx` (optional: hide sidebar in presenter mode)

**Interfaces:**
- A `presenter` boolean in `Demo` toggled by a button and the `p` key: enlarges type (a `text-lg`/scale class on the root) and hides chrome. Keyboard handlers (Space/←/→) were wired in Task 12; add `p`.

- [ ] **Step 1: Implement** the toggle + `p` handler; when on, add a `presenter` class and hide the sidebar (lift a prop to `App`, or use a context). Respect reduced-motion.
- [ ] **Step 2: Run** `npm run typecheck && npm test && npm run build` → PASS. **Commit** ("Add presenter mode and keyboard shortcuts").
- [ ] **Step 3:** Open the **Phase 2 PR** (`demo-simulator-live` → main); CI green; self-merge.

---

## Self-review notes

- **Spec coverage:** pipeline strip (T8), scenarios/catalog (T1), replay clock + transport (T7,T11), feed + drill-in (T9,T10,T12), Brain toggle (T11), backend endpoints + assembly (T1–T4), fast bundle loading from parquet (T2,T13), live run (T13,T14), scoreboard (T15), presenter mode (T16), zero new deps (Global Constraints). All spec sections map to a task.
- **Review Focus:** withheld (T3/T10), parse-failure skip (T3), idle-gap compression (T7), live 503 (T13/T14), attacker-text-as-inert (T9/T10) — each pinned to a test in its owning task.
- **Known integration risk:** Task 13's SSE tee out of `run_graph` — the task names a concrete fallback that needs no change to the frozen graph, so the live run is deliverable either way.
