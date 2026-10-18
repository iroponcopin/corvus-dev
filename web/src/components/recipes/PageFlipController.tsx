"use client";

import { forwardRef, type ReactNode, useEffect, useImperativeHandle, useRef } from "react";

/**
 * A page turn. A leaf (the page being lifted) rotates about the spine: 0° at rest, 180° once turned, with its
 * shading darkening past 90°. A riffle is several leaves starting one after another, so a jump of many pages
 * reads as the pages being thumbed through. Progress is written straight to the leaves' transforms in the frame
 * loop, not through React state, so a turn costs no re-render.
 */

export interface FlipPlan {
  /** +1: the right page turns to the left (forward). -1: the left page turns to the right (back). */
  dir: 1 | -1;
  /** Proxy leaves: 1 for a turn, 3 to 5 for a riffle. */
  leaves: number;
  /** Milliseconds for the whole move (a riffle's leaves share it). */
  duration: number;
  /** The face the leaf lifts from, and the face it lands on. */
  front: ReactNode;
  back: ReactNode;
  /** A single column (narrow screens): the leaf covers the one page. */
  single?: boolean;
  /** The reader is dragging: progress comes from the handle and the plan waits for a release. */
  manual?: boolean;
}

export interface FlipHandle {
  /** Sets the turn's progress, 0 (at rest) to 1 (turned). */
  drag(progress: number): void;
  /** Completes the turn when committed, otherwise returns the page to rest. */
  release(commit: boolean): void;
}

interface Props {
  plan: FlipPlan;
  onDone: (committed: boolean) => void;
}

/** Stagger between the leaves of a riffle, as a fraction of the whole move. */
const STAGGER = 0.08;

function easeInOutCubic(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}

export const FlipLayer = forwardRef<FlipHandle, Props>(function FlipLayer({ plan, onDone }, ref) {
  const leafEls = useRef<(HTMLDivElement | null)[]>([]);
  const progress = useRef(0);
  const frame = useRef<number | null>(null);
  const doneRef = useRef(onDone);
  doneRef.current = onDone;

  const paint = (): void => {
    const n = plan.leaves;
    for (let i = 0; i < n; i++) {
      const el = leafEls.current[i];
      if (!el) continue;
      // Leaf i starts after i staggers; the last one lands with the whole move.
      const local = clamp01((progress.current - i * STAGGER) / (1 - (n - 1) * STAGGER));
      const eased = easeInOutCubic(local);
      const angle = -plan.dir * 180 * eased;
      el.style.transform = `rotateY(${angle.toFixed(2)}deg)`;
      el.style.setProperty("--shade", String(Math.max(0, (Math.abs(angle) - 90) / 90) * 0.45));
    }
  };

  const animate = (target: 0 | 1, duration: number, done: boolean): void => {
    if (frame.current !== null) cancelAnimationFrame(frame.current);
    const from = progress.current;
    const span = Math.abs(target - from);
    const start = performance.now();
    const total = Math.max(1, duration * span);
    const step = (now: number): void => {
      const t = clamp01((now - start) / total);
      progress.current = from + (target - from) * easeInOutCubic(t);
      paint();
      if (t < 1) {
        frame.current = requestAnimationFrame(step);
      } else {
        frame.current = null;
        progress.current = target;
        paint();
        if (done) doneRef.current(target === 1);
      }
    };
    if (span === 0) {
      if (done) doneRef.current(target === 1);
      return;
    }
    frame.current = requestAnimationFrame(step);
  };

  useImperativeHandle(
    ref,
    () => ({
      drag(p: number) {
        if (frame.current !== null) cancelAnimationFrame(frame.current);
        frame.current = null;
        progress.current = clamp01(p);
        paint();
      },
      release(commit: boolean) {
        animate(commit ? 1 : 0, plan.duration, true);
      },
    }),
    // The plan's geometry is read when the leaves are painted; a new plan remounts this layer.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [plan],
  );

  useEffect(() => {
    progress.current = 0;
    paint();
    if (!plan.manual) animate(1, plan.duration, true);
    return () => {
      if (frame.current !== null) cancelAnimationFrame(frame.current);
      frame.current = null;
    };
    // A plan runs once, from its start to its end: the layer is keyed by the plan.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const leaves = Array.from({ length: plan.leaves }, (_, i) => i);
  return (
    <div className={`tome-flip${plan.single ? " is-single" : ""}${plan.dir > 0 ? " is-fwd" : " is-back"}`} aria-hidden="true" inert>
      {leaves.map((i) => (
        <div
          key={i}
          ref={(el) => {
            leafEls.current[i] = el;
          }}
          className="tome-leaf"
          style={{ zIndex: 10 + i }}
        >
          <div className="tome-leaf-face tome-leaf-front">{plan.front}</div>
          <div className="tome-leaf-face tome-leaf-back">{plan.back}</div>
        </div>
      ))}
    </div>
  );
});
