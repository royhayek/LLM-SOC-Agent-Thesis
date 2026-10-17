// Picks the scenario to replay and the "brain" (agent vs a baseline) to replay it under.
import type { Scenario } from "../../api/demo";
import { Select } from "../../components/ui/Select";

// The meaningful comparison for the demo: the full agent vs the two baselines.
const BRAINS: { value: string; label: string }[] = [
  { value: "C1", label: "Agent (full)" },
  { value: "C6", label: "Baseline B (prompt-only)" },
  { value: "C7", label: "Baseline A (ML classifier)" },
];

export function ScenarioPicker(props: {
  scenarios: Scenario[];
  scenarioId: string;
  onScenario: (id: string) => void;
  condition: string;
  onCondition: (c: string) => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-4">
      <label className="flex items-center gap-2 text-sm text-muted">
        Scenario
        <Select value={props.scenarioId} onChange={(e) => props.onScenario(e.target.value)}>
          {props.scenarios.map((s) => (
            <option key={s.id} value={s.id}>
              {s.title}
            </option>
          ))}
        </Select>
      </label>
      <label className="flex items-center gap-2 text-sm text-muted">
        Brain
        <Select value={props.condition} onChange={(e) => props.onCondition(e.target.value)}>
          {BRAINS.map((b) => (
            <option key={b.value} value={b.value}>
              {b.label}
            </option>
          ))}
        </Select>
      </label>
    </div>
  );
}
