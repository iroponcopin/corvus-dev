"use client";

import { useEffect, useRef } from "react";
import { addFrameHook } from "@/engine/loop";
import { asset } from "@/lib/site";
import {
  ACT2_ORDER,
  ACT3_ORDER,
  act2FrameUrl,
  act3FrameUrl,
  bgFrameUrl,
  BG_ORDER,
  crow3FrameUrl,
  CROW3_ORDER,
  crowFrameUrl,
  CROW_ORDER,
  eagleFrameUrl,
  EAGLE_ORDER,
} from "./frames";
import { emptyVao, FrameStore, program } from "./gl";
import { BG_FRAG, CROW_FRAG, EAGLE_FRAG, VERT } from "./shaders";
import { QualityManager } from "./quality";
import {
  ACT1_VH,
  ACT2_COUNT,
  ACT2_VH,
  ACT3_COUNT,
  ACT3_VH,
  BG_COUNT,
  clamp01,
  coverScale,
  CROW3_COUNT,
  CROW_COUNT,
  EAGLE_COUNT,
  type CrowPose,
  type Pair,
  type Pose,
  poseAt,
  smooth,
  staticPose,
  sunOnScreen,
} from "./timeline";

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
  /** The Act II background (background renderer), and the close crow (crow renderer). */
  store2?: FrameStore;
  /** The Act III headland (background renderer), and the close crow's frames (crow renderer). */
  store3?: FrameStore;
}

/** The background renderer (all three acts' footage), or null when its context or shaders cannot be made. */
function createBg(canvas: HTMLCanvasElement, small: boolean, onChange: () => void): Renderer | null {
  const gl = canvas.getContext("webgl2", { alpha: false, antialias: false, depth: false, stencil: false, powerPreference: "high-performance" });
  if (gl === null) return null;
  try {
    const prog = program(gl, VERT, BG_FRAG);
    const names = [
      "uA", "uB", "uMix", "uC", "uD", "uMix2", "uE", "uF", "uMix3", "uDis3", "uDusk", "uDis", "uFog", "uTeal", "uSunAmt",
      "uRes", "uScale", "uSun", "uBlurPx", "uTime", "uGrain", "uCA", "uMist",
    ];
    const u = uniforms(gl, prog, names);
    gl.useProgram(prog);
    gl.uniform1i(u.uA ?? null, 0);
    gl.uniform1i(u.uB ?? null, 1);
    gl.uniform1i(u.uC ?? null, 2);
    gl.uniform1i(u.uD ?? null, 3);
    gl.uniform1i(u.uE ?? null, 4);
    gl.uniform1i(u.uF ?? null, 5);
    const capacity = small ? 40 : 16;
    const store = new FrameStore(gl, { count: BG_COUNT, capacity, premultiply: false, url: (i) => bgFrameUrl(i, small), onChange });
    const store2 = new FrameStore(gl, { count: ACT2_COUNT, capacity, premultiply: false, url: (i) => act2FrameUrl(i, small), onChange });
    const store3 = new FrameStore(gl, { count: ACT3_COUNT, capacity, premultiply: false, url: (i) => act3FrameUrl(i, small), onChange });
    return { gl, prog, vao: emptyVao(gl), u, store, store2, store3 };
  } catch {
    return null;
  }
}

/** The crow renderer: premultiplied output, on the full-stage canvas (two crows: Act II and the close crow of Act III). */
function createCrow(canvas: HTMLCanvasElement, onChange: () => void): Renderer | null {
  const gl = canvas.getContext("webgl2", { alpha: true, premultipliedAlpha: true, antialias: false, depth: false, stencil: false });
  if (gl === null) return null;
  try {
    const prog = program(gl, VERT, CROW_FRAG);
    const u = uniforms(gl, prog, ["uTex", "uRes", "uBox", "uAlpha", "uWisp", "uTime", "uDusk"]);
    gl.useProgram(prog);
    gl.uniform1i(u.uTex ?? null, 0);
    const store = new FrameStore(gl, { count: CROW_COUNT, capacity: 40, premultiply: true, url: crowFrameUrl, onChange });
    const store3 = new FrameStore(gl, { count: CROW3_COUNT, capacity: 24, premultiply: true, url: crow3FrameUrl, onChange });
    return { gl, prog, vao: emptyVao(gl), u, store, store3 };
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
    const store = new FrameStore(gl, { count: EAGLE_COUNT, capacity: 24, premultiply: true, url: eagleFrameUrl, onChange });
    return { gl, prog, vao: emptyVao(gl), u, store };
  } catch {
    return null;
  }
}

