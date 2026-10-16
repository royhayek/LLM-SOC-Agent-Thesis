import type { Incident } from "./api/client";

// A one-line summary of an incident. It reads `verdict.classification.incident_type` and
// `verdict.recommendation.recommended_action` from the generated types, so renaming either field
// in the backend `Verdict` schema (and regenerating) breaks this at compile time (E10-03 AC).
export function incidentSummary(incident: Incident): string {
  const verdict = incident.verdict;
  if (verdict === null) return `${incident.bundle_id}: withheld (no verdict)`;
  return (
    `${incident.bundle_id}: ${verdict.classification.incident_type}` +
    ` → ${verdict.recommendation.recommended_action}`
  );
}
