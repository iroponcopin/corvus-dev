"use client";

import { useEffect, useRef } from "react";
import { addFrameHook } from "@/engine/loop";
import { asset } from "@/lib/site";
import { bgFrameUrl, BG_ORDER, eagleFrameUrl, EAGLE_ORDER } from "./frames";
import { emptyVao, FrameStore, program } from "./gl";
import { BG_FRAG, EAGLE_FRAG, VERT } from "./shaders";
import { QualityManager } from "./quality";
import { BG_COUNT, clamp01, coverScale, type Pose, poseAt, smooth, staticPose, sunOnScreen } from "./timeline";

const EAGLE_W = 921;
const EAGLE_H = 1400;
const MAX_DPR = 1.5;

type Uniforms = Record<string, WebGLUniformLocation | null>;

function uniforms(gl: WebGL2RenderingContext, prog: WebGLProgram, names: readonly string[]): Uniforms {
  const out: Uniforms = {};
  for (const n of names) out[n] = gl.getUniformLocation(prog, n);
  return out;
}

interface Renderer {
  gl: WebGL2RenderingContext;
  prog: WebGLProgram;
  vao: WebGLVertexArrayObject;
  u: Uniforms;
  store: FrameStore;
}

/** The background renderer, or null when its context or shaders cannot be made. */
function createBg(canvas: HTMLCanvasElement, small: boolean, onChange: () => void): Renderer | null {
  const gl = canvas.getContext("webgl2", { alpha: false, antialias: false, depth: false, stencil: false, powerPreference: "high-performance" });
  if (gl === null) return null;
  try {
    const prog = program(gl, VERT, BG_FRAG);
    const names = ["uA", "uB", "uMix", "uRes", "uScale", "uSun", "uBlurPx", "uTime", "uGrain", "uCA", "uMist"];
    const u = uniforms(gl, prog, names);
    gl.useProgram(prog);
    gl.uniform1i(u.uA ?? null, 0);
    gl.uniform1i(u.uB ?? null, 1);
    const store = new FrameStore(gl, {
      count: BG_COUNT,
      capacity: small ? 40 : 20,
      premultiply: false,
      url: (i) => bgFrameUrl(i, small),
      onChange,
    });
    return { gl, prog, vao: emptyVao(gl), u, store };
  } catch {
    return null;
  }
}

/** The eagle renderer (premultiplied output), or null. */
function createEagle(canvas: HTMLCanvasElement, onChange: () => void): Renderer | null {
  const gl = canvas.getContext("webgl2", { alpha: true, premultipliedAlpha: true, antialias: false, depth: false, stencil: false });
  if (gl === null) return null;
  try {
    const prog = program(gl, VERT, EAGLE_FRAG);
    const u = uniforms(gl, prog, ["uTex", "uRes", "uTexel", "uLight", "uBright", "uRim", "uGrain", "uTime"]);
    gl.useProgram(prog);
    gl.uniform1i(u.uTex ?? null, 0);
    gl.viewport(0, 0, EAGLE_W, EAGLE_H);
    const store = new FrameStore(gl, {
      count: EAGLE_ORDER.length,
      capacity: 24,
      premultiply: true,
      url: eagleFrameUrl,
      onChange,
    });
    return { gl, prog, vao: emptyVao(gl), u, store };
  } catch {
    return null;
  }
}

/**
 * Act I of the home page: a scroll-driven nature cinema. A sticky stage shows a drone shot over a sea of
 * clouds at sunrise (the background, scrubbed frame by frame), the word HALIA in a serif, and a bald eagle
 * that rises into the frame and turns to profile, drawn in front of the title. Progress p runs through
 * the 400vh section. Without WebGL 2 the same stages fall back to plain images.
 */
