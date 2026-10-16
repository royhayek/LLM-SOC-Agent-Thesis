import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Incident } from "../api/client";
import * as client from "../api/client";
import Recommendation from "./Recommendation";

vi.mock("../api/client");

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
    evidence: ["a1"],
  },
};

beforeEach(() => vi.resetAllMocks());

describe("Recommendation", () => {
  it("stores an accept and states that nothing was executed", async () => {
    vi.mocked(client.postDecision).mockResolvedValue({
      bundle_id: "b1", decision: "accept", note: null, decided_at: "2026-10-16T00:00:00Z",
    });
    render(<Recommendation incident={incident} />);
    fireEvent.click(screen.getByText("Accept recommendation"));
    await waitFor(() => screen.getByRole("status"));
    expect(client.postDecision).toHaveBeenCalledWith("b1", { decision: "accept", note: null });
    expect(screen.getByRole("status").textContent).toMatch(/no action was executed/i);
  });

  it("uses accept/reject wording, never apply or execute on the buttons", () => {
    render(<Recommendation incident={incident} />);
    expect(screen.queryByText(/apply|execute/i)).toBeNull();
    expect(screen.getByText("Reject recommendation")).toBeInTheDocument();
  });
});
