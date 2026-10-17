// Runs the real three-node graph on this one bundle against the hosted model, streaming the node
// outputs over SSE (Phase 2). Clearly labelled LIVE; nothing is persisted. If the hosted model is
// not configured the stream errors with no steps, and we say so.
import { Zap } from "lucide-react";
import { useRef, useState } from "react";

import { liveTraceUrl } from "../../api/demo";
import { TraceSteps } from "../../components/TraceSteps";
import { Button } from "../../components/ui/Button";

type Status = "idle" | "running" | "done" | "error";

export function LiveRunButton({ bundleId, condition }: { bundleId: string; condition: string }) {
  const [steps, setSteps] = useState<{ event: string; completion: string }[]>([]);
  const [status, setStatus] = useState<Status>("idle");
  const [elapsed, setElapsed] = useState(0);
  const timer = useRef<number | null>(null);
  const got = useRef(0);

  const stop = (s: Status) => {
    if (timer.current) window.clearInterval(timer.current);
    setStatus(s);
  };

  const start = () => {
    if (typeof EventSource === "undefined") return;
    if (!window.confirm("Run the hosted model live on this incident? This calls the paid API.")) {
      return;
    }
    setSteps([]);
    setStatus("running");
    setElapsed(0);
    got.current = 0;
    const t0 = Date.now();
    timer.current = window.setInterval(() => setElapsed((Date.now() - t0) / 1000), 100);
    const src = new EventSource(liveTraceUrl(bundleId, condition));
    for (const name of ["evidence", "classify", "recommend"]) {
      src.addEventListener(name, (e) => {
        const d = JSON.parse((e as MessageEvent).data) as { completion: string };
        got.current += 1;
        setSteps((prev) => [...prev, { event: name, completion: d.completion }]);
      });
    }
    src.addEventListener("verdict", () => {
      src.close();
      stop("done");
    });
    src.onerror = () => {
      src.close();
      stop(got.current > 0 ? "done" : "error");
    };
  };

  return (
    <div className="space-y-2">
      <Button variant="outline" onClick={start} disabled={status === "running"}>
        <Zap className="h-4 w-4" />
        {status === "running" ? "Running live…" : "Run this live"}
      </Button>

      {status !== "idle" && (
        <div className="rounded-lg border border-accent/40 bg-accent-soft/50 p-3">
          <div className="mb-2 flex items-center gap-2 text-xs font-medium text-accent">
            <Zap className="h-3.5 w-3.5" />
            LIVE · hosted model · {elapsed.toFixed(1)}s
          </div>
          {status === "error" ? (
            <p className="text-sm text-muted">
              Live run unavailable — the hosted model may not be configured on the server.
            </p>
          ) : steps.length > 0 ? (
            <TraceSteps steps={steps} />
          ) : (
            <p className="text-sm text-muted">Waiting for the model…</p>
          )}
        </div>
      )}
    </div>
  );
}
