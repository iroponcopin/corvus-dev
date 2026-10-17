/**
 * The timeline of the cinema: one scroll section, three acts. Act I (the eagle, HALIA) runs over the first ACT1_VH
 * viewport heights; Act II (the forest, CORVUS, the crow) over the next ACT2_VH; Act III (the headland at dusk,
 * the Corvus title) over the last ACT3_VH. The altitude stream closes the story after it. Pure
 * functions, so the stage's DOM and GL code only reads numbers from here.
 */

/** Scroll, in viewport heights, of each act. The section is the three acts' total plus one viewport. */
export const ACT1_VH = 3;
export const ACT2_VH = 4;
export const ACT3_VH = 4;

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
/** Act III background footage: f001..f196, indexed 0..195. Shot one ends at index 131. */
export const ACT3_COUNT = 196;

/** Eagle frame size in pixels (921 x 1400). */
export const EAGLE_ASPECT = 921 / 1400;
/** Crow frame size in pixels (1260 x 580). */
export const CROW_ASPECT = 1260 / 580;
/** Close crow frame size in pixels (2003 x 1100). */
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
  /** Act III: the dissolve from Act II to the headland (0..1), its frames, the dusk grade of shot one (0..1). */
  dissolve3: number;
  bg3: Pair;
  dusk: number;
  /** CORVUS (Act III) letter-spacing (em) and opacity. */
  letter3: number;
  title3: number;
}

/**
 * A two-shot scrub. Frames up to the cut scrub normally; the hard cut between `cut` and `cut + 1` is a cross-dissolve
 * over `win` steps; the second shot is stretched over the remaining steps.
 */
export function shotPair(x: number, count: number, cut: number, win: number): Pair {
  const N = count - 1;
  if (x < cut) {
    const a = Math.floor(x);
    return { a, b: Math.min(a + 1, cut), m: x - a };
  }
  if (x < cut + win) return { a: cut, b: cut + 1, m: (x - cut) / win };
  const y = cut + 1 + (x - (cut + win)) * ((N - (cut + 1)) / (N - (cut + win)));
  const a = Math.min(Math.floor(y), N - 1);
  return { a, b: Math.min(a + 1, N), m: y - a };
}

/** Act II: the cut between f090 and f091 (indices 89 and 90), a cross-dissolve over ten steps. */
export function act2Pair(x: number): Pair {
  return shotPair(x, ACT2_COUNT, 89, 10);
}

/** Act III: the cut between f132 and f133 (indices 131 and 132), a cross-dissolve over ten steps. */
export function act3Pair(x: number): Pair {
  return shotPair(x, ACT3_COUNT, 131, 10);
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

/**
 * The whole timeline at once: p = Act I progress (0..1), a = Act II progress (0..1), c = Act III progress (0..1).
 */
export function poseAt(
  p: number,
  a: number,
  c: number,
  vw: number,
  vh: number,
  narrow: boolean,
  sunScreen: [number, number],
): Pose {
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

  // Act III's shot one (f001..f132) is graded toward dusk; the weight follows the cross-dissolve at the cut.
  const bg3 = act3Pair(c * (ACT3_COUNT - 1));
  const duskA = bg3.a <= 131 ? 1 : 0;
  const duskB = bg3.b <= 131 ? 1 : 0;

  // The Act II crow leaves as the headland comes in.
  const crow2 = crowPose(a, vw, vh, narrow);
  // The Act II crow is fully gone before the headland starts to dissolve in.
  crow2.alpha *= 1 - smooth(0, 0.03, c);

  return {
    bg: p * BG_SPAN,
    blur: smooth(0.35, 1, p),
    letter: lerp(narrow ? 0.16 : 0.42, -0.03, smooth(0.05, 0.3, p)),
    // HALIA is gone by a = 0.03; CORVUS waits until a = 0.10, a 4% gap of section progress with neither title shown.
    title1: 1 - smooth(0, 0.03, a),
    eagle: Math.round(clamp01((p - 0.35) / 0.65) * (EAGLE_COUNT - 1)),
    // The eagle is gone before the cloud starts to dissolve, so it never hangs over another shot.
    eagleAlpha: smooth(0.28, 0.36, p) * (1 - smooth(0, 0.04, a)),
    eagleLeft: eLeft,
    eagleTop: eTop,
    eagleW: W,
    eagleH: H,
    light: [dx / len, dy / len],
    dissolve: smooth(0.04, 0.14, a),
    fog: smooth(0, 0.1, a) * lerp(0.9, 0.3, smooth(0, 0.5, a)),
    teal: smooth(0, 0.15, a),
    bg2: act2Pair(a * (ACT2_COUNT - 1)),
    wisp: smooth(0.4, 0.6, a),
    letter2: lerp(narrow ? 0.16 : 0.42, -0.03, smooth(0.1, 0.35, a)),
    title2: smooth(0.1, 0.18, a) * (1 - smooth(0, 0.03, c)),
    crow: crow2,
    dissolve3: smooth(0.03, 0.15, c),
    bg3,
    dusk: lerp(duskA, duskB, bg3.m),
    letter3: lerp(narrow ? 0.16 : 0.42, -0.03, smooth(0.1, 0.35, c)),
    title3: smooth(0.1, 0.18, c),
  };
}

/** Reduced motion: Act III as one still: the headland at f171, with its title in place. */
export function staticPose(vw: number, vh: number, narrow: boolean, sunScreen: [number, number]): Pose {
  const base = poseAt(1, 1, 1, vw, vh, narrow, sunScreen);
  return {
    ...base,
    eagleAlpha: 0,
    title1: 0,
    dissolve: 1,
    fog: 0.2,
    teal: 1,
    bg2: { a: ACT2_COUNT - 1, b: ACT2_COUNT - 1, m: 0 },
    wisp: 0,
    letter2: -0.03,
    title2: 0,
    crow: { ...base.crow, alpha: 0 },
    dissolve3: 1,
    bg3: { a: 170, b: 170, m: 0 },
    dusk: 0,
    letter3: -0.03,
    title3: 1,
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
