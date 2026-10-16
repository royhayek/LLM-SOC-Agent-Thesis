// E10-06: the human accepts or rejects the recommendation. The decision is stored in SQLite and
// nothing is executed — the agent recommends and never acts (§1.1). Buttons say "Accept"/"Reject
// recommendation", never "Apply" or "Execute".
import { Check, ShieldOff, X } from "lucide-react";
import { useState } from "react";

import { postDecision, type Incident } from "../api/client";
import { Button } from "../components/ui/Button";
import { Panel, PanelHeader } from "../components/ui/Panel";

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
    <Panel>
      <PanelHeader title="Decision" />
      <div className="space-y-4 p-4">
        {action ? (
          <p className="text-sm text-muted">
            The agent recommends{" "}
            <span className="rounded bg-panel-2 px-1.5 py-0.5 font-mono text-xs text-text">
              {action}
            </span>
            . This is a recommendation only.
          </p>
        ) : (
          <p className="text-sm text-muted">No recommendation — the verdict was withheld.</p>
        )}

        <label className="block text-sm text-muted">
          Comment
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            aria-label="comment"
            placeholder="Optional note for the record"
            className="mt-1 block w-full rounded-md border border-line-strong bg-panel-2 px-3 py-2 text-sm text-text placeholder:text-muted/60 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/70"
          />
        </label>

        <div className="flex gap-2">
          <Button onClick={() => decide("accept")}>
            <Check className="h-4 w-4" />
            Accept recommendation
          </Button>
          <Button variant="danger" onClick={() => decide("reject")}>
            <X className="h-4 w-4" />
            Reject recommendation
          </Button>
        </div>

        {error && (
          <p role="alert" className="text-sm text-sev-critical">
            {error}
          </p>
        )}
        {decision && (
          <div
            role="status"
            className="flex items-start gap-2 rounded-md border border-sev-low/30 bg-sev-low/10 px-3 py-2.5 text-sm"
          >
            <ShieldOff className="mt-0.5 h-4 w-4 shrink-0 text-sev-low" />
            <span>
              Decision recorded: <span className="font-medium">{decision}</span>. No action was
              executed — a human decided.
            </span>
          </div>
        )}
      </div>
    </Panel>
  );
}
