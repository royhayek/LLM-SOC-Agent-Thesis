// E10-04: the incident list. One row per analysed bundle for the selected condition, with its
// type, severity and device; sorted by severity; filtered by condition; rows open the detail.
import { useEffect, useState } from "react";

import { getIncidents, type Incident } from "../api/client";

const SEVERITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

function severityRank(incident: Incident): number {
  const sev = incident.verdict?.recommendation.severity;
  return sev ? (SEVERITY_ORDER[sev] ?? 98) : 99; // withheld verdicts sort last
}

export default function IncidentList(props: {
  condition: string;
  conditions: string[];
  onConditionChange: (condition: string) => void;
  onSelect: (bundleId: string) => void;
}) {
  const { condition, conditions, onConditionChange, onSelect } = props;
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setError(null);
    getIncidents(condition)
      .then((rows) => active && setIncidents(rows))
      .catch((e: unknown) => active && setError(String(e)));
    return () => {
      active = false;
    };
  }, [condition]);

  const sorted = [...incidents].sort((a, b) => severityRank(a) - severityRank(b));

  return (
    <section>
      <h2>Incidents</h2>
      <label>
        Condition{" "}
        <select value={condition} onChange={(e) => onConditionChange(e.target.value)}>
          {conditions.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </label>
      {error && <p role="alert">{error}</p>}
      <table>
        <thead>
          <tr>
            <th>Incident</th>
            <th>Type</th>
            <th>Severity</th>
            <th>Device</th>
            <th>Condition</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((incident) => (
            <tr key={incident.bundle_id}>
              <td>
                <button type="button" onClick={() => onSelect(incident.bundle_id)}>
                  {incident.bundle_id}
                </button>
              </td>
              <td>{incident.verdict?.classification.incident_type ?? "—"}</td>
              <td>{incident.verdict?.recommendation.severity ?? "withheld"}</td>
              <td>{incident.verdict?.affected_device ?? "—"}</td>
              <td>{incident.condition}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
