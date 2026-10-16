/**
 * The Act I timeline: scroll progress p in [0, 1] mapped to what the stage shows. Pure functions, so the
 * stage's DOM and GL code only reads numbers from here.
 */

/** Background footage: f001..f113 (113 frames, 12 fps), indexed 0..112 here. */
export const BG_COUNT = 113;
/** bg frame index = p * BG_SPAN (112). */
export const BG_SPAN = 112;
/** Eagle footage: h001..h060 (60 frames), indexed 0..59. */
export const EAGLE_COUNT = 60;
/** Eagle frame size in pixels (921 x 1400). */
export const EAGLE_ASPECT = 921 / 1400;
/** The footage's own aspect, 1920 x 1080. */
export const BG_ASPECT = 16 / 9;
/** The sun in background-frame coordinates (x, y down), measured on f080. */
export const SUN_IMAGE: readonly [number, number] = [0.51, 0.22];
/** The midpoint between the eagle's eyes in its frame coordinates (x, y down): the same in every frame, frontal or profile. */
export const EYE_MID: readonly [number, number] = [0.53, 0.18];

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

export interface Pose {
  /** Background frame, fractional, 0..112. */
  bg: number;
  /** Depth of field strength, 0 (sharp) .. 1 (strong). */
  blur: number;
  /** Title letter-spacing in em. */
  letter: number;
  /** Eagle frame, integer 0..59. */
  eagle: number;
  /** Eagle opacity, 0..1. */
  eagleAlpha: number;
  /** Eagle box on the viewport, in CSS pixels. */
  eagleLeft: number;
  eagleTop: number;
  eagleW: number;
  eagleH: number;
  /** Eagle centre to sun, unit vector in screen space (x, y down). */
  light: [number, number];
}

/** Layout knobs: the eagle's final placement differs on narrow screens. */
export function poseAt(p: number, vw: number, vh: number, narrow: boolean, sunScreen: [number, number]): Pose {
  // Eagle rise: from the bottom-right, scaling up, the beak landing on the end of the word by p = 0.8.
  const te = smooth(0.3, 0.8, p);
  const zoom = 1 + 0.05 * smooth(0.8, 1, p);
  const hFinal = (narrow ? 0.92 : 1.2) * vh;
  const hStart = 0.5 * vh;
  const H = lerp(hStart, hFinal, te) * zoom;
  const W = H * EAGLE_ASPECT;
  // The eyes end on the right half; at this height the beak lands on the last letters of the word.
  const finalEye: [number, number] = narrow ? [0.62 * vw, 0.58 * vh] : [0.67 * vw, 0.3 * vh];
  const startEye: [number, number] = [1.05 * vw, 1.1 * vh];
  const ex = lerp(startEye[0], finalEye[0], te);
  const ey = lerp(startEye[1], finalEye[1], te);
  const left = ex - EYE_MID[0] * W;
  const top = ey - EYE_MID[1] * H;
  const cx = left + W * 0.5;
  const cy = top + H * 0.5;
  const dx = sunScreen[0] * vw - cx;
  const dy = sunScreen[1] * vh - cy;
  const len = Math.hypot(dx, dy) || 1;
  return {
    bg: p * BG_SPAN,
    blur: smooth(0.35, 1, p),
    letter: lerp(narrow ? 0.16 : 0.42, -0.03, smooth(0.05, 0.3, p)),
    eagle: Math.round(clamp01((p - 0.35) / 0.65) * (EAGLE_COUNT - 1)),
    eagleAlpha: smooth(0.28, 0.36, p),
    eagleLeft: left,
    eagleTop: top,
    eagleW: W,
    eagleH: H,
    light: [dx / len, dy / len],
  };
}

/** Reduced motion: bg frame 80, eagle h060 at its final place, the title spaced out. */
export function staticPose(vw: number, vh: number, narrow: boolean, sunScreen: [number, number]): Pose {
  return { ...poseAt(1, vw, vh, narrow, sunScreen), bg: 79, blur: 0, eagle: EAGLE_COUNT - 1, eagleAlpha: 1 };
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
