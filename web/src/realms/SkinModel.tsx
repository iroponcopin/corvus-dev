"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AdditiveBlending,
  BoxGeometry,
  BufferAttribute,
  type BufferGeometry,
  CircleGeometry,
  DoubleSide,
  Euler,
  FrontSide,
  type Group,
  Matrix4,
  type Mesh,
  NearestFilter,
  Quaternion,
  ShaderMaterial,
  SRGBColorSpace,
  type Texture,
  Vector3,
} from "three";
import { mergeGeometries } from "three/addons/utils/BufferGeometryUtils.js";
import { COMMON, NOISE, glsl } from "@/engine/shaders/chunks";
import { damp } from "@/engine/math";
import { engine } from "@/engine/store";
import { useViewFrame } from "@/engine/View";
import { voxelGeometry } from "./voxel";

export type Pose = "stand" | "wave" | "t" | "sit" | "draw";
export type Rig = "studio" | "rim" | "neon" | "dusk";

/** The vanilla player skeleton with slim arms, in skin pixels (÷16 for world units). */
interface Part {
  size: [number, number, number];
  base: [number, number];
  outer: [number, number];
  pivot: [number, number, number];
  centre: [number, number, number];
}
const PARTS: Part[] = [
  { size: [8, 8, 8], base: [0, 0], outer: [32, 0], pivot: [0, 24, 0], centre: [0, 4, 0] }, // head
  { size: [8, 12, 4], base: [16, 16], outer: [16, 32], pivot: [0, 24, 0], centre: [0, -6, 0] }, // body
  { size: [3, 12, 4], base: [40, 16], outer: [40, 32], pivot: [-5.5, 24, 0], centre: [0, -6, 0] }, // right arm
  { size: [3, 12, 4], base: [32, 48], outer: [48, 48], pivot: [5.5, 24, 0], centre: [0, -6, 0] }, // left arm
  { size: [4, 12, 4], base: [0, 16], outer: [0, 32], pivot: [-2, 12, 0], centre: [0, -6, 0] }, // right leg
  { size: [4, 12, 4], base: [16, 48], outer: [0, 48], pivot: [2, 12, 0], centre: [0, -6, 0] }, // left leg
];
const E = Math.PI / 180;

/** Target Euler angles (x, y, z) per part, and the body drop in pixels. */
const POSES: Record<Pose, { r: [number, number, number][]; drop: number }> = {
  stand: { r: [[0, 0, 0], [0, 0, 0], [0, 0, -4 * E], [0, 0, 4 * E], [0, 0, 0], [0, 0, 0]], drop: 0 },
  wave: { r: [[0, -10 * E, 0], [0, 0, 0], [0, 0, -165 * E], [0, 0, 4 * E], [0, 0, 0], [0, 0, 0]], drop: 0 },
  t: { r: [[0, 0, 0], [0, 0, 0], [0, 0, -90 * E], [0, 0, 90 * E], [0, 0, -3 * E], [0, 0, 3 * E]], drop: 0 },
  sit: {
    r: [[8 * E, 0, 0], [0, 0, 0], [-25 * E, 0, -4 * E], [-25 * E, 0, 4 * E], [-90 * E, -8 * E, 0], [-90 * E, 8 * E, 0]],
    drop: 10,
  },
  // Combat draw: the blade comes up in the right hand, the left steadies forward.
  draw: { r: [[-4 * E, 12 * E, 0], [0, 10 * E, 0], [-150 * E, 0, 18 * E], [-50 * E, 0, 10 * E], [-12 * E, 0, -6 * E], [14 * E, 0, 4 * E]], drop: 0.6 },
};

