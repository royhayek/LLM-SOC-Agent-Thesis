// E10-07: the audit log — a read-only, paged table of every recorded attempt, filterable by
// outcome (pass | reject | would_reject). The log is append-only and never rewritten (§6.7).
import { useEffect, useState } from "react";

import { getAudit, type AuditRecord } from "../api/client";
import { Button } from "../components/ui/Button";
import { Panel } from "../components/ui/Panel";
import { Select } from "../components/ui/Select";
import { cn } from "../lib/utils";

const OUTCOMES = ["", "pass", "reject", "would_reject"];
const PAGE = 50;

const OUTCOME_STYLE: Record<string, string> = {
  pass: "text-sev-low",
  reject: "text-sev-critical",
  would_reject: "text-sev-high",
};

export default function AuditLog(props: { onSelectIncident: (bundleId: string) => void }) {
  const [records, setRecords] = useState<AuditRecord[]>([]);
  const [outcome, setOutcome] = useState("");
  const [page, setPage] = useState(0);

  useEffect(() => {
    let active = true;
    getAudit(outcome || undefined).then((r) => {
      if (!active) return;
      setRecords(r);
      setPage(0);
    });
    return () => {
      active = false;
    };
  }, [outcome]);

  const shown = records.slice(page * PAGE, page * PAGE + PAGE);
  const lastPage = (page + 1) * PAGE >= records.length;

  return (
    <section className="mx-auto max-w-5xl space-y-4">
      <div className="flex items-end justify-between">
        <div>
          <h2 className="text-lg font-semibold tracking-tight">Audit log</h2>
          <p className="text-sm text-muted">
            {records.length} record{records.length === 1 ? "" : "s"}, append-only.
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm text-muted">
          Outcome
          <Select value={outcome} onChange={(e) => setOutcome(e.target.value)}>
            {OUTCOMES.map((o) => (
              <option key={o} value={o}>
                {o || "all"}
              </option>
            ))}
          </Select>
        </label>
      </div>

      <Panel className="overflow-hidden">
        <table className="w-full border-collapse text-sm">
          <thead>
            <tr className="border-b border-line text-left text-xs font-medium text-muted">
              <th className="px-4 py-2.5 font-medium">Outcome</th>
              <th className="px-4 py-2.5 font-medium">Reason</th>
              <th className="px-4 py-2.5 font-medium">Node</th>
              <th className="px-4 py-2.5 font-medium">Incident</th>
              <th className="px-4 py-2.5 font-medium">Condition</th>
            </tr>
          </thead>
          <tbody>
            {shown.map((rec, i) => (
              <tr
                key={`${rec.bundle_id}-${rec.config_hash}-${rec.node}-${i}`}
                className="border-b border-line/60 last:border-0 hover:bg-panel-2"
              >
                <td className={cn("px-4 py-2.5 font-medium", OUTCOME_STYLE[rec.validator_outcome])}>
                  {rec.validator_outcome}
                </td>
                <td className="px-4 py-2.5 text-muted">{rec.rejection_reason ?? "—"}</td>
                <td className="px-4 py-2.5 text-muted">{rec.node}</td>
                <td className="px-4 py-2.5">
                  <button
                    type="button"
                    className="font-mono text-xs text-accent hover:underline"
                    onClick={() => props.onSelectIncident(rec.bundle_id)}
                  >
                    {rec.bundle_id}
                  </button>
                </td>
                <td className="px-4 py-2.5 font-mono text-xs text-muted">
                  {rec.config_hash.slice(0, 8)}
                </td>
              </tr>
            ))}
            {shown.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center text-sm text-muted">
                  No records.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </Panel>

      <div className="flex items-center justify-end gap-3 text-sm text-muted">
        <Button variant="outline" size="sm" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
          Previous
        </Button>
        <span className="font-mono text-xs">page {page + 1}</span>
        <Button variant="outline" size="sm" disabled={lastPage} onClick={() => setPage((p) => p + 1)}>
          Next
        </Button>
      </div>
    </section>
  );
}
