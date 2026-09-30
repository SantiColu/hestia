import { useEffect, useRef, useState } from "react";

/** Seconds of animation for one orbit at speed ×1. */
const ORBIT_SECONDS = 30;
/** One orbit per minute: slow enough to follow the satellite in the local view. */
const DEFAULT_SPEED = 0.5;

export type OrbitClock = {
  /** s within the orbit, in [0, period). */
  time: number;
  playing: boolean;
  speed: number;
  setSpeed: (speed: number) => void;
  toggle: () => void;
  /** Jump to an instant and pause. */
  seek: (time: number) => void;
};

/** The instant shown of an animated orbit: it advances while playing, one orbit every
 * `ORBIT_SECONDS / speed` s. Switching views keeps it. */
export function useOrbitClock(period: number): OrbitClock {
  const [playing, setPlaying] = useState(true);
  const [speed, setSpeed] = useState(DEFAULT_SPEED);
  const [time, setTime] = useState(0);
  const last = useRef<number | null>(null);

  useEffect(() => {
    if (!playing || period <= 0) return;
    let frame = 0;
    const tick = (now: number) => {
      const previous = last.current ?? now;
      last.current = now;
      const rate = (period / ORBIT_SECONDS) * speed;
      setTime((t) => (t + ((now - previous) / 1000) * rate) % period);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => {
      cancelAnimationFrame(frame);
      last.current = null;
    };
  }, [playing, period, speed]);

  return {
    time: period > 0 ? time % period : 0,
    playing,
    speed,
    setSpeed,
    toggle: () => setPlaying((p) => !p),
    seek: (next) => {
      setPlaying(false);
      setTime(next);
    },
  };
}