/** Light rigs: key direction + colour, fill colour, rim colour, ambient. */
const RIGS: Record<Rig, { key: [number, number, number]; keyC: [number, number, number]; fill: [number, number, number]; rim: [number, number, number]; amb: number }> = {
  studio: { key: [0.45, 0.75, 0.6], keyC: [1, 0.97, 0.92], fill: [0.55, 0.62, 0.75], rim: [0.7, 0.8, 1], amb: 0.42 },
  rim: { key: [-0.2, 0.4, -0.9], keyC: [0.9, 0.95, 1], fill: [0.12, 0.13, 0.16], rim: [1.4, 1.5, 1.8], amb: 0.18 },
  neon: { key: [0.9, 0.2, 0.4], keyC: [1, 0.25, 0.75], fill: [0.1, 0.85, 1], rim: [0.7, 0.3, 1], amb: 0.22 },
  dusk: { key: [0.8, 0.35, 0.45], keyC: [1, 0.62, 0.32], fill: [0.25, 0.32, 0.6], rim: [1, 0.55, 0.4], amb: 0.3 },
};

function buildLayer(outer: boolean): BufferGeometry {
  const parts: BufferGeometry[] = [];
  PARTS.forEach((p, index) => {
    const inflate = outer ? 0.5 : 0;
    const [w, h, d] = p.size;
    const g = new BoxGeometry((w + 2 * inflate) / 16, (h + 2 * inflate) / 16, (d + 2 * inflate) / 16);
    const [u, v] = outer ? p.outer : p.base;
    // Face rectangles [u0, v0, width, height] in skin pixels, in BoxGeometry's face order.
    const rects: [number, number, number, number][] = [
      [u + d + w, v + d, d, h], // +x
      [u, v + d, d, h], // -x
      [u + d, v, w, d], // +y (top)
      [u + d + w, v, w, d], // -y (bottom)
      [u + d, v + d, w, h], // +z (front)
      [u + 2 * d + w, v + d, w, h], // -z (back)
    ];
    const uv = g.getAttribute("uv");
    for (let i = 0; i < uv.count; i++) {
      const r = rects[Math.floor(i / 4)]!;
      const ux = uv.getX(i);
      const uy = uv.getY(i);
      uv.setXY(i, (ux < 0.5 ? r[0] : r[0] + r[2]) / 64, uy < 0.5 ? 1 - (r[1] + r[3]) / 64 : 1 - r[1] / 64);
    }
    g.translate(p.centre[0] / 16, p.centre[1] / 16, p.centre[2] / 16);
    const part = new Float32Array(g.getAttribute("position").count).fill(index);
    g.setAttribute("aPart", new BufferAttribute(part, 1));
    parts.push(g);
  });
  const merged = mergeGeometries(parts, false);
  if (merged === null) throw new Error("could not merge the skin model");
  for (const g of parts) g.dispose();
  return merged;
}

const VERT = glsl`
attribute float aPart;
uniform mat4 uPart[6];
varying vec3 vNormal;
varying vec3 vWorld;
varying vec2 vUv;
varying float vPart;
void main() {
  int i = int(aPart + 0.5);
  mat4 m = uPart[i];
  vec4 w = modelMatrix * m * vec4(position, 1.0);
  vWorld = w.xyz;
  vNormal = normalize(mat3(modelMatrix * m) * normal);
  vUv = uv;
  vPart = aPart;
  gl_Position = projectionMatrix * viewMatrix * w;
}
`;

