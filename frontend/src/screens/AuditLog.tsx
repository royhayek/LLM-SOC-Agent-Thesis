// E10-07: the audit log — a read-only, paged table of every recorded attempt, filterable by
// outcome (pass | reject | would_reject). The log is append-only and never rewritten (§6.7).
import { useEffect, useState } from "react";

import { getAudit, type AuditRecord } from "../api/client";

const OUTCOMES = ["", "pass", "reject", "would_reject"];
const PAGE = 50;

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

  return (
    <section>
      <h2>Audit log</h2>
      <label>
        Outcome{" "}
        <select value={outcome} onChange={(e) => setOutcome(e.target.value)}>
          {OUTCOMES.map((o) => (
            <option key={o} value={o}>
              {o || "all"}
            </option>
          ))}
        </select>
      </label>
      <table>
        <thead>
          <tr>
            <th>Outcome</th>
            <th>Reason</th>
            <th>Node</th>
            <th>Incident</th>
            <th>Condition</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((rec, i) => (
            <tr key={`${rec.bundle_id}-${rec.config_hash}-${rec.node}-${i}`}>
              <td>{rec.validator_outcome}</td>
              <td>{rec.rejection_reason ?? "—"}</td>
              <td>{rec.node}</td>
              <td>
                <button type="button" onClick={() => props.onSelectIncident(rec.bundle_id)}>
                  {rec.bundle_id}
                </button>
              </td>
              <td>{rec.config_hash.slice(0, 8)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div>
        <button type="button" disabled={page === 0} onClick={() => setPage((p) => p - 1)}>
          Previous
        </button>
        <span> page {page + 1} </span>
        <button
          type="button"
          disabled={(page + 1) * PAGE >= records.length}
          onClick={() => setPage((p) => p + 1)}
        >
          Next
        </button>
      </div>
    </section>
  );
}
