// The pipeline, made live: each stage lights up as the replay reaches activity in it. The three
// agent calls are bracketed to show the fixed evidence -> classify -> recommend graph.
import { cn } from "../../lib/utils";

export type Stage =
  | "telemetry"
  | "detectors"
  | "bundle"
  | "evidence"
  | "classify"
  | "recommend"
  | "validator"
  | "recommendation"
  | "human"
  | null;

const STAGES: { key: Exclude<Stage, null>; label: string; agent?: boolean }[] = [
  { key: "telemetry", label: "Telemetry" },
  { key: "detectors", label: "Detectors" },
  { key: "bundle", label: "Bundle" },
  { key: "evidence", label: "Evidence", agent: true },
  { key: "classify", label: "Classify", agent: true },
  { key: "recommend", label: "Recommend", agent: true },
  { key: "validator", label: "Validator" },
  { key: "recommendation", label: "Action" },
  { key: "human", label: "Human" },
];

function Node({ label, active }: { label: string; active: boolean }) {
  return (
    <span
      className={cn(
        "rounded-md border px-2.5 py-1 text-xs font-medium whitespace-nowrap transition-colors",
        active
          ? "border-accent/50 bg-accent-soft text-accent motion-safe:animate-pulse"
          : "border-line text-muted",
      )}
    >
      {label}
    </span>
  );
}

export function PipelineStrip({ activeStage }: { activeStage: Stage }) {
  return (
    <div className="flex items-center gap-1.5 overflow-x-auto py-1">
      {STAGES.map((s, i) => (
        <div key={s.key} className="flex items-center gap-1.5">
          {i > 0 && <span className="text-muted/50">→</span>}
          {s.agent && (!STAGES[i - 1]?.agent || i === 0) && (
            <span className="text-[10px] font-medium tracking-wide text-muted">agent&nbsp;</span>
          )}
          <Node label={s.label} active={activeStage === s.key} />
        </div>
      ))}
    </div>
  );
}