const FRAG = glsl`
${COMMON}
${NOISE}
uniform sampler2D uMap;
uniform float uHasMap;
uniform float uReveal;
uniform float uOuter;
uniform float uTime;
uniform vec3 uKey;
uniform vec3 uKeyC;
uniform vec3 uFill;
uniform vec3 uRim;
uniform float uAmb;
varying vec3 vNormal;
varying vec3 vWorld;
varying vec2 vUv;
varying float vPart;

void main() {
  vec3 N = normalize(vNormal);
  vec3 V = normalize(cameraPosition - vWorld);
  float NdV = max(dot(N, V), 0.0);
  float fres = pow(1.0 - NdV, 2.4);

  // Sealed: a hologram of the skeleton with its skin-pixel grid, scanning upward.
  vec2 px = vUv * 64.0;
  vec2 g = abs(fract(px) - 0.5);
  float grid = smoothstep(0.42, 0.5, max(g.x, g.y));
  float scan = 0.5 + 0.5 * sin(vWorld.y * 38.0 - uTime * 3.2);
  vec3 cream = vec3(0.96, 0.88, 0.8);
  vec3 crimson = vec3(0.92, 0.22, 0.32);
  vec3 holo = mix(crimson, cream, fres) * (0.12 + fres * 1.3 + grid * 0.55) * (0.75 + 0.25 * scan);
  float holoA = clamp(0.28 + fres * 0.7 + grid * 0.5, 0.0, 1.0);

  // Unsealed: the skin itself, lit by the chosen rig.
  vec3 skin = vec3(0.0);
  float skinA = 0.0;
  if (uHasMap > 0.5) {
    vec4 t = texture2D(uMap, vUv);
    skinA = t.a;
    float key = max(dot(N, normalize(uKey)), 0.0);
    float fill = max(dot(N, normalize(vec3(-uKey.x, 0.3, 0.6))), 0.0);
    float rim = pow(1.0 - NdV, 3.0);
    vec3 light = uKeyC * key * 1.05 + uFill * fill * 0.55 + uRim * rim * 0.65 + vec3(uAmb);
    skin = t.rgb * light;
  }

  // The reveal sweeps from the feet up, through a band of light.
  float edge = vWorld.y + 1.05 - uReveal * 2.4 + snoise(vWorld * 9.0) * 0.08;
  float shown = 1.0 - smoothstep(-0.03, 0.03, edge);
  float band = exp(-edge * edge * 900.0) * step(0.001, uReveal) * step(uReveal, 0.999);

  vec3 col = mix(holo, skin, shown) + cream * band * 2.5;
  float a = mix(holoA * (1.0 - uOuter * 0.55), skinA, shown);
  if (uOuter > 0.5 && shown > 0.5 && skinA < 0.5) discard;
  if (uOuter < 0.5 && shown > 0.5 && skinA < 0.02) a = 1.0;
  gl_FragColor = vec4(toSRGB(tonemap(col)), clamp(a + band, 0.0, 1.0));
}
`;

const PEDESTAL_FRAG = glsl`
uniform float uTime;
uniform vec3 uColor;
varying vec2 vUv;
void main() {
  float r = length(vUv - 0.5) * 2.0;
  float disc = smoothstep(1.0, 0.96, r) * 0.08;
  float ring = exp(-pow((r - 0.93) * 40.0, 2.0)) * 0.9 + exp(-pow((r - 0.7) * 60.0, 2.0)) * 0.25;
  float sweep = pow(0.5 + 0.5 * cos(atan(vUv.y - 0.5, vUv.x - 0.5) * 1.0 - uTime * 0.8), 8.0) * ring;
  gl_FragColor = vec4(uColor * (disc + ring * 0.5 + sweep), 1.0);
}
`;

/**
 * Sparxie on the vanilla skeleton (slim arms): one draw for the base layer, one for the outer
 * layer, the six parts posed through a uniform array of matrices. Sealed until the page hands
 * over the decrypted texture; then the hologram dissolves into the skin from the feet up.
 */
