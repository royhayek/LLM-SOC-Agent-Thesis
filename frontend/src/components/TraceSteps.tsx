// The agent's reasoning trace as numbered steps. Completions are rendered as text in a <pre>
// (React-escaped), beautified when JSON. The raw event name is kept in an .sr-only span.
import { beautifyJson } from "../lib/format";

const STEP_TITLE: Record<string, string> = {
  evidence: "Evidence analysis",
  classify: "Classification",
  recommend: "Recommendation",
};

export function TraceSteps({ steps }: { steps: { event: string; completion: string }[] }) {
  return (
    <ol className="space-y-4">
      {steps.map((step, i) => (
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
  );
}
