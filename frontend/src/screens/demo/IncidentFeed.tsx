// The incident feed fills as bundles form during the replay. One card per incident; click to focus
// its lifecycle. All dynamic text is React-escaped (attacker text stays inert).
import { ChevronRight } from "lucide-react";

import { SeverityBadge } from "../../components/ui/SeverityBadge";
import { cn } from "../../lib/utils";

export interface DemoIncident {
  bundle_id: string;
  device: string;
  status: "detecting" | "reasoning" | "recommended" | "withheld";
  incident_type?: string | null;
  severity?: string | null;
  recommended_action?: string | null;
}

export function IncidentFeed({
  incidents,
  focusedId,
  onFocus,
}: {
  incidents: DemoIncident[];
  focusedId: string | null;
  onFocus: (bundleId: string) => void;
}) {
  return (
    <div className="space-y-2">
      {incidents.length === 0 && <p className="text-sm text-muted">No incidents yet.</p>}
      {incidents.map((inc) => (
        <button
          key={inc.bundle_id}
          type="button"
          onClick={() => onFocus(inc.bundle_id)}
          className={cn(
            "fade-in flex w-full items-center gap-3 rounded-lg border px-3 py-2.5 text-left transition-colors",
            focusedId === inc.bundle_id
              ? "border-accent/50 bg-accent-soft"
              : "border-line bg-panel hover:bg-panel-2",
          )}
        >
          <div className="min-w-0 flex-1">
            <div className="font-mono text-xs text-muted">{inc.device}</div>
            <div className="truncate text-sm font-medium">{inc.incident_type ?? "—"}</div>
            {inc.recommended_action && (
              <div className="mt-0.5 font-mono text-xs text-accent">{inc.recommended_action}</div>
            )}
          </div>
          <SeverityBadge severity={inc.severity} />
          <span className="w-20 text-right text-xs text-muted">{inc.status}</span>
          <ChevronRight className="h-4 w-4 shrink-0 text-muted" />
        </button>
      ))}
    </div>
  );
}
