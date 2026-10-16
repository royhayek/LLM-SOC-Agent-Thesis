// E10-05: the incident detail — the E7-08 report, the evidence, and the reasoning trace streamed
// over SSE. All dynamic content is rendered as text (React escapes it), never as HTML: attacker
// text in a bundle must not become markup in a security tool (ticket gotcha).
import { useEffect, useState } from "react";

import { getIncident, getReport, traceUrl, type Incident } from "../api/client";
import Recommendation from "./Recommendation";

interface TraceStep {
  event: string;
  completion: string;
}

export default function IncidentDetail(props: {
  bundleId: string;
  condition: string;
  onBack: () => void;
}) {
  const { bundleId, condition, onBack } = props;
  const [incident, setIncident] = useState<Incident | null>(null);
  const [report, setReport] = useState("");
  const [trace, setTrace] = useState<TraceStep[]>([]);

  useEffect(() => {
    let active = true;
    getIncident(bundleId, condition).then((i) => active && setIncident(i));
    getReport(bundleId).then((r) => active && setReport(r));
    return () => {
      active = false;
    };
  }, [bundleId, condition]);

  useEffect(() => {
    if (typeof EventSource === "undefined") return;
    setTrace([]);
    const source = new EventSource(traceUrl(bundleId, condition));
    const add = (e: MessageEvent) => {
      const step = JSON.parse(e.data) as { event: string; completion: string };
      setTrace((prev) => [...prev, { event: step.event, completion: step.completion }]);
    };
    for (const name of ["evidence", "classify", "recommend"]) {
      source.addEventListener(name, add as EventListener);
    }
    source.onerror = () => source.close(); // the stream closes after the three steps
    return () => source.close();
  }, [bundleId, condition]);

  if (!incident) return <p>Loading…</p>;

  return (
    <section>
      <button type="button" onClick={onBack}>
        ← Back to incidents
      </button>
      <h2>
        {incident.bundle_id} <small>({incident.condition})</small>
      </h2>

      <h3>Report</h3>
      {report ? <pre>{report}</pre> : <p>No report for this incident.</p>}

      <h3>Evidence</h3>
      {incident.verdict && incident.verdict.evidence.length > 0 ? (
        <ul>
          {incident.verdict.evidence.map((alertId) => (
            <li key={alertId}>{alertId}</li>
          ))}
        </ul>
      ) : (
        <p>No evidence cited.</p>
      )}

      <h3>Reasoning trace</h3>
      {trace.length === 0 ? (
        <p>No recorded trace.</p>
      ) : (
        <ol>
          {trace.map((step) => (
            <li key={step.event}>
              <strong>{step.event}</strong>
              <pre>{step.completion}</pre>
            </li>
          ))}
        </ol>
      )}

      <Recommendation incident={incident} />
    </section>
  );
}