interface Picked {
  ta: WebGLTexture;
  tb: WebGLTexture;
  mix: number;
}

/** Requests the frames of a pair, and returns the textures to draw now (the nearest decoded ones while one is missing). */
function pick(store: FrameStore, pair: Pair, count: number): Picked | null {
  const a0 = pair.a;
  const a1 = pair.b;
  store.setProtected([0, a0, a1]);
  store.request(a0);
  store.request(a1);
  for (let k = a0 - 2; k <= a1 + 2; k++) if (k >= 0 && k < count) store.request(k);
  const A = store.nearest(a0);
  if (A === null) return null;
  const both = store.has(a0) && store.has(a1);
  const B = both ? a1 : A;
  const ta = store.get(A);
  const tb = store.get(B);
  if (ta === null || tb === null) return null;
  return { ta, tb, mix: both ? pair.m : 0 };
}

/**
 * The cinema: one scroll story in three acts. Act I: a drone shot over the clouds scrubs while the eagle rises to
 * profile in front of HALIA. Act II: the cloud dissolves into a forest, CORVUS comes in, and a crow rises in front of
 * it. Act III: a headland at dusk, AURORA CORVUS, and a close crow entering on the right. The altitude stream closes
 * the story. Without WebGL 2 the same stages are plain images.
 */
