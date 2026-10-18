"use client";

import { useEffect, useRef } from "react";
import type { Shell } from "@/i18n/shell";

/** The loading screen's minimum time on screen, so its three lines can be read. */
const MIN_MS = 1600;
/** Guards from the template: the page counts as ready at 6 s whatever the network did, and the screen always lifts by 9 s. */
const READY_GUARD_MS = 6000;
const HARD_GUARD_MS = 9000;
/** Matches the .ac-loader transition in chrome.css; after it, the overlay is taken out of layout. */
const LIFT_MS = 1100;

/**
 * The editorial loading screen (the template's, in the Corvus palette and thirteen languages). Its visibility is decided
 * before first paint by the head script (data-loader="show" | "skip" | "done"), so it is shown once per session and never
 * under reduced motion. This component only lifts the screen when the page is ready, and never strands the page: the
 * ready guard and the hard guard both lift it, and a reload or a skip marks it "done" at once.
 */
export function LoadingScreen({ labels }: { labels: Shell["loader"] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    const root = document.documentElement;
    if (!el || root.dataset.loader !== "show") return;

    const timers: number[] = [];
    const started = performance.now();
    let lifted = false;

    const lift = (): void => {
      if (lifted) return;
      lifted = true;
      const wait = Math.max(0, MIN_MS - (performance.now() - started));
      timers.push(
        window.setTimeout(() => {
          el.classList.add("is-complete");
          el.setAttribute("aria-hidden", "true");
          timers.push(window.setTimeout(() => (root.dataset.loader = "done"), LIFT_MS));
        }, wait),
      );
    };

    const loaded = new Promise<void>((resolve) => {
      if (document.readyState === "complete") resolve();
      else window.addEventListener("load", () => resolve(), { once: true });
    });
    const fonts = document.fonts?.ready ?? Promise.resolve();
    void Promise.all([loaded, fonts]).then(() => requestAnimationFrame(lift));
    timers.push(window.setTimeout(lift, READY_GUARD_MS));
    timers.push(window.setTimeout(() => {
      if (!lifted) {
        lifted = true;
        el.classList.add("is-complete");
        root.dataset.loader = "done";
      }
    }, HARD_GUARD_MS));

    return () => {
      for (const t of timers) window.clearTimeout(t);
    };
  }, []);

  return (
    <div ref={ref} className="ac-loader" role="status" aria-live="polite" aria-label={labels.title}>
      <div className="ac-loader-top">
        <span>{labels.top}</span>
        <span className="ac-loader-muted">{labels.muted}</span>
      </div>
      <div className="ac-loader-center">
        <span className="ac-loader-eyebrow">{labels.eyebrow}</span>
        <span className="ac-loader-title">{labels.title}</span>
      </div>
      <div className="ac-loader-bottom">
        <span className="ac-loader-muted">{labels.bottom}</span>
        <span className="ac-loader-bar" aria-hidden="true" />
      </div>
    </div>
  );
}
