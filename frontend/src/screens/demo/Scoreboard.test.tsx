import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { DemoEvent } from "../../api/demo";
import { Scoreboard } from "./Scoreboard";

const e = (kind: DemoEvent["kind"], payload: Record<string, unknown> = {}): DemoEvent =>
  ({ t: 0, kind, bundle_id: "b", payload }) as DemoEvent;

describe("Scoreboard", () => {
  it("tallies alerts, incidents, recommendations and withheld", () => {
    render(
      <Scoreboard
        events={[
          e("alert"),
          e("alert"),
          e("bundle_formed"),
          e("bundle_formed"),
          e("recommendation", { recommended_action: "rate_limit_source" }),
          e("verdict", { withheld: true }),
        ]}
      />,
    );
    expect(screen.getByTestId("stat-alerts")).toHaveTextContent("2");
    expect(screen.getByTestId("stat-incidents")).toHaveTextContent("2");
    expect(screen.getByTestId("stat-recommended")).toHaveTextContent("1");
    expect(screen.getByTestId("stat-withheld")).toHaveTextContent("1");
  });
});
