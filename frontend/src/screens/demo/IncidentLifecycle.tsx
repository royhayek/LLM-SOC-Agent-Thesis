// The drill-in for one incident during the replay: the alerts that fed it, the reasoning revealed
// so far, the verdict, the report, and the recommendation + human decision. Reuses the shared
// report/trace rendering and the existing Recommendation component; `events` are the visible events
// for this bundle, so the drill-in reveals in step with the clock.
import { useEffect, useState } from "react";

import { getIncident, getReport, type Incident } from "../../api/client";
import type { DemoEvent } from "../../api/demo";
import { ReportMarkdown } from "../../components/ReportMarkdown";
import { TraceSteps } from "../../components/TraceSteps";
import { Panel, PanelHeader } from "../../components/ui/Panel";
import { SeverityBadge } from "../../components/ui/SeverityBadge";
import Recommendation from "../Recommendation";

export function IncidentLifecycle({
  bundleId,
  condition,
  events,
}: {
  bundleId: string;
  condition: string;
  events: DemoEvent[];
}) {
  const [incident, setIncident] = useState<Incident | null>(null);
  const [report, setReport] = useState("");

  useEffect(() => {
    let active = true;
    setIncident(null);
    setReport("");
    getIncident(bundleId, condition)
      .then((i) => active && setIncident(i))
      .catch(() => undefined);
    getReport(bundleId)
      .then((r) => active && setReport(r))
      .catch(() => undefined);
    return () => {
      active = false;
    };
  }, [bundleId, condition]);

  const mine = events.filter((e) => e.bundle_id === bundleId);
  const alerts = mine.filter((e) => e.kind === "alert");
  const steps = mine
    .filter((e) => e.kind === "reasoning")
    .map((e) => ({ event: String(e.payload.event), completion: String(e.payload.completion) }));
  const verdict = mine.find((e) => e.kind === "verdict");
  const recommended = mine.find((e) => e.kind === "recommendation");
  const withheld = verdict ? Boolean(verdict.payload.withheld) : false;

  return (
    <div className="space-y-4">
      <Panel className="p-4">
        <div className="font-mono text-xs text-muted">{bundleId}</div>
        <div className="mt-1 flex flex-wrap items-center gap-3">
          <h3 className="text-lg font-semibold tracking-tight">
            {verdict && !withheld ? String(verdict.payload.incident_type) : "Withheld"}
          </h3>
          {verdict && !withheld && (
            <SeverityBadge severity={String(verdict.payload.severity)} />
          )}
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Alerts" aside={<span className="text-xs text-muted">as detected</span>} />
        <div className="space-y-1 p-3">
          {alerts.length === 0 && <p className="text-sm text-muted">No alerts yet.</p>}
          {alerts.map((a, i) => (
            <div
              key={`${String(a.payload.alert_id)}-${i}`}
              className="rounded border border-line bg-panel-2 px-2.5 py-1.5 font-mono text-xs break-all text-text/80"
            >
              {String(a.payload.source)} · {String(a.payload.summary)}
            </div>
          ))}
        </div>
      </Panel>

      <Panel>
        <PanelHeader title="Reasoning" aside={<span className="text-xs text-muted">replayed</span>} />
        <div className="p-3">
          {steps.length === 0 ? (
            <p className="text-sm text-muted">The agent has not reasoned about this yet.</p>
          ) : (
            <TraceSteps steps={steps} />
          )}
        </div>
      </Panel>

      {report && (
        <Panel>
          <PanelHeader title="Report" />
          <div className="p-4">
            <ReportMarkdown markdown={report} />
          </div>
        </Panel>
      )}

      {recommended && incident && <Recommendation incident={incident} />}
    </div>
  );
}
