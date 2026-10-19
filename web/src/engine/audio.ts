import { engine } from "./store";

/**
 * A quiet procedural drone of spatial harmonics: partials of a just-intonation chord on HRTF panners
 * around the listener. Scroll velocity opens the filter, swells the upper harmonics and raises a
 * band of soft "air".
 *
 * Off by default and never started without a gesture (the Sound toggle). The per-frame update
 * only schedules AudioParam targets — no nodes, no objects, no garbage.
 */

const STORAGE_KEY = "corvus-dev-sound";

/** The drone's chord ratios over a 55 Hz fundamental: open fifths, a major third above. */
const CHORD: readonly number[] = [1, 1.5, 2, 2.5, 3, 4.5];
const VOICES = 6;
const BASE_HZ = 55;

interface Graph {
  ctx: AudioContext;
  master: GainNode;
  filter: BiquadFilterNode;
  air: GainNode;
  airFilter: BiquadFilterNode;
  oscs: OscillatorNode[];
  gains: GainNode[];
  panners: PannerNode[];
  duck: GainNode;
}

let graph: Graph | null = null;
let enabled = false;
let ducked = false;
const listeners = new Set<(on: boolean) => void>();
let lastUpdate = 0;

function readStored(): boolean {
  try {
    return sessionStorage.getItem(STORAGE_KEY) === "on";
  } catch {
    return false;
  }
}

function writeStored(on: boolean): void {
  try {
    sessionStorage.setItem(STORAGE_KEY, on ? "on" : "off");
  } catch {
    /* not remembered */
  }
}

function noiseBuffer(ctx: AudioContext): AudioBuffer {
  const len = ctx.sampleRate * 2;
  const buf = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = buf.getChannelData(c);
    let b = 0;
    for (let i = 0; i < len; i++) {
      // Brown-ish noise: integrated white, gently leaky.
      b = (b + (Math.random() * 2 - 1) * 0.02) * 0.995;
      d[i] = b * 3.5;
    }
  }
  return buf;
}

function impulse(ctx: AudioContext, seconds: number): AudioBuffer {
  const len = Math.floor(ctx.sampleRate * seconds);
  const buf = ctx.createBuffer(2, len, ctx.sampleRate);
  for (let c = 0; c < 2; c++) {
    const d = buf.getChannelData(c);
    for (let i = 0; i < len; i++) d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / len, 2.6);
  }
  return buf;
}

function build(): Graph | null {
  const Ctor: typeof AudioContext | undefined =
    window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (Ctor === undefined) return null;
  const ctx = new Ctor({ latencyHint: "interactive" });
  const out = ctx.createDynamicsCompressor();
  out.threshold.value = -18;
  out.ratio.value = 3;
  out.connect(ctx.destination);
  const duck = ctx.createGain();
  duck.gain.value = 1;
  duck.connect(out);
  const master = ctx.createGain();
  master.gain.value = 0;
  master.connect(duck);

  const reverb = ctx.createConvolver();
  reverb.buffer = impulse(ctx, 4.5);
  const wet = ctx.createGain();
  wet.gain.value = 0.55;
  reverb.connect(wet);
  wet.connect(master);

  const filter = ctx.createBiquadFilter();
  filter.type = "lowpass";
  filter.frequency.value = 420;
  filter.Q.value = 0.7;
  filter.connect(master);
  filter.connect(reverb);

  const listener = ctx.listener;
  if (listener.positionZ !== undefined) {
    listener.positionX.value = 0;
    listener.positionY.value = 0;
    listener.positionZ.value = 0;
  }

  const oscs: OscillatorNode[] = [];
  const gains: GainNode[] = [];
  const panners: PannerNode[] = [];
  const chord = CHORD;
  for (let i = 0; i < VOICES; i++) {
    const osc = ctx.createOscillator();
    osc.type = i < 2 ? "sine" : "triangle";
    osc.frequency.value = BASE_HZ * (chord[i] ?? 1) * (i % 2 === 0 ? 1 : 2);
    osc.detune.value = (i - VOICES / 2) * 3;
    const g = ctx.createGain();
    g.gain.value = 0;
    const p = ctx.createPanner();
    p.panningModel = "HRTF";
    p.distanceModel = "inverse";
    p.refDistance = 1;
    p.rolloffFactor = 0.6;
    osc.connect(g);
    g.connect(p);
    p.connect(filter);
    osc.start();
    oscs.push(osc);
    gains.push(g);
    panners.push(p);
  }

  // Starlight air: band-passed noise that rises with scroll energy.
  const noise = ctx.createBufferSource();
  noise.buffer = noiseBuffer(ctx);
  noise.loop = true;
  const airFilter = ctx.createBiquadFilter();
  airFilter.type = "bandpass";
  airFilter.frequency.value = 2400;
  airFilter.Q.value = 1.2;
  const air = ctx.createGain();
  air.gain.value = 0;
  noise.connect(airFilter);
  airFilter.connect(air);
  air.connect(master);
  air.connect(reverb);
  noise.start();

  return { ctx, master, filter, air, airFilter, oscs, gains, panners, duck };
}

