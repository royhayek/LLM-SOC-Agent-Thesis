import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { TransportBar } from "./TransportBar";

const noop = () => {};

describe("TransportBar", () => {
  it("the scrubber can reach the exact duration (not rounded short by the step)", () => {
    const onSeek = vi.fn();
    render(
      <TransportBar
        playing={false}
        nowT={0}
        duration={13.886987}
        speed={4}
        onToggle={noop}
        onSeek={onSeek}
        onStep={noop}
        onRestart={noop}
        onSpeed={noop}
      />,
    );
    const range = screen.getByLabelText("timeline") as HTMLInputElement;
    // A stepped slider rounds its max down and can never reach the exact duration (so the final
    // event never shows when scrubbing to the end). `step="any"` makes it continuous. jsdom does
    // not enforce range stepping, so this pins the fix by its attribute; verified live in a browser.
    expect(range).toHaveAttribute("step", "any");
    fireEvent.change(range, { target: { value: "13.886987" } });
    expect(onSeek).toHaveBeenCalledWith(13.886987);
  });
});
