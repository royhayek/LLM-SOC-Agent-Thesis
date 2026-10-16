import { describe, expect, it } from "vitest";

import type { Incident } from "./api/client";
import { incidentSummary } from "./incidentLabel";

const withVerdict: Incident = {
  bundle_id: "b1",
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

describe("incidentSummary", () => {
  it("summarises the verdict", () => {
    expect(incidentSummary(withVerdict)).toBe("b1: syn_flood → rate_limit_source");
  });

  it("marks a withheld incident", () => {
    expect(incidentSummary({ ...withVerdict, emitted: false, verdict: null })).toBe(
      "b1: withheld (no verdict)",
    );
  });
});
