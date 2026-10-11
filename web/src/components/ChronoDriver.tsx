"use client";

import { useEffect } from "react";
import { addFrameHook } from "@/engine/loop";
import { clamp, smoothstep } from "@/engine/math";
import { engine } from "@/engine/store";
import { useWorld } from "@/engine/useWorld";

export const BRAND_COLOR: Record<string, string> = {
  ouka: "#ff9fc4",
  cherry: "#ff6b8b",
  alpha: "#8e8e93",
  aureum: "#ffc35a",
  astraea: "#a68bff",
  tsubomi: "#8fe3b0",
  halia: "#d9b56a",
  corvus: "#2997ff",
  noctua: "#ffb340",
};

/**
 * Puts the camera on the orbital path of time: milestones become beacons along the path, and
 * scrolling through `targetId` moves the camera from `from` to `to` (path parameters, 0..1).
 * Unscoped, the camera rides the path for as long as the page is mounted; `scoped`, only while
 * the section is on screen, easing on as it arrives and off as it leaves (the home page, where
 * time is one realm among six). Scroll is read from the engine, which Lenis writes every frame.
 */
export function ChronoDriver({
  nodes,
  targetId,
  from = 0.02,
  to = 0.5,
  weight = 1,
  scoped = false,
}: {
  nodes: { u: number; color: string }[];
  targetId: string;
  from?: number;
  to?: number;
  weight?: number;
  scoped?: boolean;
}) {
  const world = useWorld();
  const key = JSON.stringify(nodes);

  useEffect(() => {
    if (world === null) return;
    const list = JSON.parse(key) as { u: number; color: string }[];
    world.chrono.setNodes(
      list.map((n) => n.u),
      list.map((n) => n.color),
    );
  }, [world, key]);

  useEffect(() => {
    if (!scoped) engine.splineWeightTarget = weight;
    let top = 0;
    let full = 1;
    let height = 1;
    const measure = (): void => {
      const el = document.getElementById(targetId);
      if (el === null) return;
      const r = el.getBoundingClientRect();
      top = r.top + window.scrollY;
      full = r.height;
      height = Math.max(1, r.height - window.innerHeight * 0.5);
    };
    measure();
    const ro = new ResizeObserver(measure);
    const el = document.getElementById(targetId);
    if (el !== null) ro.observe(el);
    const vh = { h: window.innerHeight };
    const onResize = (): void => {
      vh.h = window.innerHeight;
    };
    window.addEventListener("resize", onResize, { passive: true });
    // The camera parameter follows scroll, inside the shared frame loop (no second rAF).
    const unhook = addFrameHook(() => {
      const y = engine.scrollY;
      const p = clamp((y - top + vh.h * 0.25) / height, 0, 1);
      engine.splineT = from + (to - from) * p;
      if (scoped) {
        // 0 → 1 as the section's top climbs the viewport; 1 → 0 as its bottom leaves the top.
        const arriving = (y + vh.h - top) / vh.h;
        const leaving = (top + full - y) / vh.h;
        engine.splineWeightTarget = weight * smoothstep(0.3, 0.95, arriving) * smoothstep(0.05, 0.7, leaving);
      }
    });
    return () => {
      unhook();
      window.removeEventListener("resize", onResize);
      ro.disconnect();
      engine.splineWeightTarget = 0;
    };
  }, [targetId, from, to, weight, scoped]);

  return null;
}
