// Replay transport: play/pause, a scrubber, speed, step and restart. Space and arrow keys are wired
// at the Demo view.
import { Pause, Play, RotateCcw, SkipBack, SkipForward } from "lucide-react";

import { Button } from "../../components/ui/Button";

const SPEEDS = [1, 2, 4, 8];

export function TransportBar(props: {
  playing: boolean;
  nowT: number;
  duration: number;
  speed: number;
  onToggle: () => void;
  onSeek: (t: number) => void;
  onStep: (dir: 1 | -1) => void;
  onRestart: () => void;
  onSpeed: (x: number) => void;
}) {
  const { playing, nowT, duration, speed } = props;
  return (
    <div className="flex items-center gap-3">
      <Button variant="outline" size="icon" aria-label="step back" onClick={() => props.onStep(-1)}>
        <SkipBack className="h-4 w-4" />
      </Button>
      <Button size="icon" aria-label={playing ? "pause" : "play"} onClick={props.onToggle}>
        {playing ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
      </Button>
      <Button
        variant="outline"
        size="icon"
        aria-label="step forward"
        onClick={() => props.onStep(1)}
      >
        <SkipForward className="h-4 w-4" />
      </Button>
      <Button variant="ghost" size="icon" aria-label="restart" onClick={props.onRestart}>
        <RotateCcw className="h-4 w-4" />
      </Button>
      <input
        type="range"
        aria-label="timeline"
        min={0}
        max={Math.max(duration, 0.001)}
        step="any"
        value={Math.min(nowT, duration)}
        onChange={(e) => props.onSeek(Number(e.target.value))}
        className="h-1.5 flex-1 cursor-pointer accent-accent"
      />
      <label className="flex items-center gap-1.5 text-xs text-muted">
        speed
        <select
          aria-label="speed"
          value={speed}
          onChange={(e) => props.onSpeed(Number(e.target.value))}
          className="rounded-md border border-line-strong bg-panel-2 px-2 py-1 text-xs text-text"
        >
          {SPEEDS.map((s) => (
            <option key={s} value={s}>
              {s}×
            </option>
          ))}
        </select>
      </label>
    </div>
  );
}
