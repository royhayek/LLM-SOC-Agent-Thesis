// The telemetry feed: alerts appear by source as the replay clock passes their timestamps. Newest
// first. Alert summaries are rendered as text (attacker text stays inert).
import type { DemoEvent } from "../../api/demo";
import { cn } from "../../lib/utils";

const SRC_COLOR: Record<string, string> = {
  flows: "text-sev-medium",
  mqtt: "text-sev-low",
  honeypot: "text-sev-high",
};

export function TelemetryFeed({ alerts }: { alerts: DemoEvent[] }) {
  const shown = [...alerts].reverse().slice(0, 40); // newest first, capped
  return (
    <div className="space-y-1.5">
      {shown.length === 0 && <p className="text-sm text-muted">Waiting for telemetry…</p>}
      {shown.map((a, i) => {
        const src = String(a.payload.source ?? "");
        const label = a.payload.detector_label ? String(a.payload.detector_label) : null;
        const score = a.payload.detector_score;
        const summary = String(a.payload.summary ?? "");
        return (
          <div
            key={`${a.bundle_id}-${String(a.payload.alert_id)}-${i}`}
            className="fade-in flex items-start gap-2 rounded border border-line bg-panel px-2.5 py-1.5 text-xs"
          >
            <span className={cn("font-mono font-medium uppercase", SRC_COLOR[src] ?? "text-muted")}>
              {src}
            </span>
            <span className="font-mono break-all text-text/80">{summary}</span>
            {label && (
              <span className="ml-auto whitespace-nowrap text-muted">
                {label}
                {typeof score === "number" ? ` (${score})` : ""}
              </span>
            )}
          </div>
        );
      })}
    </div>
  );
}
