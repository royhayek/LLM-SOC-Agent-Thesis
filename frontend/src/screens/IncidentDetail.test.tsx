import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Incident } from "../api/client";
import * as client from "../api/client";
import IncidentDetail from "./IncidentDetail";

vi.mock("../api/client");

// A fake SSE source that replays the three trace steps once listeners are registered.
class FakeEventSource {
  private listeners: Record<string, ((e: { data: string }) => void)[]> = {};
  onerror: (() => void) | null = null;
  constructor(public url: string) {
    queueMicrotask(() => {
      const steps: [string, string][] = [
        ["evidence", "<b>attacker</b> flows look like a flood"],
        ["classify", "syn_flood"],
        ["recommend", "rate_limit_source"],
      ];
      for (const [event, completion] of steps) {
        (this.listeners[event] ?? []).forEach((fn) =>
          fn({ data: JSON.stringify({ event, completion }) }),
        );
      }
    });
  }
  addEventListener(name: string, fn: (e: { data: string }) => void) {
    (this.listeners[name] ??= []).push(fn);
  }
  close() {}
}

const incident: Incident = {
  bundle_id: "b1",
  condition: "C1",
  ground_truth: "syn_flood",
  emitted: true,
  decision: null,
  verdict: {
    classification: { incident_type: "syn_flood", confidence: 0.9 },
    recommendation: { recommended_action: "rate_limit_source", severity: "high" },
    affected_device: "iot-cam-01",
    evidence: ["<img src=x onerror=alert(1)>"], // attacker text in an evidence id
  },
};

beforeEach(() => {
  vi.resetAllMocks();
  vi.stubGlobal("EventSource", FakeEventSource);
});

describe("IncidentDetail", () => {
  it("shows the report, evidence and the three trace steps, escaping attacker text", async () => {
    vi.mocked(client.getIncident).mockResolvedValue(incident);
    vi.mocked(client.getReport).mockResolvedValue("# Incident report\nRecorded E7-08 report body.");
    vi.mocked(client.traceUrl).mockReturnValue("/api/incidents/b1/trace?condition=C1");

    render(<IncidentDetail bundleId="b1" condition="C1" onBack={() => {}} />);

    await waitFor(() => screen.getByText(/Recorded E7-08 report body/));
    // The attacker evidence id renders as text, not as an <img> element (no XSS).
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
    // The three trace steps arrive.
    await waitFor(() => screen.getByText("evidence"));
    expect(screen.getByText("classify")).toBeInTheDocument();
    expect(screen.getByText("recommend")).toBeInTheDocument();
    // Attacker markup inside a trace step is text too.
    expect(screen.getByText(/<b>attacker<\/b> flows/)).toBeInTheDocument();
  });
});