function emit(): void {
  for (const l of listeners) l(enabled);
}

export function isSoundOn(): boolean {
  return enabled;
}

export function onSound(listener: (on: boolean) => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Must be called from a user gesture the first time (autoplay policy). */
export function setSound(on: boolean): void {
  enabled = on;
  writeStored(on);
  if (on) {
    if (graph === null) graph = build();
    if (graph !== null) {
      void graph.ctx.resume();
      const t = graph.ctx.currentTime;
      graph.master.gain.cancelScheduledValues(t);
      graph.master.gain.setTargetAtTime(0.32, t, 0.8);
    }
  } else if (graph !== null) {
    const t = graph.ctx.currentTime;
    graph.master.gain.cancelScheduledValues(t);
    graph.master.gain.setTargetAtTime(0, t, 0.25);
    const ctx = graph.ctx;
    window.setTimeout(() => {
      if (!enabled) void ctx.suspend();
    }, 900);
  }
  emit();
}

/** The visitor's remembered choice; sound still needs a gesture to start. */
export function soundRemembered(): boolean {
  return readStored();
}

/** Quieten the drone while another sound (the OUKA theme) plays. */
export function duckSound(on: boolean): void {
  ducked = on;
  if (graph === null) return;
  graph.duck.gain.setTargetAtTime(on ? 0.12 : 1, graph.ctx.currentTime, 0.4);
}

/** Per frame (from the shared loop). Throttled to ~30 Hz of parameter targets. */
export function updateSound(): void {
  const g = graph;
  if (g === null || !enabled) return;
  const now = engine.time;
  if (now - lastUpdate < 1 / 30) return;
  lastUpdate = now;
  const t = g.ctx.currentTime;
  const e = engine.energy;

  g.filter.frequency.setTargetAtTime(380 + e * 3800 + engine.pointerSY * 120, t, 0.12);
  g.air.gain.setTargetAtTime(0.004 + e * 0.07, t, 0.15);
  g.airFilter.frequency.setTargetAtTime(1800 + e * 4200, t, 0.2);

  // The voices hold their places around the listener; the upper ones swell with energy.
  for (let i = 0; i < VOICES; i++) {
    const a = (i / VOICES) * Math.PI * 2;
    const r = 1.6 + i * 0.35;
    const p = g.panners[i]!;
    if (p.positionX !== undefined) {
      p.positionX.setTargetAtTime(Math.cos(a) * r * engine.mirror, t, 0.1);
      p.positionY.setTargetAtTime(Math.sin(a * 0.7) * 0.6, t, 0.1);
      p.positionZ.setTargetAtTime(Math.sin(a) * r, t, 0.1);
    }
    const base = i < 2 ? 0.16 : 0.07 / (i - 0.5);
    const swell = i < 2 ? 1 : 0.35 + e * 1.8;
    g.gains[i]!.gain.setTargetAtTime(base * swell, t, 0.2);
  }
}

type Chime = "tick" | "fuse" | "unlock" | "get" | "done" | "error";

/** A short sound for an event (allocates a few nodes, once, at the event — never per frame). */
export function chime(kind: Chime): void {
  const g = graph;
  if (g === null || !enabled || ducked) return;
  const ctx = g.ctx;
  const t = ctx.currentTime;
  const out = ctx.createGain();
  out.connect(g.master);
  const tone = (freq: number, start: number, dur: number, gain: number, type: OscillatorType = "sine"): void => {
    const o = ctx.createOscillator();
    const m = ctx.createOscillator();
    const mg = ctx.createGain();
    const env = ctx.createGain();
    o.type = type;
    o.frequency.value = freq;
    // A touch of FM for a bell-like attack.
    m.frequency.value = freq * 2.01;
    mg.gain.setValueAtTime(freq * 0.8, t + start);
    mg.gain.exponentialRampToValueAtTime(1, t + start + dur);
    m.connect(mg);
    mg.connect(o.frequency);
    env.gain.setValueAtTime(0.0001, t + start);
    env.gain.exponentialRampToValueAtTime(gain, t + start + 0.012);
    env.gain.exponentialRampToValueAtTime(0.0001, t + start + dur);
    o.connect(env);
    env.connect(out);
    o.start(t + start);
    m.start(t + start);
    o.stop(t + start + dur + 0.05);
    m.stop(t + start + dur + 0.05);
  };
  switch (kind) {
    case "tick":
      tone(1760, 0, 0.08, 0.05);
      break;
    case "fuse":
      tone(220, 0, 1.6, 0.14, "triangle");
      tone(330, 0.18, 1.4, 0.1);
      tone(440, 0.36, 1.3, 0.09);
      tone(880, 0.62, 1.8, 0.08);
      tone(1320, 0.7, 2.2, 0.05);
      break;
    case "unlock":
      tone(523.25, 0, 0.7, 0.1);
      tone(659.25, 0.12, 0.7, 0.09);
      tone(783.99, 0.24, 0.9, 0.09);
      tone(1046.5, 0.36, 1.4, 0.08);
      break;
    case "get":
      tone(660, 0, 0.18, 0.06);
      tone(990, 0.08, 0.25, 0.05);
      break;
    case "done":
      tone(880, 0, 0.3, 0.07);
      tone(1318.5, 0.12, 0.6, 0.06);
      break;
    case "error":
      tone(220, 0, 0.25, 0.08, "square");
      tone(207.65, 0.12, 0.35, 0.06, "square");
      break;
  }
  window.setTimeout(() => out.disconnect(), 4000);
}

/** Suspend with the tab; resume when it returns (if the visitor left sound on). */
export function installSoundLifecycle(): () => void {
  const onVis = (): void => {
    if (graph === null) return;
    if (document.hidden) void graph.ctx.suspend();
    else if (enabled) void graph.ctx.resume();
  };
  document.addEventListener("visibilitychange", onVis);
  return () => document.removeEventListener("visibilitychange", onVis);
}

// ------------------------------------------------------------------ music (the OUKA theme)

let musicCtx: AudioContext | null = null;
let musicAnalyser: AnalyserNode | null = null;
let musicBins: Uint8Array<ArrayBuffer> | null = null;
const attached = new WeakSet<HTMLMediaElement>();

/**
 * Route a page's <audio> through an analyser so the page can react to the music. Called from
 * the play button's click (a gesture), once per element.
 */
export function attachMusic(el: HTMLMediaElement): void {
  if (attached.has(el)) {
    void musicCtx?.resume();
    return;
  }
  const Ctor: typeof AudioContext | undefined =
    window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (Ctor === undefined) return;
  try {
    musicCtx ??= new Ctor();
    const src = musicCtx.createMediaElementSource(el);
    musicAnalyser = musicCtx.createAnalyser();
    musicAnalyser.fftSize = 256;
    musicAnalyser.smoothingTimeConstant = 0.82;
    musicBins = new Uint8Array(new ArrayBuffer(musicAnalyser.frequencyBinCount));
    src.connect(musicAnalyser);
    musicAnalyser.connect(musicCtx.destination);
    attached.add(el);
    void musicCtx.resume();
  } catch {
    /* the element plays on its own; there is just no pulse */
  }
}

let musicPlaying = false;

export function setMusicPlaying(on: boolean): void {
  musicPlaying = on;
  duckSound(on);
}

/** Per frame: the music's low-band loudness into engine.music (allocation-free). */
export function updateMusic(playing: boolean = musicPlaying): void {
  const a = musicAnalyser;
  const bins = musicBins;
  let level = 0;
  if (playing && a !== null && bins !== null) {
    a.getByteFrequencyData(bins);
    let sum = 0;
    const n = Math.min(24, bins.length);
    for (let i = 2; i < n; i++) sum += bins[i] ?? 0;
    level = sum / ((n - 2) * 255);
  }
  engine.music += (level - engine.music) * (level > engine.music ? 0.5 : 0.08);
}
