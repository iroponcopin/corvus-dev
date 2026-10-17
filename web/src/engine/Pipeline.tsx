"use client";

import { useFrame, useThree } from "@react-three/fiber";
import { useEffect } from "react";
import type { WebGLRenderer } from "three";
import { damp } from "./math";
import { engine } from "./store";
import { updateTracked } from "./tracked";
import { views } from "./views";

/** Adaptive resolution: step the DPR down when frames run long, back up when there is room. */
const quality = {
  minDelta: 16.7,
  minDeltaAge: 0,
  avgDelta: 16.7,
  slowFor: 0,
  fastFor: 0,
  maxDpr: 2,
};

function adapt(dt: number, setDpr: (dpr: number) => void): void {
  const ms = dt * 1000;
  quality.minDeltaAge += dt;
  if (ms < quality.minDelta || quality.minDeltaAge > 3) {
    quality.minDelta = Math.max(4, ms);
    quality.minDeltaAge = 0;
  }
  quality.avgDelta = damp(quality.avgDelta, ms, 3, dt);
  const ratio = quality.avgDelta / quality.minDelta;
  if (ratio > 1.3) {
    quality.slowFor += dt;
    quality.fastFor = 0;
  } else if (ratio < 1.08) {
    quality.fastFor += dt;
    quality.slowFor = 0;
  } else {
    quality.slowFor = 0;
    quality.fastFor = 0;
  }
  if (quality.slowFor > 1.5) {
    quality.slowFor = 0;
    if (engine.dpr > 1.01) {
      const next = Math.max(1, engine.dpr - 0.25);
      engine.dpr = next;
      setDpr(next);
    } else if (engine.quality > 0.5) {
      engine.quality = 0.5;
    }
  } else if (quality.fastFor > 6) {
    quality.fastFor = 0;
    if (engine.quality < 1) engine.quality = 1;
    else if (engine.dpr < quality.maxDpr - 0.01) {
      const next = Math.min(quality.maxDpr, engine.dpr + 0.25);
      engine.dpr = next;
      setDpr(next);
    }
  }
}

function renderViews(gl: WebGLRenderer, height: number): void {
  let scissoring = false;
  for (let i = 0; i < views.length; i++) {
    const v = views[i]!;
    const t = v.tracked;
    if (!t.visible) continue;
    if (v.beforeRender !== null) v.beforeRender(engine.dt, v);
    const aspect = t.width / Math.max(1, t.height);
    if (Math.abs(aspect - v.aspect) > 1e-4) {
      v.aspect = aspect;
      v.camera.aspect = aspect;
      v.camera.updateProjectionMatrix();
    }
    const x = t.screenLeft;
    const y = height - (t.screenTop + t.height);
    gl.setViewport(x, y, t.width, t.height);
    gl.setScissor(x, y, t.width, t.height);
    if (!scissoring) {
      gl.setScissorTest(true);
      scissoring = true;
    }
    gl.clearDepth();
    gl.render(v.scene, v.camera);
  }
  if (scissoring) gl.setScissorTest(false);
}

/**
 * Takes over rendering (priority 1): clear the canvas to transparent, then draw every visible
 * viewport inside its element (the 3D stages of the realms). Counts draw calls across the frame.
 */
export function Pipeline(): null {
  const gl = useThree((s) => s.gl);
  const setDpr = useThree((s) => s.setDpr);

  useEffect(() => {
    gl.autoClear = false;
    gl.info.autoReset = false;
    quality.maxDpr = Math.min(window.devicePixelRatio || 1, 2);
    engine.dpr = quality.maxDpr;
    setDpr(engine.dpr);
  }, [gl, setDpr]);

  useFrame((state) => {
    const w = state.size.width;
    const h = state.size.height;
    engine.width = w;
    engine.height = h;
    adapt(engine.dt, setDpr);

    // Measure the stages on screen (their boxes, and whether they are visible) before drawing them.
    updateTracked(engine.scrollY, w, h);
    gl.info.reset();
    gl.setRenderTarget(null);
    gl.setViewport(0, 0, w, h);
    gl.setClearColor(0x000000, 0);
    gl.clear(true, true, false);
    renderViews(gl, h);

    engine.drawCalls = gl.info.render.calls;
    engine.triangles = gl.info.render.triangles;
    if (engine.ready === 0) engine.ready = 1;
  }, 1);

  return null;
}
