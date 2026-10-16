// E10-05: the incident detail — the E7-08 report, the evidence, and the reasoning trace streamed
// over SSE. All dynamic content is rendered as text (React escapes it), never as HTML: attacker
// text in a bundle must not become markup in a security tool (ticket gotcha). The report is rendered
// as Markdown with react-markdown (ADR-0014): it emits React elements and never raw HTML (no
// rehype-raw), so an attacker's `<img onerror>` in the report shows as inert text, not an element.
import { ArrowLeft, Cpu } from "lucide-react";
import { useEffect, useState } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import { getIncident, getReport, traceUrl, type Incident } from "../api/client";
import { Panel, PanelHeader } from "../components/ui/Panel";
import { SeverityBadge } from "../components/ui/SeverityBadge";
import { Button } from "../components/ui/Button";
import Recommendation from "./Recommendation";

interface TraceStep {
  event: string;
  completion: string;
}

const STEP_TITLE: Record<string, string> = {
  evidence: "Evidence analysis",
  classify: "Classification",
  recommend: "Recommendation",
};

// Pretty-print a reasoning-trace completion when it is JSON (the node outputs are), else leave it.
function beautifyJson(text: string): string {
  try {
    return JSON.stringify(JSON.parse(text), null, 2);
  } catch {
    return text;
  }
}

// Tailwind-styled renderers for the report Markdown, to match the console. `node` (the hast node)
// is pulled out of each so it is not spread onto the DOM element.
const REPORT_MD: Components = {
  h1: ({ node: _n, ...p }) => <h1 className="mb-2 text-base font-semibold tracking-tight" {...p} />,
  h2: ({ node: _n, ...p }) => (
    <h2 className="mt-4 mb-1.5 text-sm font-semibold tracking-tight" {...p} />
  ),
  h3: ({ node: _n, ...p }) => <h3 className="mt-3 mb-1 text-sm font-medium" {...p} />,
  p: ({ node: _n, ...p }) => <p className="my-2 text-sm leading-relaxed text-text/90" {...p} />,
  ul: ({ node: _n, ...p }) => (
    <ul className="my-2 list-disc space-y-1 pl-5 text-sm text-text/90" {...p} />
  ),
  ol: ({ node: _n, ...p }) => (
    <ol className="my-2 list-decimal space-y-1 pl-5 text-sm text-text/90" {...p} />
  ),
  li: ({ node: _n, ...p }) => <li className="leading-relaxed" {...p} />,
  table: ({ node: _n, ...p }) => <table className="my-2 w-full border-collapse text-sm" {...p} />,
  th: ({ node: _n, ...p }) => (
    <th className="border-b border-line px-2 py-1 text-left font-medium text-muted" {...p} />
  ),
  td: ({ node: _n, ...p }) => <td className="border-b border-line/60 px-2 py-1 align-top" {...p} />,
  code: ({ node: _n, ...p }) => (
    <code className="rounded bg-panel-2 px-1 py-0.5 font-mono text-xs break-all" {...p} />
  ),
  a: ({ node: _n, ...p }) => <a className="text-accent underline" {...p} />,
  hr: ({ node: _n, ...p }) => <hr className="my-3 border-line" {...p} />,
  strong: ({ node: _n, ...p }) => <strong className="font-semibold" {...p} />,
  em: ({ node: _n, ...p }) => <em className="italic" {...p} />,
};

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-0.5 text-sm">{children}</div>
    </div>
  );
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

  if (!incident) return <p className="text-sm text-muted">Loading…</p>;

  const v = incident.verdict;
  const confidence = v ? `${Math.round(v.classification.confidence * 100)}%` : "—";

  return (
    <section className="mx-auto max-w-7xl space-y-5">
      <Button variant="ghost" size="sm" onClick={onBack} className="-ml-2">
        <ArrowLeft className="h-4 w-4" />
        Incidents
      </Button>

      {/* Verdict header — the one clear summary the architecture promises. */}
      <Panel className="p-5">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <div className="font-mono text-xs text-muted">{incident.bundle_id}</div>
            <h2 className="mt-1 text-2xl font-semibold tracking-tight">
              {v?.classification.incident_type ?? "Withheld"}
            </h2>
            <div className="mt-1 text-sm text-muted">
              ground truth{" "}
              <span className="font-mono text-text">{incident.ground_truth}</span> · condition{" "}
              <span className="font-mono text-text">{incident.condition}</span>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-6">
            <Field label="Severity">
              <SeverityBadge severity={v?.recommendation.severity} />
            </Field>
            <Field label="Device">
              <span className="font-mono text-xs">{v?.affected_device ?? "—"}</span>
            </Field>
            <Field label="Confidence">{confidence}</Field>
          </div>
        </div>
      </Panel>

      <div className="grid grid-cols-1 gap-5 lg:grid-cols-2">
        <div className="space-y-5">
          <Panel>
            <PanelHeader title="Report" />
            <div className="p-4">
              {report ? (
                <div className="max-w-none overflow-x-auto text-text">
                  <ReactMarkdown remarkPlugins={[remarkGfm]} components={REPORT_MD}>
                    {report}
                  </ReactMarkdown>
                </div>
              ) : (
                <p className="text-sm text-muted">No report for this incident.</p>
              )}
            </div>
          </Panel>

          <Panel>
            <PanelHeader title="Evidence" aside={<span className="text-xs text-muted">alert ids</span>} />
            <div className="p-4">
              {v && v.evidence.length > 0 ? (
                <ul className="space-y-1.5">
                  {v.evidence.map((alertId) => (
                    <li
                      key={alertId}
                      className="rounded border border-line bg-panel-2 px-2.5 py-1.5 font-mono text-xs break-all text-text/90"
                    >
                      {alertId}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted">No evidence cited.</p>
              )}
            </div>
          </Panel>
        </div>

        <Panel>
          <PanelHeader
            title="Reasoning trace"
            aside={
              <span className="flex items-center gap-1.5 text-xs text-muted">
                <Cpu className="h-3.5 w-3.5" /> replayed
              </span>
            }
          />
          <div className="p-4">
            {trace.length === 0 ? (
              <p className="text-sm text-muted">No recorded trace.</p>
            ) : (
              <ol className="space-y-4">
                {trace.map((step, i) => (
                  <li key={step.event} className="relative pl-8">
                    <span className="absolute top-0 left-0 flex h-6 w-6 items-center justify-center rounded-full border border-line-strong bg-panel-2 font-mono text-xs text-accent">
                      {i + 1}
                    </span>
                    <div className="text-sm font-medium">{STEP_TITLE[step.event] ?? step.event}</div>
                    <div className="sr-only">{step.event}</div>
                    <pre className="mt-1.5 overflow-auto rounded border border-line bg-panel-2 p-2.5 font-mono text-xs leading-relaxed whitespace-pre-wrap text-text/80">
                      {beautifyJson(step.completion)}
                    </pre>
                  </li>
                ))}
              </ol>
            )}
          </div>
        </Panel>
      </div>

      <Recommendation incident={incident} />
    </section>
  );
}
