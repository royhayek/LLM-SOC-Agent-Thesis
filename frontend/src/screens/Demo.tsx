// The demo simulator: replay a captured attack episode end to end. A virtual clock reveals the
// scenario's events over time, driving the pipeline strip, the telemetry feed, the incident feed and
// the drill-in. All from frozen data (the optional live run is added in Phase 2). Recommend-only.
import { Maximize2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import type { DemoEvent, Scenario, ScenarioEvents } from "../api/demo";
import { getScenarioEvents, getScenarios } from "../api/demo";
import { Button } from "../components/ui/Button";
import { Panel, PanelHeader } from "../components/ui/Panel";
import { useReplayClock } from "../hooks/useReplayClock";
import { cn } from "../lib/utils";
import { IncidentFeed, type DemoIncident } from "./demo/IncidentFeed";
import { IncidentLifecycle } from "./demo/IncidentLifecycle";
import { PipelineStrip, type Stage } from "./demo/PipelineStrip";
import { ScenarioPicker } from "./demo/ScenarioPicker";
import { Scoreboard } from "./demo/Scoreboard";
import { TelemetryFeed } from "./demo/TelemetryFeed";
import { TransportBar } from "./demo/TransportBar";

function stageOf(e: DemoEvent | undefined): Stage {
  if (!e) return null;
  if (e.kind === "alert") return "telemetry";
  if (e.kind === "bundle_formed") return "bundle";
  if (e.kind === "reasoning") {
    const ev = String(e.payload.event);
    return ev === "evidence" ? "evidence" : ev === "classify" ? "classify" : "recommend";
  }
  if (e.kind === "verdict") return "validator";
  return "recommendation";
}

function deriveIncidents(visible: DemoEvent[]): DemoIncident[] {
  const map = new Map<string, DemoIncident>();
  const order: string[] = [];
  for (const e of visible) {
    if (e.kind === "bundle_formed" && !map.has(e.bundle_id)) {
      map.set(e.bundle_id, {
        bundle_id: e.bundle_id,
        device: String(e.payload.device ?? ""),
        status: "detecting",
      });
      order.push(e.bundle_id);
    }
    const inc = map.get(e.bundle_id);
    if (!inc) continue; // alerts before the bundle forms show only in the telemetry feed
    if (e.kind === "reasoning") inc.status = "reasoning";
    if (e.kind === "verdict") {
      if (e.payload.withheld) {
        inc.status = "withheld";
      } else {
        inc.incident_type = String(e.payload.incident_type);
        inc.severity = String(e.payload.severity);
      }
    }
    if (e.kind === "recommendation") {
      inc.recommended_action = String(e.payload.recommended_action);
      inc.status = "recommended";
    }
  }
  return order.map((id) => map.get(id)!);
}

export default function Demo({ onPresenter }: { onPresenter?: (on: boolean) => void } = {}) {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [scenarioId, setScenarioId] = useState("");
  const [condition, setCondition] = useState("C1");
  const [data, setData] = useState<ScenarioEvents | null>(null);
  const [clickedId, setClickedId] = useState<string | null>(null);
  const [presenter, setPresenter] = useState(false);

  const togglePresenter = () =>
    setPresenter((p) => {
      onPresenter?.(!p);
      return !p;
    });

  useEffect(() => {
    getScenarios()
      .then((s) => {
        if (s.length === 0) return;
        setScenarios(s);
        setScenarioId(s[0].id);
        setCondition(s[0].default_condition);
      })
      .catch(() => undefined);
  }, []);

  useEffect(() => {
    if (!scenarioId) return;
    let active = true;
    setData(null);
    setClickedId(null);
    getScenarioEvents(scenarioId, condition)
      .then((d) => active && setData(d))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [scenarioId, condition]);

  const events = useMemo(() => data?.events ?? [], [data]);
  const clock = useReplayClock(events);
  const visible = clock.visible;

  // keyboard: space = play/pause, arrows = step
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) return;
      if (e.code === "Space") {
        e.preventDefault();
        clock.toggle();
      } else if (e.code === "ArrowRight") {
        clock.step(1);
      } else if (e.code === "ArrowLeft") {
        clock.step(-1);
      } else if (e.code === "KeyP") {
        togglePresenter();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clock]);

  const incidents = deriveIncidents(visible);
  const activeStage = stageOf(visible[visible.length - 1]);
  const alerts = visible.filter((e) => e.kind === "alert");
  const focusedId = clickedId ?? (incidents.length ? incidents[incidents.length - 1].bundle_id : null);
  const scenario = scenarios.find((s) => s.id === scenarioId);

  return (
    <section
      className={cn(
        "mx-auto flex h-full max-w-7xl flex-col gap-4",
        presenter && "[zoom:1.15]",
      )}
    >
      <Panel className="p-3">
        <PipelineStrip activeStage={activeStage} />
      </Panel>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <ScenarioPicker
          scenarios={scenarios}
          scenarioId={scenarioId}
          onScenario={setScenarioId}
          condition={condition}
          onCondition={setCondition}
        />
        <div className="flex items-center gap-3">
          <Scoreboard events={visible} />
          <Button
            variant="outline"
            size="sm"
            aria-label="presenter mode"
            title="Presenter mode (p)"
            onClick={togglePresenter}
          >
            <Maximize2 className="h-4 w-4" />
            Presenter
          </Button>
        </div>
      </div>

      {scenario?.highlight && (
        <p className="rounded-md border border-accent/30 bg-accent-soft px-3 py-2 text-sm text-text">
          {scenario.highlight}
        </p>
      )}

      <div className="grid min-h-0 flex-1 grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.3fr)]">
        <Panel className="flex min-h-0 flex-col">
          <PanelHeader title="Telemetry" aside={<span className="text-xs text-muted">live feed</span>} />
          <div className="min-h-0 flex-1 overflow-auto p-3">
            <TelemetryFeed alerts={alerts} />
          </div>
        </Panel>

        <div className="flex min-h-0 flex-col gap-4">
          <Panel className="flex min-h-0 flex-col">
            <PanelHeader title="Incidents" />
            <div className="min-h-0 flex-1 overflow-auto p-3">
              <IncidentFeed incidents={incidents} focusedId={focusedId} onFocus={setClickedId} />
            </div>
          </Panel>
          {focusedId && (
            <div className="min-h-0 flex-1 overflow-auto">
              <IncidentLifecycle
                bundleId={focusedId}
                condition={condition}
                events={visible.filter((e) => e.bundle_id === focusedId)}
              />
            </div>
          )}
        </div>
      </div>

      <Panel className="p-3">
        <TransportBar
          playing={clock.playing}
          nowT={clock.nowT}
          duration={clock.duration}
          speed={clock.speed}
          onToggle={clock.toggle}
          onSeek={clock.seek}
          onStep={clock.step}
          onRestart={clock.restart}
          onSpeed={clock.setSpeed}
        />
      </Panel>
    </section>
  );
}