export function NaturalCinemaStage({
  title,
  title2,
  title3,
  tagline,
  tagline2,
  tagline3,
  credit,
  hint,
}: {
  title: string;
  title2: string;
  title3: string;
  tagline: string;
  tagline2: string;
  tagline3: string;
  credit: string;
  hint: string;
}) {
  const sectionRef = useRef<HTMLElement>(null);
  const stageRef = useRef<HTMLDivElement>(null);
  const bgCanvasRef = useRef<HTMLCanvasElement>(null);
  const bgImgRef = useRef<HTMLImageElement>(null);
  const titleRef = useRef<HTMLHeadingElement>(null);
  const taglineRef = useRef<HTMLParagraphElement>(null);
  const title2Ref = useRef<HTMLHeadingElement>(null);
  const tagline2Ref = useRef<HTMLParagraphElement>(null);
  const title3Ref = useRef<HTMLHeadingElement>(null);
  const tagline3Ref = useRef<HTMLParagraphElement>(null);
  const hintRef = useRef<HTMLParagraphElement>(null);
  const eagleRef = useRef<HTMLDivElement>(null);
  const eagleCanvasRef = useRef<HTMLCanvasElement>(null);
  const eagleImgRef = useRef<HTMLImageElement>(null);
  const crowCanvasRef = useRef<HTMLCanvasElement>(null);
  const crowImgRef = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const section = sectionRef.current;
    const stage = stageRef.current;
    const bgCanvas = bgCanvasRef.current;
    const bgImg = bgImgRef.current;
    const titleEl = titleRef.current;
    const taglineEl = taglineRef.current;
    const title2El = title2Ref.current;
    const tagline2El = tagline2Ref.current;
    const title3El = title3Ref.current;
    const tagline3El = tagline3Ref.current;
    const hintEl = hintRef.current;
    const eagle = eagleRef.current;
    const eagleCanvas = eagleCanvasRef.current;
    const eagleImg = eagleImgRef.current;
    const crowCanvas = crowCanvasRef.current;
    const crowImg = crowImgRef.current;
    if (!section || !stage || !bgCanvas || !bgImg || !titleEl || !taglineEl || !title2El || !tagline2El) return;
    if (!title3El || !tagline3El || !hintEl || !eagle || !eagleCanvas || !eagleImg || !crowCanvas || !crowImg) return;

    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const small = window.innerWidth < 768 || window.devicePixelRatio * window.innerWidth <= 1100;
    const quality = new QualityManager();
    if (reduced) section.dataset.static = "true";

    let disposed = false;
    let active = true;
    let dirty = true;
    let resize = true;
    let mode: "gl" | "img" = "img";
    let bg: Renderer | null = null;
    let eg: Renderer | null = null;
    let cr: Renderer | null = null;
    let lastBgImg = "";
    let lastEagleImg = "";
    let lastCrowImg = "";

    const markDirty = (): void => {
      dirty = true;
    };

    bg = createBg(bgCanvas, small, markDirty);
    eg = bg === null ? null : createEagle(eagleCanvas, markDirty);
    cr = bg === null ? null : createCrow(crowCanvas, markDirty);
    if (bg !== null && eg !== null && cr !== null && bg.store2 !== undefined && bg.store3 !== undefined && cr.store3 !== undefined) {
      mode = "gl";
      stage.dataset.mode = "gl";
      void bg.store.load(BG_ORDER, 3);
      void bg.store2.load(ACT2_ORDER, 3);
      void bg.store3.load(ACT3_ORDER, 3);
      void eg.store.load(EAGLE_ORDER, 2);
      void cr.store.load(CROW_ORDER, 2);
      void cr.store3.load(CROW3_ORDER, 2);
    } else {
      // No WebGL 2: the posters become plain image layers.
      for (const r of [bg, eg, cr]) r?.gl.getExtension("WEBGL_lose_context")?.loseContext();
      bg = null;
      eg = null;
      cr = null;
      stage.dataset.mode = "img";
      lastBgImg = bgImg.getAttribute("src") ?? "";
    }

    const sizeCanvases = (r: Renderer): void => {
      const dpr = Math.min(window.devicePixelRatio || 1, MAX_DPR);
      const w = Math.max(2, Math.round(stage.clientWidth * dpr * quality.scale));
      const h = Math.max(2, Math.round(stage.clientHeight * dpr * quality.scale));
      if (bgCanvas.width !== w || bgCanvas.height !== h) {
        bgCanvas.width = w;
        bgCanvas.height = h;
        r.gl.viewport(0, 0, w, h);
        crowCanvas.width = w;
        crowCanvas.height = h;
        cr?.gl.viewport(0, 0, w, h);
      }
    };

    const drawBg = (r: Renderer, pose: Pose, effects: boolean): boolean => {
      const fi = pose.bg;
      const a0 = Math.floor(fi);
      const p1 = pose.dissolve < 0.999 ? pick(r.store, { a: a0, b: Math.min(a0 + 1, BG_COUNT - 1), m: fi - a0 }, BG_COUNT) : null;
      const p2 = pose.dissolve > 0.001 && r.store2 !== undefined ? pick(r.store2, pose.bg2, ACT2_COUNT) : null;
      const p3 = pose.dissolve3 > 0.001 && r.store3 !== undefined ? pick(r.store3, pose.bg3, ACT3_COUNT) : null;
      if (p1 === null && p2 === null && p3 === null) return false;
      // The lowest layer that is decoded stands in for a missing one (a layer with no weight never shows).
      const s1 = p1 ?? p2 ?? p3;
      const s2 = p2 ?? p1 ?? p3;
      const s3 = p3 ?? s2;
      if (s1 === null || s2 === null || s3 === null) return false;
      const dis = p1 === null ? 1 : p2 === null ? 0 : pose.dissolve;
      const dis3 = p3 === null ? 0 : pose.dissolve3;
      const gl = r.gl;
      const w = bgCanvas.width;
      const h = bgCanvas.height;
      const aspect = w / h;
      const [sx, sy] = coverScale(aspect);
      const [px, py] = sunOnScreen(aspect);
      gl.useProgram(r.prog);
      gl.bindVertexArray(r.vao);
      const bind = (unit: number, tex: WebGLTexture): void => {
        gl.activeTexture(gl.TEXTURE0 + unit);
        gl.bindTexture(gl.TEXTURE_2D, tex);
      };
      bind(0, s1.ta);
      bind(1, s1.tb);
      bind(2, s2.ta);
      bind(3, s2.tb);
      bind(4, s3.ta);
      bind(5, s3.tb);
      const u = r.u;
      gl.uniform1f(u.uMix ?? null, p1?.mix ?? 0);
      gl.uniform1f(u.uMix2 ?? null, p2?.mix ?? 0);
      gl.uniform1f(u.uMix3 ?? null, p3?.mix ?? 0);
      gl.uniform1f(u.uDis ?? null, dis);
      gl.uniform1f(u.uDis3 ?? null, dis3);
      gl.uniform1f(u.uDusk ?? null, pose.dusk);
      gl.uniform1f(u.uFog ?? null, pose.fog);
      gl.uniform1f(u.uTeal ?? null, pose.teal);
      gl.uniform1f(u.uSunAmt ?? null, (1 - dis) * (1 - dis3));
      gl.uniform2f(u.uRes ?? null, w, h);
      gl.uniform2f(u.uScale ?? null, sx, sy);
      gl.uniform2f(u.uSun ?? null, px, py);
      gl.uniform1f(u.uBlurPx ?? null, pose.blur * 0.0075 * h);
      gl.uniform1f(u.uTime ?? null, performance.now() / 1000);
      gl.uniform1f(u.uGrain ?? null, effects ? 0.022 : 0);
      gl.uniform1f(u.uCA ?? null, effects ? 1 : 0);
      gl.uniform1f(u.uMist ?? null, effects ? (1 - dis) * (1 - dis3) : 0);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
      return true;
    };

    const drawEagle = (r: Renderer, pose: Pose): void => {
      const e = pose.eagle;
      r.store.setProtected([0, e]);
      r.store.request(e);
      r.store.request(Math.min(e + 1, EAGLE_COUNT - 1));
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
      gl.uniform1f(u.uRim ?? null, 0.225);
      gl.uniform1f(u.uGrain ?? null, quality.effects && !reduced ? 0.015 : 0);
      gl.uniform1f(u.uTime ?? null, performance.now() / 1000);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    /** One crow drawn into its box on the full-stage canvas (blended over what is already there). */
    const drawOneCrow = (r: Renderer, store: FrameStore, c: CrowPose, wisp: number, dusk: number): void => {
      if (c.alpha <= 0.001) return;
      const fi = c.frame;
      store.setProtected([0, fi]);
      store.request(fi);
      const A = store.nearest(fi);
      if (A === null) return;
      const tex = store.get(A);
      if (tex === null) return;
      const gl = r.gl;
      const sx = crowCanvas.width / stage.clientWidth;
      const sy = crowCanvas.height / stage.clientHeight;
      gl.useProgram(r.prog);
      gl.bindVertexArray(r.vao);
      gl.activeTexture(gl.TEXTURE0);
      gl.bindTexture(gl.TEXTURE_2D, tex);
      const u = r.u;
      gl.uniform2f(u.uRes ?? null, crowCanvas.width, crowCanvas.height);
      gl.uniform4f(u.uBox ?? null, c.left * sx, c.top * sy, c.w * sx, c.h * sy);
      gl.uniform1f(u.uAlpha ?? null, c.alpha);
      gl.uniform1f(u.uWisp ?? null, quality.effects && !reduced ? wisp : 0);
      gl.uniform1f(u.uDusk ?? null, dusk);
      gl.uniform1f(u.uTime ?? null, performance.now() / 1000);
      gl.drawArrays(gl.TRIANGLES, 0, 3);
    };

    const drawCrows = (r: Renderer, pose: Pose): void => {
      const gl = r.gl;
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.ONE, gl.ONE_MINUS_SRC_ALPHA);
      gl.clearColor(0, 0, 0, 0);
      gl.clear(gl.COLOR_BUFFER_BIT);
      if (r.store3 !== undefined) drawOneCrow(r, r.store, pose.crow, pose.wisp, 0);
      if (r.store3 !== undefined) drawOneCrow(r, r.store3, pose.crow3, 0, 1);
      gl.disable(gl.BLEND);
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
      const scrolled = clamp01(-rect.top / span) * span;
      const dvh = scrolled / vh;
      const p = clamp01(dvh / ACT1_VH);
      const a = clamp01((dvh - ACT1_VH) / ACT2_VH);
      const c = clamp01((dvh - ACT1_VH - ACT2_VH) / ACT3_VH);
      const pose = reduced ? staticPose(sw, sh, narrow, sunScreen) : poseAt(p, a, c, sw, sh, narrow, sunScreen);
      if (reduced && !dirty) return;
      dirty = false;

      // Typography: each title spaces in with its own act; the hint leaves at the first scroll.
      titleEl.style.letterSpacing = `${pose.letter}em`;
      titleEl.style.paddingLeft = `${Math.max(0, pose.letter)}em`;
      titleEl.style.opacity = String(pose.title1);
      taglineEl.style.opacity = String(pose.title1);
      title2El.style.letterSpacing = `${pose.letter2}em`;
      title2El.style.paddingLeft = `${Math.max(0, pose.letter2)}em`;
      title2El.style.opacity = String(pose.title2);
      tagline2El.style.opacity = String(pose.title2);
      title3El.style.letterSpacing = `${pose.letter3}em`;
      title3El.style.paddingLeft = `${Math.max(0, pose.letter3)}em`;
      title3El.style.opacity = String(pose.title3);
      tagline3El.style.opacity = String(pose.title3);
      hintEl.style.opacity = String(1 - smooth(0, 0.05, p));

      // The eagle layer, placed in CSS pixels.
      eagle.style.transform = `translate3d(${pose.eagleLeft.toFixed(1)}px, ${pose.eagleTop.toFixed(1)}px, 0)`;
      eagle.style.width = `${pose.eagleW.toFixed(1)}px`;
      eagle.style.height = `${pose.eagleH.toFixed(1)}px`;
      eagle.style.opacity = pose.eagleAlpha.toFixed(3);
      eagle.style.visibility = pose.eagleAlpha > 0.001 ? "visible" : "hidden";

      const effects = quality.effects && !reduced;
      if (mode === "gl" && bg !== null && eg !== null && cr !== null) {
        if (resize) {
          resize = false;
          sizeCanvases(bg);
        }
        const drew = drawBg(bg, pose, effects);
        if (drew) stage.dataset.ready = "true";
        if (pose.eagleAlpha > 0.001) drawEagle(eg, pose);
        const crowOn = pose.crow.alpha > 0.001 || pose.crow3.alpha > 0.001 || pose.wisp > 0.001;
        crowCanvas.style.visibility = crowOn ? "visible" : "hidden";
        if (crowOn) drawCrows(cr, pose);
        if (!reduced && quality.sample(dt * 1000)) resize = true;
        return;
      }

      // Image fallback: the same frames as plain images (the Act III headland, else the Act II forest, else the cloud).
      const src =
        pose.dissolve3 > 0.5
          ? act3FrameUrl(Math.round(pose.bg3.a), small)
          : pose.dissolve > 0.5
            ? act2FrameUrl(Math.round(pose.bg2.a), small)
            : bgFrameUrl(Math.round(pose.bg), small);
      if (src !== lastBgImg) {
        lastBgImg = src;
        bgImg.src = src;
      }
      const eSrc = eagleFrameUrl(pose.eagle);
      if (eSrc !== lastEagleImg) {
        lastEagleImg = eSrc;
        eagleImg.src = eSrc;
      }
      const showC3 = pose.crow3.alpha > pose.crow.alpha;
      const crow = showC3 ? pose.crow3 : pose.crow;
      const cSrc = showC3 ? crow3FrameUrl(crow.frame) : crowFrameUrl(crow.frame);
      if (cSrc !== lastCrowImg) {
        lastCrowImg = cSrc;
        crowImg.src = cSrc;
      }
      crowImg.style.transform = `translate3d(${crow.left.toFixed(1)}px, ${crow.top.toFixed(1)}px, 0)`;
      crowImg.style.width = `${crow.w.toFixed(1)}px`;
      crowImg.style.height = `${crow.h.toFixed(1)}px`;
      crowImg.style.opacity = crow.alpha.toFixed(3);
      stage.dataset.ready = "true";
    });

    return () => {
      disposed = true;
      removeHook();
      io.disconnect();
      ro.disconnect();
      if (bg !== null) {
        bg.store.dispose();
        bg.store2?.dispose();
        bg.store3?.dispose();
        bg.gl.deleteProgram(bg.prog);
      }
      eg?.store.dispose();
      if (eg !== null) eg.gl.deleteProgram(eg.prog);
      cr?.store.dispose();
      cr?.store3?.dispose();
      if (cr !== null) cr.gl.deleteProgram(cr.prog);
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
        <div className="cin-copy cin-copy--2">
          <h2 ref={title2Ref} className="cin-title cin-title--2">
            {title2}
          </h2>
          <p ref={tagline2Ref} className="cin-tagline cin-tagline--2">
            {tagline2}
          </p>
        </div>
        <div className="cin-copy cin-copy--3">
          <h2 ref={title3Ref} className="cin-title cin-title--3">
            {title3}
          </h2>
          <p ref={tagline3Ref} className="cin-tagline cin-tagline--3">
            {tagline3}
          </p>
        </div>
        <div ref={eagleRef} className="cin-eagle" aria-hidden="true">
          <canvas ref={eagleCanvasRef} className="cin-eagle-canvas" width={EAGLE_W} height={EAGLE_H} />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img ref={eagleImgRef} className="cin-eagle-img" src={asset("cinema/act1/eagle/h001.webp")} alt="" />
        </div>
        <canvas ref={crowCanvasRef} className="cin-crow-canvas" aria-hidden="true" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img ref={crowImgRef} className="cin-crow-img" src={asset("cinema/act2/crow/c001.webp")} alt="" />
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
