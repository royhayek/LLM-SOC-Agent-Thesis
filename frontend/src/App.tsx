// The console shell: a fixed sidebar, a top bar, and one of four screens (list, detail, decision,
// audit). Localhost only. The agent recommends and never executes.
import { ListChecks, Lock, PlayCircle, ScrollText, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { getConditions } from "./api/client";
import { cn } from "./lib/utils";
import AuditLog from "./screens/AuditLog";
import Demo from "./screens/Demo";
import IncidentDetail from "./screens/IncidentDetail";
import IncidentList from "./screens/IncidentList";

type View =
  | { name: "incidents" }
  | { name: "detail"; bundleId: string }
  | { name: "audit" }
  | { name: "demo" };

function NavItem(props: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      type="button"
      onClick={props.onClick}
      className={cn(
        "flex w-full items-center gap-3 rounded-md px-3 py-2 text-sm transition-colors",
        props.active
          ? "bg-accent-soft text-text"
          : "text-muted hover:bg-panel-2 hover:text-text",
      )}
    >
      <span className={cn(props.active ? "text-accent" : "text-muted")}>{props.icon}</span>
      {props.label}
    </button>
  );
}

export default function App() {
  const [view, setView] = useState<View>({ name: "incidents" });
  const [conditions, setConditions] = useState<string[]>(["C1"]);
  const [condition, setCondition] = useState("C1");

  useEffect(() => {
    getConditions()
      .then((c) => c.length > 0 && setConditions(c))
      .catch(() => undefined);
  }, []);

  const openDetail = (bundleId: string) => setView({ name: "detail", bundleId });
  const current = view.name;

  return (
    <div className="app-grid flex min-h-screen">
      <aside className="flex w-60 shrink-0 flex-col justify-between border-r border-line bg-panel/60 px-3 py-5">
        <div>
          <div className="flex items-center gap-2.5 px-2 pb-6">
            <ShieldCheck className="h-6 w-6 text-accent" />
            <div className="leading-tight">
              <div className="font-semibold tracking-tight">SOC console</div>
              <div className="font-mono text-[11px] text-muted">IoT incident triage</div>
            </div>
          </div>
          <nav className="space-y-1">
            <NavItem
              active={current === "incidents" || current === "detail"}
              onClick={() => setView({ name: "incidents" })}
              icon={<ListChecks className="h-4 w-4" />}
              label="Incidents"
            />
            <NavItem
              active={current === "audit"}
              onClick={() => setView({ name: "audit" })}
              icon={<ScrollText className="h-4 w-4" />}
              label="Audit log"
            />
            <NavItem
              active={current === "demo"}
              onClick={() => setView({ name: "demo" })}
              icon={<PlayCircle className="h-4 w-4" />}
              label="Demo"
            />
          </nav>
        </div>
        <div className="rounded-md border border-line bg-panel-2 px-3 py-2.5">
          <div className="flex items-center gap-2 text-xs font-medium text-text">
            <Lock className="h-3.5 w-3.5 text-sev-low" />
            Recommend-only
          </div>
          <p className="mt-1 text-[11px] leading-snug text-muted">
            The agent suggests. A human decides. Nothing is executed.
          </p>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b border-line px-6">
          <h1 className="text-sm font-medium text-muted">
            {current === "audit" ? "Audit log" : current === "demo" ? "Demo" : "Incidents"}
          </h1>
          <span className="font-mono text-[11px] text-muted">127.0.0.1 · read-only</span>
        </header>

        <main className="fade-in min-w-0 flex-1 overflow-auto p-6">
          {current === "incidents" && (
            <IncidentList
              condition={condition}
              conditions={conditions}
              onConditionChange={setCondition}
              onSelect={openDetail}
            />
          )}
          {view.name === "detail" && (
            <IncidentDetail
              bundleId={view.bundleId}
              condition={condition}
              onBack={() => setView({ name: "incidents" })}
            />
          )}
          {current === "audit" && <AuditLog onSelectIncident={openDetail} />}
          {current === "demo" && <Demo />}
        </main>
      </div>
    </div>
  );
}
