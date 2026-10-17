import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { IncidentFeed, type DemoIncident } from "./IncidentFeed";

const inc = (over: Partial<DemoIncident> = {}): DemoIncident => ({
  bundle_id: "b1",
  device: "iot-cam-01",
  status: "recommended",
  incident_type: "syn_flood",
  severity: "high",
  recommended_action: "rate_limit_source",
  ...over,
});

describe("IncidentFeed", () => {
  it("renders a card per incident and focuses on click", () => {
    const onFocus = vi.fn();
    render(
      <IncidentFeed
        incidents={[inc(), inc({ bundle_id: "b2" })]}
        focusedId={null}
        onFocus={onFocus}
      />,
    );
    const cards = screen.getAllByRole("button");
    expect(cards.length).toBe(2);
    fireEvent.click(cards[0]);
    expect(onFocus).toHaveBeenCalledWith("b1");
  });

  it("renders attacker text as text, not markup", () => {
    render(
      <IncidentFeed
        incidents={[inc({ incident_type: "<img src=x onerror=alert(1)>" })]}
        focusedId={null}
        onFocus={() => {}}
      />,
    );
    expect(screen.getByText("<img src=x onerror=alert(1)>")).toBeInTheDocument();
    expect(document.querySelector("img")).toBeNull();
  });
});
