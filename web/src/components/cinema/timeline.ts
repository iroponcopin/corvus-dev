/**
 * The timeline of the cinema: one scroll section, two acts. Act I (the eagle, HALIA) runs over the first
 * ACT1_VH viewport heights; Act II (the forest, CORVUS, the crow) over the next ACT2_VH. Pure functions, so
 * the stage's DOM and GL code only reads numbers from here.
 */

/** Scroll, in viewport heights, of Act I and of Act II (the section is 8 viewport heights; 7 scroll). */
export const ACT1_VH = 3;
export const ACT2_VH = 4;

/** Act I background footage: f001..f113, indexed 0..112 here. */
export const BG_COUNT = 113;
/** Act I: bg frame index = p * BG_SPAN (112). */
export const BG_SPAN = 112;
/** Act I eagle footage: h001..h060, indexed 0..59. */
export const EAGLE_COUNT = 60;
/** Act II background footage: f001..f182, indexed 0..181. */
export const ACT2_COUNT = 182;
/** Act II crow footage: c001..c105, indexed 0..104. */
export const CROW_COUNT = 105;

/** Eagle frame size in pixels (921 x 1400). */
export const EAGLE_ASPECT = 921 / 1400;
/** Crow frame size in pixels (1260 x 580). */
export const CROW_ASPECT = 1260 / 580;
/** The footage's own aspect, 16 x 9. */
export const BG_ASPECT = 16 / 9;
/** The sun in background-frame coordinates (x, y down), measured on f080. */
export const SUN_IMAGE: readonly [number, number] = [0.51, 0.22];

/** Eagle frame coordinates after the mirror (the eagle faces left): eyes' midpoint, beak tip, top of the head. */
export const EYE_MID: readonly [number, number] = [0.47, 0.18];
export const BEAK_TIP: readonly [number, number] = [0.185, 0.3];
export const HEAD_TOP_Y = 0.107;

/**
 * Crow frame coordinates, measured on the final frame (c105): the bird is 37% of the frame's height and its centre
 * is at 53% of its width; its top sits at 29%.
 */
export const CROW_BODY_H = 0.37;
export const CROW_BODY_CX = 0.53;
/** The bird's final height in viewport heights (desktop, phones). Sized so the title stays readable. */
const CROW_FINAL_VH = 0.3;
const CROW_FINAL_VH_NARROW = 0.13;

export function clamp01(x: number): number {
  return x < 0 ? 0 : x > 1 ? 1 : x;
}

