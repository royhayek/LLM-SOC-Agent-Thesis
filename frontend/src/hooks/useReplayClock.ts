// A virtual replay clock over a scenario's events. It maps each event's time onto a compressed
// timeline — idle gaps longer than `maxGap` are shrunk — so playback never stalls, and reveals the
// events whose compressed time has passed `nowT`. Pure React + requestAnimationFrame; no dependency.
import { useEffect, useMemo, useRef, useState } from "react";

import type { DemoEvent } from "../api/demo";

export function useReplayClock(events: DemoEvent[], opts: { speed?: number; maxGap?: number } = {}) {
  const maxGap = opts.maxGap ?? 2;
  const ct = useMemo(() => {
    const out: number[] = [];
    events.forEach((e, i) => {
      out[i] = i === 0 ? 0 : out[i - 1] + Math.min(Math.max(e.t - events[i - 1].t, 0), maxGap);
    });
    return out;
  }, [events, maxGap]);
  const duration = ct.length ? ct[ct.length - 1] : 0;

  const [nowT, setNowT] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [speed, setSpeed] = useState(opts.speed ?? 4);
  const raf = useRef<number | null>(null);
  const last = useRef<number | null>(null);

  // A new scenario or brain replaces the events — start its replay fresh, paused at the beginning.
  // Keyed on the content (length + first/last t), not array identity, so re-renders with an equal
  // but new array do not reset mid-replay.
  const sig = `${events.length}:${events[0]?.t ?? 0}:${events[events.length - 1]?.t ?? 0}`;
  useEffect(() => {
    setNowT(0);
    setPlaying(false);
  }, [sig]);

  useEffect(() => {
    if (!playing) return;
    const tick = (ts: number) => {
      if (last.current != null) {
        setNowT((t) => {
          const next = t + ((ts - last.current!) / 1000) * speed;
          if (next >= duration) {
            setPlaying(false);
            return duration;
          }
          return next;
        });
      }
      last.current = ts;
      raf.current = requestAnimationFrame(tick);
    };
    raf.current = requestAnimationFrame(tick);
    return () => {
      if (raf.current) cancelAnimationFrame(raf.current);
      last.current = null;
    };
  }, [playing, speed, duration]);

  const visible = useMemo(() => events.filter((_, i) => ct[i] <= nowT + 1e-9), [events, ct, nowT]);
  const seek = (t: number) => setNowT(Math.max(0, Math.min(duration, t)));
  const step = (dir: 1 | -1) => {
    const future =
      dir === 1 ? ct.filter((c) => c > nowT + 1e-9) : ct.filter((c) => c < nowT - 1e-9);
    if (future.length) seek(dir === 1 ? Math.min(...future) : Math.max(...future));
  };

  return {
    nowT,
    playing,
    visible,
    duration,
    speed,
    play: () => setPlaying(true),
    pause: () => setPlaying(false),
    toggle: () => setPlaying((p) => !p),
    seek,
    step,
    restart: () => {
      setNowT(0);
      setPlaying(true);
    },
    setSpeed,
  };
}