export function NaturalCinemaStage({ title, tagline, credit, hint }: { title: string; tagline: string; credit: string; hint: string }) {
  const sectionRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const bgCanvasRef = useRef<HTMLCanvasElement>(null);
  const bgImgRef = useRef<HTMLImageElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const taglineRef = useRef<HTMLParagraphElement>(null);
  const hintRef = useRef<HTMLParagraphElement>(null);
  const eagleRef = useRef<HTMLDivElement>(null);
  const eagleCanvasRef = useRef<HTMLCanvasElement>(null);
  const eagleImgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const section = sectionRef.current;
    const stage = stageRef.current;
    const bgCanvas = bgCanvasRef.current;
    const bgImg = bgImgRef.current;
    const titleEl = titleRef.current;
    const taglineEl = taglineRef.current;
    const hintEl = hintRef.current;
    const eagle = eagleRef.current;
    const eagleCanvas = eagleCanvasRef.current;
    const eagleImg = eagleImgRef.current;
    if (!section || !stage || !bgCanvas || !bgImg || !titleEl || !taglineEl || !hintEl || !eagle || !eagleCanvas || !eagleImg) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const small = window.innerWidth < 768 || window.devicePixelRatio * window.innerWidth < 1600;
    const quality = new QualityManager();
    if (reduced) section.dataset.static = "true";

    let disposed = false;
    let active = true;
    let dirty = true;
    let resize = true;
    let mode: "gl" | "img" = "img";
    let bg: Renderer | null = null;
    let eg: Renderer | null = null;
    let lastBgImg = "";
    let lastEagleImg = "";

    const markDirty = (): void => {
      dirty = true;
    };

    bg = createBg(bgCanvas, small, markDirty);
    eg = bg === null ? null : createEagle(eagleCanvas, markDirty);
    if (bg !== null && eg !== null) {
      mode = "gl";
      stage.dataset.mode = "gl";
      // The first frame is loaded before anything else; the rest follow in footage order.
      void bg.store.load(BG_ORDER, 3);
      void eg.store.load(EAGLE_ORDER, 2);
    } else {
      // No WebGL 2: the posters become plain image layers.
      bg?.gl.getExtension("WEBGL_lose_context")?.loseContext();
      eg?.gl.getExtension("WEBGL_lose_context")?.loseContext();
      bg = null;
      eg = null;
      stage.dataset.mode = "img";
      lastBgImg = bgImg.getAttribute("src") ?? "";
    }

    const sizeBg = (r: Renderer): void => {
      const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
      const w = Math.max(2, Math.round(stage.clientWidth * dpr * quality.scale));
      const h = Math.max(2, Math.round(stage.clientHeight * dpr * quality.scale));
      if (bgCanvas.width !== w || bgCanvas.height !== h) {
        bgCanvas.width = w;
        bgCanvas.height = h;
        r.gl.viewport(0, 0, w, h);
      }
    };

    const drawBg = (r: Renderer, pose: Pose, effects: boolean): boolean => {
      const fi = pose.bg;
      const a0 = Math.floor(fi);
      const a1 = Math.min(a0 + 1, BG_COUNT - 1);
      const m = fi - a0;
      r.store.setProtected([0, a0, a1]);
      r.store.request(a0);
      r.store.request(a1);
      for (let k = a0 - 2; k <= a1 + 2; k++) if (k >= 0 && k < BG_COUNT) r.store.request(k);
      const A = r.store.nearest(a0);
      if (A === null) return false;
      const both = r.store.has(a0) && r.store.has(a1);
      const B = both ? a1 : A;
      const ta = r.store.get(A);
      const tb = r.store.get(B);
      if (ta === null || tb === null) return false;
      const gl = r.gl;
      const w = bgCanvas.width;
      const h = bgCanvas.height;
      const aspect = w / h;
      const [sx, sy] = coverScale(aspect);
      const [px, py] = sunOnScreen(aspect);
      gl.useProgram(r.prog);
      gl.bindVertexArray(r.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, ta);
      gl.activeTexture(gl.TEXTURE1);
      gl.bindTexture(gl.TEXTURE_2D, tb);
      const u = r.u;
      gl.uniform1f(u.uMix ?? null, both ? m : 0);
      gl.uniform2f(u.uRes ?? null, w, h);
      gl.uniform2f(u.uScale ?? null, sx, sy);
      gl.uniform2f(u.uSun ?? null, px, py);
      gl.uniform1f(u.uBlurPx ?? null, pose.blur * 0.0075 * h);
      gl.uniform1f(u.uTime ?? null, performance.now() / 1000);
      gl.uniform1f(u.uGrain ?? null, effects ? 0.022 : 0);
      gl.uniform1f(u.uCA ?? null, effects ? 1 : 0);
      gl.uniform1f(u.uMist ?? null, effects ? 1 : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      return true;
    };

    const drawEagle = (r: Renderer, pose: Pose, effects: boolean): void => {
      const e = pose.eagle;
      r.store.setProtected([0, e]);
      r.store.request(e);
      r.store.request(Math.min(e + 1, EAGLE_ORDER.length - 1));
      const E = r.store.nearest(e);
      if (E === null) return;
      const tex = r.store.get(E);
      if (tex === null) return;
      const gl = r.gl;
      gl.useProgram(r.prog);
      gl.bindVertexArray(r.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      const u = r.u;
      gl.uniform2f(u.uRes ?? null, EAGLE_W, EAGLE_H);
      gl.uniform2f(u.uTexel ?? null, 1 / EAGLE_W, 1 / EAGLE_H);
      gl.uniform2f(u.uLight ?? null, pose.light[0], pose.light[1]);
      gl.uniform1f(u.uBright ?? null, 0.66);
      gl.uniform1f(u.uRim ?? null, 0.9);
      gl.uniform1f(u.uGrain ?? null, effects ? 0.015 : 0);
      gl.uniform1f(u.uTime ?? null, performance.now() / 1000);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    const io = new IntersectionObserver(
      (entries) => {
        active = entries.some((x) => x.isIntersecting);
      },
      { rootMargin: "120px 0px" },
    );
    io.observe(section);
    const ro = new ResizeObserver(() => {
      resize = true;
      markDirty();
    });
    ro.observe(stage);

    const removeHook = addFrameHook((dt) => {
      if (disposed || !active) return;
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const narrow = vw < 768;
      const sw = stage.clientWidth;
      const sh = stage.clientHeight;
      if (sw === 0 || sh === 0) return;
      const sunScreen = sunOnScreen(sw / sh);
      const rect = section.getBoundingClientRect();
      const span = Math.max(1, section.offsetHeight - vh);
      const p = reduced ? 1 : clamp01(-rect.top / span);
      const pose = reduced ? staticPose(sw, sh, narrow, sunScreen) : poseAt(p, sw, sh, narrow, sunScreen);
      if (reduced && !dirty) return;
      dirty = false;

      // Typography: the title spaces in as the eagle comes; the hint leaves at the first scroll.
      titleEl.style.letterSpacing = `${pose.letter}em`;
      titleEl.style.paddingLeft = `${pose.letter}em`;
      taglineEl.style.opacity = String(0.55 + 0.45 * smooth(0.0, 0.25, p));
      hintEl.style.opacity = String(1 - smooth(0, 0.05, p));

      // The eagle layer, placed in CSS pixels.
      eagle.style.transform = `translate3d(${pose.eagleLeft.toFixed(1)}px, ${pose.eagleTop.toFixed(1)}px, 0)`;
      eagle.style.width = `${pose.eagleW.toFixed(1)}px`;
      eagle.style.height = `${pose.eagleH.toFixed(1)}px`;
      eagle.style.opacity = pose.eagleAlpha.toFixed(3);
      eagle.style.visibility = pose.eagleAlpha > 0.001 ? "visible" : "hidden";

      const effects = quality.effects && !reduced;
      if (mode === "gl" && bg !== null && eg !== null) {
        if (resize) {
          resize = false;
          sizeBg(bg);
        }
        const drew = drawBg(bg, pose, effects);
        if (drew) stage.dataset.ready = "true";
        if (pose.eagleAlpha > 0.001) drawEagle(eg, pose, effects);
        if (!reduced && quality.sample(dt * 1000)) {
          resize = true;
        }
        return;
      }

      // Image fallback: the same frames as plain images.
      const bgSrc = bgFrameUrl(Math.round(pose.bg), small);
      if (bgSrc !== lastBgImg) {
        lastBgImg = bgSrc;
        bgImg.src = bgSrc;
      }
      const eSrc = eagleFrameUrl(pose.eagle);
      if (eSrc !== lastEagleImg) {
        lastEagleImg = eSrc;
        eagleImg.src = eSrc;
      }
      stage.dataset.ready = "true";
    });

    return () => {
      disposed = true;
      removeHook();
      io.disconnect();
      ro.disconnect();
      bg?.store.dispose();
      eg?.store.dispose();
      if (bg !== null) bg.gl.deleteProgram(bg.prog);
      if (eg !== null) eg.gl.deleteProgram(eg.prog);
    };
  }, []);

  return (
    <section ref={sectionRef} className="cin-section" aria-labelledby="cin-title" data-static="false">
      <div ref={stageRef} className="cin-stage" data-mode="" data-ready="false">
        {/* The poster is also the image layer of the fallback, so it stays a plain img (the footage is served as-is). */}
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          ref={bgImgRef}
          className="cin-bg-img"
          src={asset("cinema/act1/bg/f001.webp")}
          alt=""
          width={1920}
          height={1080}
          fetchPriority="high"
          decoding="async"
        />
        <canvas ref={bgCanvasRef} className="cin-bg-canvas" aria-hidden="true" />
        <div className="cin-veil" aria-hidden="true" />
        <div className="cin-copy">
          <h1 id="cin-title" ref={titleRef} className="cin-title">
            {title}
          </h1>
          <p ref={taglineRef} className="cin-tagline">
            {tagline}
          </p>
        </div>
        <div ref={eagleRef} className="cin-eagle" aria-hidden="true">
          <canvas ref={eagleCanvasRef} className="cin-eagle-canvas" width={EAGLE_W} height={EAGLE_H} />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img ref={eagleImgRef} className="cin-eagle-img" src={asset("cinema/act1/eagle/h001.webp")} alt="" />
        </div>
        <p ref={hintRef} className="cin-hint" aria-hidden="true">
          {hint}
        </p>
        <p className="cin-credit" dir="ltr">
          {credit}
        </p>
      </div>
    </section>
  );
}
