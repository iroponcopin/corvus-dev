/**
 * The engine's live state: one plain, mutable object read and written from the frame loop.
 *
 * Nothing here is React state. A frame never causes a render, and nothing in the loop
 * allocates: every field is a number written in place.
 */

export const engine = {
  /** Seconds since the engine started (monotonic, frame-rate independent). */
  time: 0,
  /** Seconds since the previous frame, clamped to [1/240, 1/20]. */
  dt: 1 / 60,
  frame: 0,

  /** Lenis' animated scroll position, in CSS pixels, and its velocity (px per frame at 60 Hz). */
  scrollY: 0,
  scrollVelocity: 0,
  scrollLimit: 1,

  /** Viewport in CSS pixels and the device pixel ratio actually used by the renderer. */
  width: 1,
  height: 1,
  dpr: 1,

  /** Pointer in CSS pixels, in normalised device coordinates (-1..1, y up), and smoothed. */
  pointerX: 0,
  pointerY: 0,
  pointerNX: 0,
  pointerNY: 0,
  pointerSX: 0,
  pointerSY: 0,
  pointerInside: 0,
  /** Seconds of the last pointer movement. */
  pointerLastMove: -10,

  /** |velocity| through a critically damped follower, normalised to roughly 0..1. */
  energy: 0,

  /** Brand tint of the light (linear RGB), blended per page. */
  tintR: 0.36,
  tintG: 0.62,
  tintB: 1,
  tintTargetR: 0.36,
  tintTargetG: 0.62,
  tintTargetB: 1,

  /** Loudness of the music playing on the page (the OUKA theme), 0..1, smoothed. */
  music: 0,
  /** -1 when the document is right-to-left: X positions of paths and layouts are mirrored. */
  mirror: 1,
  reducedMotion: false,
  /** Adaptive quality: 1 = full. The DPR follows it. */
  quality: 1,
  /** Draw calls and triangles of the last frame (read by the debug overlay and the tests). */
  drawCalls: 0,
  triangles: 0,
  /** Frames whose CPU time exceeded the refresh budget; reset by the debug overlay. */
  longFrames: 0,
  /** Smoothed CPU milliseconds per frame spent in the engine (sim + render submission). */
  cpuMs: 0,
  /** Estimated display refresh interval in ms (8.3 on ProMotion, 16.7 at 60 Hz). */
  refreshMs: 16.7,
  /** 1 once the WebGL context is up and the first frame has been drawn. */
  ready: 0,
};

export type Engine = typeof engine;
