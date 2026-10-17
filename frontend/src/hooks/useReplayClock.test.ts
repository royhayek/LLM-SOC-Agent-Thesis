import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import type { DemoEvent } from "../api/demo";
import { useReplayClock } from "./useReplayClock";

const ev = (t: number): DemoEvent => ({ t, kind: "alert", bundle_id: "b", payload: {} });

describe("useReplayClock", () => {
  it("reveals events up to nowT and supports seek/step", () => {
    const { result } = renderHook(() => useReplayClock([ev(0), ev(10), ev(100)], { maxGap: 2 }));
    expect(result.current.visible.length).toBe(1); // t=0 visible at start
    act(() => result.current.step(1));
    expect(result.current.visible.length).toBe(2); // step to the next event
    act(() => result.current.seek(result.current.duration));
    expect(result.current.visible.length).toBe(3); // seek to the end reveals all
  });

  it("compresses idle gaps so duration is bounded", () => {
    const { result } = renderHook(() => useReplayClock([ev(0), ev(1000)], { maxGap: 2 }));
    expect(result.current.duration).toBeLessThanOrEqual(2); // 1000s gap compressed to <=2s
  });

  it("resets to the start when the events change (new scenario/brain)", () => {
    const { result, rerender } = renderHook(({ evs }) => useReplayClock(evs, { maxGap: 2 }), {
      initialProps: { evs: [ev(0), ev(10)] },
    });
    act(() => result.current.seek(result.current.duration));
    expect(result.current.visible.length).toBe(2); // all of scenario A revealed
    rerender({ evs: [ev(0), ev(5), ev(50)] }); // switch to scenario B
    expect(result.current.visible.length).toBe(1); // reset: only B's first event is visible
  });
});