export function SkinModel({
  texture,
  pose,
  walk,
  breathe,
  rig,
  outer,
  bladeIcon,
  yaw,
  pitch,
}: {
  texture: Texture | null;
  pose: Pose;
  walk: boolean;
  breathe: boolean;
  rig: Rig;
  outer: boolean;
  bladeIcon: string | null;
  yaw: { current: number };
  pitch: { current: number };
}) {
  const root = useRef<Group>(null);
  const turn = useRef<Group>(null);
  const blade = useRef<Mesh | null>(null);
  const [bladeGeom, setBladeGeom] = useState<BufferGeometry | null>(null);
  const geoms = useMemo(() => ({ base: buildLayer(false), outer: buildLayer(true) }), []);
  const matrices = useMemo(() => Array.from({ length: 6 }, () => new Matrix4()), []);
  const scratch = useMemo(() => ({ q: new Quaternion(), e: new Euler(), p: new Vector3(), s: new Vector3(1, 1, 1) }), []);
  const angles = useRef(PARTS.map(() => [0, 0, 0] as [number, number, number]));
  const state = useRef({ drop: 0, yaw: 0.5, pitch: 0.05, t: 0, reveal: 0 });

  const makeMaterial = (isOuter: boolean): ShaderMaterial =>
    new ShaderMaterial({
      vertexShader: VERT,
      fragmentShader: FRAG,
      uniforms: {
        uPart: { value: matrices },
        uMap: { value: null },
        uHasMap: { value: 0 },
        uReveal: { value: 0 },
        uOuter: { value: isOuter ? 1 : 0 },
        uTime: { value: 0 },
        uKey: { value: new Vector3() },
        uKeyC: { value: new Vector3() },
        uFill: { value: new Vector3() },
        uRim: { value: new Vector3() },
        uAmb: { value: 0.4 },
      },
      transparent: true,
      depthWrite: !isOuter,
      side: isOuter ? DoubleSide : FrontSide,
    });
  const mats = useMemo(() => ({ base: makeMaterial(false), outer: makeMaterial(true) }), // eslint-disable-next-line react-hooks/exhaustive-deps
  []);
  // Both skins, as one list made once, so the frame walks them without building an array.
  const matList = useMemo(() => [mats.base, mats.outer], [mats]);
  const pedestal = useMemo(() => {
    const g = new CircleGeometry(1.05, 96);
    const m = new ShaderMaterial({
      vertexShader: glsl`varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: PEDESTAL_FRAG,
      uniforms: { uTime: { value: 0 }, uColor: { value: new Vector3(0.95, 0.35, 0.45) } },
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
    });
    return { g, m };
  }, []);

  useEffect(() => {
    for (const m of [mats.base, mats.outer]) {
      m.uniforms.uMap!.value = texture;
      m.uniforms.uHasMap!.value = texture === null ? 0 : 1;
    }
    if (texture !== null) {
      texture.magFilter = NearestFilter;
      texture.minFilter = NearestFilter;
      texture.generateMipmaps = false;
      texture.colorSpace = SRGBColorSpace;
      texture.needsUpdate = true;
      state.current.reveal = engine.reducedMotion ? 1 : 0;
    }
  }, [texture, mats]);

  useEffect(() => {
    if (bladeIcon === null) return;
    let alive = true;
    void voxelGeometry(bladeIcon, "flat").then((g) => {
      if (alive) setBladeGeom(g);
    });
    return () => {
      alive = false;
    };
  }, [bladeIcon]);

  useEffect(
    () => () => {
      geoms.base.dispose();
      geoms.outer.dispose();
      mats.base.dispose();
      mats.outer.dispose();
      pedestal.g.dispose();
      pedestal.m.dispose();
    },
    [geoms, mats, pedestal],
  );

  useViewFrame((dtRaw) => {
    const dt = Math.min(dtRaw, 0.05);
    const s = state.current;
    s.t += dt;
    const calm = engine.reducedMotion;
    const animate = !calm;
    const target = POSES[pose];
    const k = 1 - Math.exp(-dt * (animate ? 9 : 60));
    const sw = Math.sin(s.t * 5.2);
    const breath = breathe && animate ? Math.sin(s.t * 1.9) : 0;
    for (let i = 0; i < 6; i++) {
      const a = angles.current[i]!;
      const tr = target.r[i]!;
      let tx = tr[0];
      const ty = tr[1];
      let tz = tr[2];
      if (walk && animate && (pose === "stand" || pose === "t")) {
        if (i === 4) tx += 0.75 * sw;
        if (i === 5) tx -= 0.75 * sw;
        if (i === 2) tx -= 0.6 * sw;
        if (i === 3) tx += 0.6 * sw;
      }
      if (pose === "wave" && animate && i === 2) tz += 0.22 * Math.sin(s.t * 6);
      if (pose === "draw" && animate) {
        if (i === 2) tx += Math.sin(s.t * 2.2) * 0.06;
        if (i === 1) tz += Math.sin(s.t * 1.1) * 0.02;
      }
      if (breath !== 0) {
        if (i === 2) tz -= 0.035 * breath;
        if (i === 3) tz += 0.035 * breath;
        if (i === 0) tx += 0.02 * breath;
      }
      a[0] += (tx - a[0]) * k;
      a[1] += (ty - a[1]) * k;
      a[2] += (tz - a[2]) * k;
      const p = PARTS[i]!;
      scratch.e.set(a[0], a[1], a[2], "XYZ");
      scratch.q.setFromEuler(scratch.e);
      scratch.p.set(p.pivot[0] / 16, p.pivot[1] / 16 - 1, p.pivot[2] / 16);
      matrices[i]!.compose(scratch.p, scratch.q, scratch.s);
    }
    s.drop += (target.drop + (breath * 0.15) - s.drop) * k;
    s.yaw = damp(s.yaw, yaw.current, 10, dt);
    s.pitch = damp(s.pitch, pitch.current, 10, dt);
    if (root.current !== null) root.current.position.y = -s.drop / 16;
    if (turn.current !== null) turn.current.rotation.set(s.pitch, s.yaw, 0);

    // The blade rides the right hand while drawing.
    const b = blade.current;
    if (b !== null) {
      const show = pose === "draw";
      b.visible = show;
      if (show) {
        const hand = matrices[2]!;
        b.matrixAutoUpdate = false;
        b.matrix.copy(hand);
        scratch.p.set(-0.02, -0.72, 0.12);
        scratch.e.set(Math.PI / 2, 0, -Math.PI / 4);
        scratch.q.setFromEuler(scratch.e);
        scratch.s.setScalar(0.95);
        b.matrix.multiply(tmpMatrix.compose(scratch.p, scratch.q, scratch.s));
        scratch.s.setScalar(1);
      }
    }

    const rg = RIGS[rig];
    if (texture !== null && s.reveal < 1) s.reveal = Math.min(1, s.reveal + dt * 0.75);
    for (let mi = 0; mi < matList.length; mi++) {
      const u = matList[mi]!.uniforms;
      u.uTime!.value = s.t;
      u.uReveal!.value = texture === null ? 0 : s.reveal;
      (u.uKey!.value as Vector3).set(rg.key[0] * engine.mirror, rg.key[1], rg.key[2]);
      (u.uKeyC!.value as Vector3).set(rg.keyC[0], rg.keyC[1], rg.keyC[2]);
      (u.uFill!.value as Vector3).set(rg.fill[0], rg.fill[1], rg.fill[2]);
      (u.uRim!.value as Vector3).set(rg.rim[0], rg.rim[1], rg.rim[2]);
      u.uAmb!.value = rg.amb;
    }
    pedestal.m.uniforms.uTime!.value = s.t;
    (pedestal.m.uniforms.uColor!.value as Vector3).set(rg.rim[0] * 0.7, rg.rim[1] * 0.45, rg.rim[2] * 0.55);
  });

  return (
    <group ref={root}>
      <mesh geometry={pedestal.g} material={pedestal.m} rotation={[-Math.PI / 2, 0, 0]} position={[0, -1.03, 0]} />
      <group ref={turn}>
        <mesh geometry={geoms.base} material={mats.base} frustumCulled={false} />
        <mesh geometry={geoms.outer} material={mats.outer} frustumCulled={false} visible={outer} renderOrder={2} />
        {bladeGeom !== null ? (
          <mesh
            ref={(m) => {
              blade.current = m;
            }}
            geometry={bladeGeom}
            visible={false}
          >
            <meshBasicMaterial vertexColors />
          </mesh>
        ) : null}
      </group>
    </group>
  );
}

const tmpMatrix = new Matrix4();
