// A running tally of the replay so far: alerts seen, incidents formed, recommendations made, and
// verdicts withheld. Pure derivation from the visible events; updates live as the clock advances.
import { useMemo } from "react";

import type { DemoEvent } from "../../api/demo";

export function Scoreboard({ events }: { events: DemoEvent[] }) {
  const tally = useMemo(() => {
    let alerts = 0;
    let incidents = 0;
    let recommended = 0;
    let withheld = 0;
    for (const e of events) {
      if (e.kind === "alert") alerts += 1;
      else if (e.kind === "bundle_formed") incidents += 1;
      else if (e.kind === "recommendation") recommended += 1;
      else if (e.kind === "verdict" && e.payload.withheld) withheld += 1;
    }
    return { alerts, incidents, recommended, withheld };
  }, [events]);

  const stats: { key: string; label: string; value: number }[] = [
    { key: "alerts", label: "Alerts", value: tally.alerts },
    { key: "incidents", label: "Incidents", value: tally.incidents },
    { key: "recommended", label: "Recommended", value: tally.recommended },
    { key: "withheld", label: "Withheld", value: tally.withheld },
  ];

  return (
    <div className="flex flex-wrap gap-3">
      {stats.map((s) => (
        <div
          key={s.key}
          data-testid={`stat-${s.key}`}
          className="rounded-lg border border-line bg-panel px-3 py-1.5 text-center"
        >
          <div className="text-lg font-semibold tracking-tight">{s.value}</div>
          <div className="text-xs text-muted">{s.label}</div>
        </div>
      ))}
    </div>
  );
}
