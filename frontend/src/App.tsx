// The console shell: four screens (incident list, detail, decision, audit), localhost only. The
// agent recommends and never executes.
import { useEffect, useState } from "react";

import { getConditions } from "./api/client";
import AuditLog from "./screens/AuditLog";
import IncidentDetail from "./screens/IncidentDetail";
import IncidentList from "./screens/IncidentList";

type View = { name: "incidents" } | { name: "detail"; bundleId: string } | { name: "audit" };

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

  return (
    <main>
      <h1>SOC console</h1>
      <p>A recommendation view. A human decides; the agent never executes.</p>
      <nav>
        <button type="button" onClick={() => setView({ name: "incidents" })}>
          Incidents
        </button>{" "}
        <button type="button" onClick={() => setView({ name: "audit" })}>
          Audit log
        </button>
      </nav>

      {view.name === "incidents" && (
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
      {view.name === "audit" && <AuditLog onSelectIncident={openDetail} />}
    </main>
  );
}
