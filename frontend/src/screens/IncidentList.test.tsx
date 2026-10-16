import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Incident } from "../api/client";
import * as client from "../api/client";
import IncidentList from "./IncidentList";

vi.mock("../api/client");

const inc = (id: string, severity: string): Incident => ({
  bundle_id: id,
  condition: "C1",
  ground_truth: "syn_flood",
  emitted: true,
  decision: null,
  verdict: {
    classification: { incident_type: "syn_flood", confidence: 0.9 },
    recommendation: { recommended_action: "rate_limit_source", severity: severity as never },
    affected_device: "iot-cam-01",
    evidence: [],
  },
});

beforeEach(() => vi.resetAllMocks());

describe("IncidentList", () => {
  it("lists incidents sorted by severity (critical first)", async () => {
    vi.mocked(client.getIncidents).mockResolvedValue([inc("b-low", "low"), inc("b-crit", "critical")]);
    render(
      <IncidentList condition="C1" conditions={["C1", "C2"]} onConditionChange={() => {}} onSelect={() => {}} />,
    );
    await waitFor(() => screen.getByText("b-crit"));
    const bundles = screen.getAllByRole("row").slice(1).map((r) => r.querySelector("button")?.textContent);
    expect(bundles).toEqual(["b-crit", "b-low"]); // critical sorts before low
  });

  it("reloads when the condition filter changes", async () => {
    vi.mocked(client.getIncidents).mockResolvedValue([]);
    const onConditionChange = vi.fn();
    render(
      <IncidentList
        condition="C1"
        conditions={["C1", "C2"]}
        onConditionChange={onConditionChange}
        onSelect={() => {}}
      />,
    );
    fireEvent.change(screen.getByLabelText(/condition/i), { target: { value: "C2" } });
    expect(onConditionChange).toHaveBeenCalledWith("C2");
  });
});
