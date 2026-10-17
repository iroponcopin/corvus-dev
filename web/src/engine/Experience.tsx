"use client";

import { Canvas, type RootState } from "@react-three/fiber";
import { useCallback, useEffect, useRef, useState } from "react";
import { setConsoleFunction } from "three";
import { installInput, webglVerdict } from "./input";
import { attachRoot, detachRoot, ensureLoop } from "./loop";
import { Pipeline } from "./Pipeline";
import { engine } from "./store";
import { SceneOut } from "./tunnel";

// React Three Fiber 9 still builds a THREE.Clock (deprecated since r183) for its own store. This
// site never reads that clock (the shared loop owns time and calls advance() itself), so that one
// notice is dropped; every other message from three passes through unchanged.
setConsoleFunction((type, message, ...params) => {
  if (type === "warn" && message.startsWith("THREE.Clock: This module has been deprecated")) return;
  // eslint-disable-next-line no-console -- forwards three's own log/warn/error calls as they were
  console[type](message, ...params);
});

/**
 * The persistent WebGL world behind every page: one context for the whole visit, fixed under
 * the document, never intercepting the pointer. Pages reach into it through the scene tunnel
 * and the realm anchors; without WebGL 2 (or with `?webgl=off`, Save-Data or a low-end device)
 * it is simply absent and every page still works as a document.
 */
export function Experience({ dir }: { dir: "ltr" | "rtl" }) {
  const [verdict, setVerdict] = useState<"pending" | "on" | "off">("pending");
  const root = useRef<RootState | null>(null);

  useEffect(() => {
    engine.mirror = dir === "rtl" ? -1 : 1;
  }, [dir]);

  useEffect(() => {
    ensureLoop();
    const v = webglVerdict();
    document.documentElement.dataset.webgl = v.ok ? "on" : "off";
    if (!v.ok) document.documentElement.dataset.webglReason = v.reason;
    setVerdict(v.ok ? "on" : "off");
    const media = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = (): void => {
      engine.reducedMotion = media.matches;
    };
    sync();
    media.addEventListener("change", sync);
    const uninstall = installInput();
    // ?debug exposes the live engine numbers (draw calls, frame cost) to tooling and tests.
    if (new URLSearchParams(window.location.search).has("debug")) {
      (window as unknown as { __acEngine?: typeof engine }).__acEngine = engine;
    }
    return () => {
      media.removeEventListener("change", sync);
      uninstall();
      if (root.current !== null) detachRoot(root.current);
    };
  }, []);

  const created = useCallback((state: RootState): void => {
    state.gl.setClearColor(0x000000, 0);
    root.current = state;
    attachRoot(state);
  }, []);

  if (verdict !== "on") return null;

  return (
    <div className="ac-world" aria-hidden="true">
      <Canvas
        frameloop="never"
        dpr={1}
        flat
        gl={{
          antialias: true,
          alpha: true,
          depth: true,
          stencil: false,
          powerPreference: "high-performance",
          preserveDrawingBuffer: false,
        }}
        camera={{ fov: 38, near: 0.1, far: 600, position: [0, 0, 16] }}
        resize={{ scroll: false, debounce: { scroll: 0, resize: 0 } }}
        onCreated={created}
        style={{ position: "absolute", inset: 0 }}
      >
        <Pipeline />
        <SceneOut />
      </Canvas>
    </div>
  );
}
