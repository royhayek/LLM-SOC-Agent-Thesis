// E10-06: the human accepts or rejects the recommendation. The decision is stored in SQLite and
// nothing is executed — the agent recommends and never acts (§1.1). Buttons say "Accept"/"Reject
// recommendation", never "Apply" or "Execute".
import { useState } from "react";

import { postDecision, type Incident } from "../api/client";

export default function Recommendation(props: {
  incident: Incident;
  onDecided?: (decision: string) => void;
}) {
  const { incident } = props;
  const [note, setNote] = useState("");
  const [decision, setDecision] = useState<string | null>(incident.decision);
  const [error, setError] = useState<string | null>(null);

  const decide = (choice: "accept" | "reject") => {
    setError(null);
    postDecision(incident.bundle_id, { decision: choice, note: note || null })
      .then((out) => {
        setDecision(out.decision);
        props.onDecided?.(out.decision);
      })
      .catch((e: unknown) => setError(String(e)));
  };

  const action = incident.verdict?.recommendation.recommended_action;

  return (
    <section>
      <h3>Recommendation</h3>
      {action ? (
        <p>
          The agent recommends <strong>{action}</strong>. It is a recommendation only.
        </p>
      ) : (
        <p>No recommendation (the verdict was withheld).</p>
      )}
      <label>
        Comment{" "}
        <input value={note} onChange={(e) => setNote(e.target.value)} aria-label="comment" />
      </label>
      <div>
        <button type="button" onClick={() => decide("accept")}>
          Accept recommendation
        </button>
        <button type="button" onClick={() => decide("reject")}>
          Reject recommendation
        </button>
      </div>
      {error && <p role="alert">{error}</p>}
      {decision && (
        <p role="status">
          Decision recorded: <strong>{decision}</strong>. No action was executed — a human decided.
        </p>
      )}
    </section>
  );
}
