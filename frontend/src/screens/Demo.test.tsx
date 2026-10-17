import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import * as client from "../api/client";
import * as demoApi from "../api/demo";
import Demo from "./Demo";

vi.mock("../api/demo");
vi.mock("../api/client");

const scenario = {
  id: "s1",
  title: "SYN flood",
  description: "d",
  episode_id: "ep-x",
  bundle_ids: null,
  attack_family: "syn_flood",
  default_condition: "C1",
  highlight: null,
};

const events = {
  scenario,
  condition: "C1",
  window_seconds: 10,
  events: [
    { t: 1, kind: "alert", bundle_id: "b1", payload: { source: "flows", summary: "s", alert_id: "a1" } },
    { t: 5, kind: "bundle_formed", bundle_id: "b1", payload: { device: "iot-cam-01" } },
    { t: 7, kind: "verdict", bundle_id: "b1", payload: { withheld: false, incident_type: "syn_flood", severity: "high" } },
    { t: 9, kind: "recommendation", bundle_id: "b1", payload: { recommended_action: "rate_limit_source", severity: "high" } },
  ],
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal("EventSource", class {});
  vi.mocked(demoApi.getScenarios).mockResolvedValue([scenario]);
  vi.mocked(demoApi.getScenarioEvents).mockResolvedValue(events as never);
  vi.mocked(client.getIncident).mockResolvedValue({
    bundle_id: "b1", condition: "C1", ground_truth: "syn_flood", emitted: true, decision: null,
    verdict: {
      classification: { incident_type: "syn_flood", confidence: 0.9 },
      recommendation: { recommended_action: "rate_limit_source", severity: "high" },
      affected_device: "iot-cam-01", evidence: [],
    },
  } as never);
  vi.mocked(client.getReport).mockResolvedValue("");
});

describe("Demo", () => {
  it("replays a scenario: seeking to the end reveals the incident and lights the pipeline", async () => {
    render(<Demo />);
    // wait for the scenario events to load (the first alert is visible at the start)
    await waitFor(() => screen.getByText("s"));
    // seek to the end — reveal every event
    fireEvent.change(screen.getByLabelText("timeline"), { target: { value: "999" } });
    await waitFor(() => expect(screen.getAllByText("syn_flood").length).toBeGreaterThan(0));
    // the recommended action shows in the feed
    expect(screen.getAllByText("rate_limit_source").length).toBeGreaterThan(0);
    // the pipeline strip is present (its "Detectors" node is unique to the strip)
    expect(screen.getByText("Detectors")).toBeInTheDocument();
  });
});