export function smooth(a: number, b: number, x: number): number {
  const t = clamp01((x - a) / (b - a));
  return t * t * (3 - 2 * t);
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export interface Pair {
  /** The two frames blended, and the blend (0..1). */
  a: number;
  b: number;
  m: number;
}

export interface CrowPose {
  left: number;
  top: number;
  w: number;
  h: number;
  /** Crow frame index. */
  frame: number;
  alpha: number;
}

export interface Pose {
  /** Act I background frame, fractional, 0..112. */
  bg: number;
  /** Depth of field strength, 0 (sharp) .. 1 (strong). */
  blur: number;
  /** HALIA letter-spacing (em) and opacity. */
  letter: number;
  title1: number;
  /** Act I eagle frame, integer 0..59, opacity, and box in CSS pixels. */
  eagle: number;
  eagleAlpha: number;
  eagleLeft: number;
  eagleTop: number;
  eagleW: number;
  eagleH: number;
  /** Eagle centre to sun, unit vector in screen space (x, y down). */
  light: [number, number];
  /** Transition and Act II: the dissolve from Act I to Act II (0..1), the mist, the cool grade. */
  dissolve: number;
  fog: number;
  teal: number;
  /** Act II background frames (fractional index into the 182) and the wisps' amount. */
  bg2: Pair;
  wisp: number;
  /** CORVUS letter-spacing (em) and opacity. */
  letter2: number;
  title2: number;
  crow: CrowPose;
}

/**
 * The Act II background: frames 0..88 scrub normally; the hard cut between f090 and f091 (indices 89 and 90) is a
 * cross-dissolve over ten steps; the rest of the second shot is stretched over the remaining steps.
 */
export function act2Pair(x: number): Pair {
  const CUT = 89;
  const WIN = 10;
  const N = ACT2_COUNT - 1;
  if (x < CUT) {
    const a = Math.floor(x);
    return { a, b: Math.min(a + 1, CUT), m: x - a };
  }
  if (x < CUT + WIN) return { a: CUT, b: CUT + 1, m: (x - CUT) / WIN };
  const y = CUT + 1 + (x - (CUT + WIN)) * ((N - (CUT + 1)) / (N - (CUT + WIN)));
  const a = Math.min(Math.floor(y), N - 1);
  return { a, b: Math.min(a + 1, N), m: y - a };
}

function crowPose(a: number, vw: number, vh: number, narrow: boolean): CrowPose {
  const rise = smooth(0.55, 1, a);
  const hFinal = (narrow ? CROW_FINAL_VH_NARROW : CROW_FINAL_VH) / CROW_BODY_H * vh;
  const h = lerp(0.55 * hFinal, hFinal, rise);
  const w = h * CROW_ASPECT;
  // The frame's bottom (the treetop's cut) stays beyond the viewport's bottom at every point.
  const bottom = lerp(vh + 0.9 * h, vh + 0.02 * vh, rise);
  const top = bottom - h;
  const cx = narrow ? 0.5 * vw : 0.68 * vw;
  return {
    left: cx - CROW_BODY_CX * w,
    top,
    w,
    h,
    frame: Math.round(clamp01((a - 0.55) / 0.45) * (CROW_COUNT - 1)),
    alpha: smooth(0.5, 0.6, a),
  };
}

/** The whole timeline at once: p = Act I progress (0..1), a = Act II progress (0..1). */
export function poseAt(p: number, a: number, vw: number, vh: number, narrow: boolean, sunScreen: [number, number]): Pose {
  // Act I: the eagle rises from the bottom-right; the beak lands on the end of the word.
  const te = smooth(0.3, 0.8, p);
  const zoom = 1 + 0.03 * smooth(0.8, 1, p);
  const hFinal = (narrow ? 0.95 : 1.15) * vh;
  const H0 = lerp(0.5 * vh, hFinal, te) * zoom;
  const W0 = H0 * EAGLE_ASPECT;
  const beakX = narrow ? 0.25 * vw : 0.73 * vw;
  const headY = narrow ? 0.55 * vh : 0.12 * vh;
  const topFinal = headY - HEAD_TOP_Y * H0;
  const leftFinal = beakX - BEAK_TIP[0] * W0;
  let left = lerp(vw - 0.45 * W0, leftFinal, te);
  let top = lerp(vh - 0.2 * H0, topFinal, te);
  left = Math.max(left, vw - W0);
  top = Math.max(top, vh - H0);

  // Transition: the eagle scales past the camera and up out of the top, its cut bottom edge kept below the viewport.
  const exit = smooth(0, 0.2, a);
  const H = H0 * (1 + 1.6 * exit);
  const W = H * EAGLE_ASPECT;
  const eLeft = Math.max(left - (W - W0) * 0.5, vw - W);
  const eTop = Math.max(top - exit * 0.5 * vh, vh - H);

  const cx = eLeft + W * 0.5;
  const cy = eTop + H * 0.5;
  const dx = sunScreen[0] * vw - cx;
  const dy = sunScreen[1] * vh - cy;
  const len = Math.hypot(dx, dy) || 1;

  return {
    bg: p * BG_SPAN,
    blur: smooth(0.35, 1, p),
    letter: lerp(narrow ? 0.16 : 0.42, -0.03, smooth(0.05, 0.3, p)),
    title1: 1 - smooth(0, 0.1, a),
    eagle: Math.round(clamp01((p - 0.35) / 0.65) * (EAGLE_COUNT - 1)),
    eagleAlpha: smooth(0.28, 0.36, p) * (1 - smooth(0.12, 0.2, a)),
    eagleLeft: eLeft,
    eagleTop: eTop,
    eagleW: W,
    eagleH: H,
    light: [dx / len, dy / len],
    dissolve: smooth(0, 0.12, a),
    fog: smooth(0, 0.1, a) * lerp(0.9, 0.3, smooth(0, 0.5, a)),
    teal: smooth(0, 0.15, a),
    bg2: act2Pair(a * (ACT2_COUNT - 1)),
    wisp: smooth(0.4, 0.6, a),
    letter2: lerp(narrow ? 0.16 : 0.42, -0.03, smooth(0.05, 0.3, a)),
    title2: smooth(0.02, 0.12, a),
    crow: crowPose(a, vw, vh, narrow),
  };
}

/** Reduced motion: Act II as one still: bg f150, crow c105, CORVUS in place. */
export function staticPose(vw: number, vh: number, narrow: boolean, sunScreen: [number, number]): Pose {
  const base = poseAt(1, 1, vw, vh, narrow, sunScreen);
  return {
    ...base,
    eagleAlpha: 0,
    title1: 0,
    dissolve: 1,
    fog: 0.25,
    teal: 1,
    bg2: { a: 149, b: 149, m: 0 },
    wisp: 0,
    letter2: -0.03,
    title2: 1,
    crow: { ...base.crow, frame: CROW_COUNT - 1, alpha: 1 },
  };
}

/** Cover-fit scale of a 16:9 frame on a canvas of the given aspect: the visible share of the frame. */
export function coverScale(canvasAspect: number): [number, number] {
  return [Math.min(1, canvasAspect / BG_ASPECT), Math.min(1, BG_ASPECT / canvasAspect)];
}

/** The sun's place on screen (uv, y down) for a cover-fitted frame. */
export function sunOnScreen(canvasAspect: number): [number, number] {
  const [sx, sy] = coverScale(canvasAspect);
  return [0.5 + (SUN_IMAGE[0] - 0.5) / sx, 0.5 + (SUN_IMAGE[1] - 0.5) / sy];
}
