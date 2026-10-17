// E10-04: the incident list. One row per analysed bundle for the selected condition, with its
// type, severity and device; sorted by severity; filtered by condition; rows open the detail.
import { ChevronRight } from "lucide-react";
import { useEffect, useState } from "react";

import { getIncidents, type Incident } from "../api/client";
import { Button } from "../components/ui/Button";
import { Panel } from "../components/ui/Panel";
import { Select } from "../components/ui/Select";
import { SeverityBadge } from "../components/ui/SeverityBadge";
import { severityRank } from "../lib/utils";

const PAGE = 50;

export default function IncidentList(props: {
  condition: string;
  conditions: string[];
  onConditionChange: (condition: string) => void;
  onSelect: (bundleId: string) => void;
}) {
  const { condition, conditions, onConditionChange, onSelect } = props;
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);

  useEffect(() => {
    let active = true;
    setError(null);
    getIncidents(condition)
      .then((rows) => {
        if (!active) return;
        setIncidents(rows);
        setPage(0);
      })
      .catch((e: unknown) => active && setError(String(e)));
    return () => {
      active = false;
    };
  }, [condition]);

  const sorted = [...incidents].sort(
    (a, b) =>
      severityRank(a.verdict?.recommendation.severity) -
      severityRank(b.verdict?.recommendation.severity),
  );
  const shown = sorted.slice(page * PAGE, page * PAGE + PAGE);
  const lastPage = (page + 1) * PAGE >= sorted.length;

  return (
    <section className="mx-auto flex h-full max-w-5xl flex-col gap-4">
      <div className="flex shrink-0 items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Incidents</h2>
          <p className="text-sm text-muted">
            {incidents.length} analysed bundle{incidents.length === 1 ? "" : "s"}, sorted by
            severity.
            {sorted.length > PAGE && (
              <>
                {" "}
                Showing {page * PAGE + 1}–{Math.min((page + 1) * PAGE, sorted.length)}.
              </>
            )}
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-muted">
          Condition
          <Select value={condition} onChange={(e) => onConditionChange(e.target.value)}>
            {conditions.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </Select>
        </label>
      </div>

      {error && (
        <p role="alert" className="rounded-md border border-sev-critical/40 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">
          {error}
        </p>
      )}

      <Panel className="flex min-h-0 flex-1 flex-col overflow-hidden">
        <div className="min-h-0 flex-1 overflow-auto">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="sticky top-0 z-10 border-b border-line bg-panel text-left text-xs font-medium text-muted">
              <th className="px-4 py-2.5 font-medium">Incident</th>
              <th className="px-4 py-2.5 font-medium">Type</th>
              <th className="px-4 py-2.5 font-medium">Severity</th>
              <th className="px-4 py-2.5 font-medium">Device</th>
              <th className="px-4 py-2.5 font-medium">Condition</th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {shown.map((incident) => (
              <tr
                key={incident.bundle_id}
                className="group cursor-pointer border-b border-line/60 last:border-0 hover:bg-panel-2"
                onClick={() => onSelect(incident.bundle_id)}
              >
                <td className="px-4 py-2.5">
                  <button
                    type="button"
                    className="font-mono text-xs text-accent hover:underline"
                    onClick={() => onSelect(incident.bundle_id)}
                  >
                    {incident.bundle_id}
                  </button>
                </td>
                <td className="px-4 py-2.5">
                  {incident.verdict?.classification.incident_type ?? (
                    <span className="text-muted">—</span>
                  )}
                </td>
                <td className="px-4 py-2.5">
                  <SeverityBadge severity={incident.verdict?.recommendation.severity} />
                </td>
                <td className="px-4 py-2.5 font-mono text-xs text-muted">
                  {incident.verdict?.affected_device ?? "—"}
                </td>
                <td className="px-4 py-2.5 font-mono text-xs text-muted">{incident.condition}</td>
                <td className="px-2 text-muted">
                  <ChevronRight className="h-4 w-4 opacity-0 transition-opacity group-hover:opacity-100" />
                </td>
              </tr>
            ))}
            {sorted.length === 0 && !error && (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-sm text-muted">
                  No incidents for this condition.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
      </Panel>

      {sorted.length > PAGE && (
        <div className="flex items-center justify-end gap-3 text-sm text-muted">
          <Button
            variant="outline"
            size="sm"
            disabled={page === 0}
            onClick={() => setPage((p) => p - 1)}
          >
            Previous
          </Button>
          <span className="font-mono text-xs">page {page + 1}</span>
          <Button
            variant="outline"
            size="sm"
            disabled={lastPage}
            onClick={() => setPage((p) => p + 1)}
          >
            Next
          </Button>
        </div>
      )}
    </section>
  );
}
