"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  AdditiveBlending,
  BufferAttribute,
  BufferGeometry,
  type Group,
  type Mesh,
  NearestFilter,
  Points,
  RingGeometry,
  ShaderMaterial,
  SRGBColorSpace,
  type Texture,
  TextureLoader,
  Vector3,
} from "three";
import { COMMON, glsl } from "@/engine/shaders/chunks";
import { chime } from "@/engine/audio";
import { damp } from "@/engine/math";
import { engine } from "@/engine/store";
import { useViewFrame } from "@/engine/View";
import { voxelGeometry } from "./voxel";

export interface SynthItem {
  icon: string | null;
  kind: "flat" | "cube" | "icon" | "none";
}

export interface SynthIngredient extends SynthItem {
  /** Crafting grid slot (0..8, row-major), or -1 for a fusion ingredient on the ring. */
  slot: number;
}

const ITEM_VERT = glsl`
attribute float aShade;
varying vec3 vColor;
varying float vShade;
varying vec3 vNormal;
varying vec3 vWorld;
varying vec2 vUv;
void main() {
#ifdef USE_COLOR
  vColor = color;
#else
  vColor = vec3(1.0);
#endif
  vShade = aShade;
  vUv = uv;
  vec4 w = modelMatrix * vec4(position, 1.0);
  vWorld = w.xyz;
  vNormal = normalize(mat3(modelMatrix) * normal);
  gl_Position = projectionMatrix * viewMatrix * w;
}
`;

const ITEM_FRAG = glsl`
${COMMON}
uniform sampler2D uMap;
uniform float uUseMap;
uniform float uMissing;
uniform float uGlow;
uniform float uAlpha;
uniform vec3 uTint;
varying vec3 vColor;
varying float vShade;
varying vec3 vNormal;
varying vec3 vWorld;
varying vec2 vUv;
void main() {
  vec3 base = vColor;
  if (uUseMap > 0.5) {
    vec4 t = texture2D(uMap, vUv);
    if (t.a < 0.5) discard;
    base = t.rgb;
  }
  if (uMissing > 0.5) {
    // No published icon: a dark glass cube with a faint question of light.
    vec2 q = abs(vUv - 0.5);
    base = vec3(0.05, 0.06, 0.08) + uTint * 0.4 * smoothstep(0.42, 0.5, max(q.x, q.y));
  }
  vec3 N = normalize(vNormal);
  vec3 V = normalize(cameraPosition - vWorld);
  float rim = pow(1.0 - max(dot(N, V), 0.0), 3.0);
  vec3 L = normalize(vec3(0.4, 0.9, 0.6));
  float spec = pow(max(dot(reflect(-L, N), V), 0.0), 24.0) * 0.18;
  vec3 col = base * (0.28 + 0.82 * vShade) + uTint * rim * 0.22 + vec3(spec) + base * uGlow * 1.4 + uTint * uGlow * 0.3;
  gl_FragColor = vec4(toSRGB(tonemap(col)), uAlpha);
}
`;

const SPARK_VERT = glsl`
attribute vec4 aSeed;
uniform float uAge;
uniform float uPixelRatio;
varying float vLife;
varying float vHue;
void main() {
  float t = max(uAge, 0.0);
  vec3 dir = normalize(aSeed.xyz - 0.5);
  float speed = 0.6 + aSeed.w * 1.9;
  vec3 p = dir * speed * (1.0 - exp(-t * 2.8)) + vec3(0.0, -0.18 * t * t, 0.0);
  float life = clamp(1.0 - t / (0.7 + aSeed.w * 0.9), 0.0, 1.0) * step(0.0, uAge);
  vLife = life;
  vHue = aSeed.x;
  vec4 mv = modelViewMatrix * vec4(p, 1.0);
  gl_Position = projectionMatrix * mv;
  gl_PointSize = (1.5 + 7.0 * life * life) * uPixelRatio * (3.0 / max(-mv.z, 0.1));
}
`;

const SPARK_FRAG = glsl`
uniform vec3 uColor;
varying float vLife;
varying float vHue;
void main() {
  vec2 c = gl_PointCoord * 2.0 - 1.0;
  float d = dot(c, c);
  if (d > 1.0) discard;
  vec3 col = mix(uColor, vec3(1.0, 0.95, 0.85), 0.5 + 0.5 * vHue) * (exp(-d * 6.0) * 1.4) * vLife;
  gl_FragColor = vec4(col, 1.0);
}
`;

const ALTAR_FRAG = glsl`
uniform vec3 uColor;
uniform float uPulse;
varying vec2 vUv;
void main() {
  float r = length(vUv - 0.5) * 2.0;
  float ring = exp(-pow((r - 0.86) * 18.0, 2.0)) + exp(-pow((r - 0.62) * 30.0, 2.0)) * 0.4;
  float glow = exp(-r * 3.0) * 0.25 * (0.6 + uPulse);
  gl_FragColor = vec4(uColor * (ring + glow), 1.0);
}
`;

const SPARKS = 1400;
const textureCache = new Map<string, Texture>();

function itemTexture(url: string): Texture {
  let t = textureCache.get(url);
  if (t === undefined) {
    t = new TextureLoader().load(url);
    t.colorSpace = SRGBColorSpace;
    t.magFilter = NearestFilter;
    t.minFilter = NearestFilter;
    t.generateMipmaps = false;
    textureCache.set(url, t);
  }
  return t;
}

function useItemMaterial(item: SynthItem): ShaderMaterial {
  const material = useMemo(
    () =>
      new ShaderMaterial({
        vertexShader: ITEM_VERT,
        fragmentShader: ITEM_FRAG,
        vertexColors: item.kind !== "cube" && item.kind !== "none" && item.icon !== null,
        transparent: true,
        uniforms: {
          uMap: { value: null },
          uUseMap: { value: item.kind === "cube" && item.icon !== null ? 1 : 0 },
          uMissing: { value: item.icon === null || item.kind === "none" ? 1 : 0 },
          uGlow: { value: 0 },
          uAlpha: { value: 1 },
          uTint: { value: new Vector3(1, 0.78, 0.42) },
        },
      }),
    [item.kind, item.icon],
  );
  useEffect(() => {
    if (item.kind === "cube" && item.icon !== null) material.uniforms.uMap!.value = itemTexture(item.icon);
    return () => material.dispose();
  }, [material, item.kind, item.icon]);
  return material;
}

/** One item, as a voxel object (or a textured cube, or the "no icon" glass cube). */
function VoxelItem({ item, meshRef }: { item: SynthItem; meshRef: (m: Mesh | null) => void }) {
  const [geometry, setGeometry] = useState<BufferGeometry | null>(null);
  const material = useItemMaterial(item);
  useEffect(() => {
    let alive = true;
    void voxelGeometry(item.icon, item.kind).then((g) => {
      if (alive) setGeometry(g);
    });
    return () => {
      alive = false;
    };
  }, [item.icon, item.kind]);
  if (geometry === null) return null;
  return <mesh ref={meshRef} geometry={geometry} material={material} />;
}

const SLOT = 0.66;

/**
 * The matter synthesiser: a recipe's ingredients appear on the crafting grid (or around the
 * crucible's ring), fly inward on spiral paths, fuse in a flash of light, and leave the
 * finished item turning on its altar. `playKey` replays the synthesis; drag turns the result.
 */
export function Synthesizer({
  result,
  ingredients,
  playKey,
  spinning,
  turn,
}: {
  result: SynthItem;
  ingredients: SynthIngredient[];
  playKey: number;
  spinning: boolean;
  /** Extra yaw from dragging / arrow keys (radians), owned by the DOM side. */
  turn: { current: number };
}) {
  const group = useRef<Group>(null);
  const resultMesh = useRef<Mesh | null>(null);
  const ingMeshes = useRef<(Mesh | null)[]>([]);
  const timeline = useRef({ t: 0, fired: false, spin: 0, yaw: 0 });
  const tmp = useMemo(() => new Vector3(), []);

  const sparks = useMemo(() => {
    const g = new BufferGeometry();
    const seeds = new Float32Array(SPARKS * 4);
    for (let i = 0; i < seeds.length; i++) seeds[i] = Math.random();
    g.setAttribute("position", new BufferAttribute(new Float32Array(SPARKS * 3), 3));
    g.setAttribute("aSeed", new BufferAttribute(seeds, 4));
    const m = new ShaderMaterial({
      vertexShader: SPARK_VERT,
      fragmentShader: SPARK_FRAG,
      uniforms: { uAge: { value: -1 }, uPixelRatio: { value: 1 }, uColor: { value: new Vector3(1, 0.78, 0.42) } },
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
    });
    const p = new Points(g, m);
    p.frustumCulled = false;
    return p;
  }, []);
  const altar = useMemo(() => {
    const g = new RingGeometry(0.01, 1.25, 64, 1);
    // Map radial UVs so the shader can draw concentric rings.
    const pos = g.getAttribute("position");
    const uv = g.getAttribute("uv");
    for (let i = 0; i < pos.count; i++) uv.setXY(i, pos.getX(i) / 2.5 + 0.5, pos.getY(i) / 2.5 + 0.5);
    const m = new ShaderMaterial({
      vertexShader: glsl`varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }`,
      fragmentShader: ALTAR_FRAG,
      uniforms: { uColor: { value: new Vector3(1, 0.7, 0.35) }, uPulse: { value: 0 } },
      transparent: true,
      depthWrite: false,
      blending: AdditiveBlending,
    });
    return { g, m };
  }, []);

  useEffect(
    () => () => {
      sparks.geometry.dispose();
      (sparks.material as ShaderMaterial).dispose();
      altar.g.dispose();
      altar.m.dispose();
    },
    [sparks, altar],
  );

  // A new recipe (or "synthesise again") restarts the timeline.
  useEffect(() => {
    timeline.current.t = engine.reducedMotion ? 10 : 0;
    timeline.current.fired = engine.reducedMotion;
  }, [playKey, result.icon]);

  const ringCount = ingredients.filter((i) => i.slot < 0).length;

  useViewFrame((dt) => {
    const tl = timeline.current;
    tl.t += dt;
    const t = tl.t;
    const fuseAt = 1.15;
    if (!tl.fired && t >= fuseAt) {
      tl.fired = true;
      chime("fuse");
    }
    const sm = sparks.material as ShaderMaterial;
    sm.uniforms.uAge!.value = t - fuseAt;
    sm.uniforms.uPixelRatio!.value = engine.dpr;
    altar.m.uniforms.uPulse!.value = Math.exp(-Math.max(0, t - fuseAt) * 2) * 2 + 0.3 * Math.sin(engine.time * 2);

    // Ingredients: appear, then spiral inward and vanish into the flash.
    let ringIndex = 0;
    for (let i = 0; i < ingredients.length; i++) {
      const m = ingMeshes.current[i];
      const ing = ingredients[i];
      if (m === null || m === undefined || ing === undefined) continue;
      let sx: number;
      let sy: number;
      if (ing.slot >= 0) {
        sx = ((ing.slot % 3) - 1) * SLOT * engine.mirror;
        sy = (1 - Math.floor(ing.slot / 3)) * SLOT;
      } else {
        const a = (ringIndex / Math.max(1, ringCount)) * Math.PI * 2 + Math.PI / 2;
        sx = Math.cos(a) * 1.0;
        sy = Math.sin(a) * 1.0;
        ringIndex++;
      }
      const delay = i * 0.045;
      const appear = Math.min(1, Math.max(0, (t - delay) / 0.3));
      const fly = Math.min(1, Math.max(0, (t - 0.42 - delay * 0.5) / 0.7));
      const e = fly * fly * (3 - 2 * fly);
      const swirl = Math.sin(e * Math.PI) * 0.55;
      const ang = Math.atan2(sy, sx) + e * 2.4;
      const rad = Math.hypot(sx, sy) * (1 - e);
      tmp.set(Math.cos(ang) * rad, Math.sin(ang) * rad + swirl * 0.25, 0.25 + swirl);
      m.position.copy(tmp);
      const scale = 0.5 * (1 - Math.pow(1 - appear, 3)) * (1 - e * 0.85);
      m.scale.setScalar(Math.max(0.0001, scale));
      m.rotation.set(0.3 * e, (t + i) * 1.6 * fly, 0);
      m.visible = fly < 1 && appear > 0;
      const mat = m.material as ShaderMaterial;
      mat.uniforms.uGlow!.value = e * 1.2;
    }

    // The result: rises out of the flash with a spring, then turns.
    const r = resultMesh.current;
    if (r !== null) {
      const k = Math.min(1, Math.max(0, (t - fuseAt + 0.05) / 0.55));
      const spring = k >= 1 ? 1 : 1 - Math.exp(-6 * k) * Math.cos(10 * k);
      r.scale.setScalar(Math.max(0.0001, spring * (result.kind === "cube" ? 1.05 : 1.25)));
      r.visible = k > 0;
      if (spinning && !engine.reducedMotion) tl.spin += dt * 0.7;
      tl.yaw = damp(tl.yaw, tl.spin + turn.current, 10, dt);
      r.rotation.set(-0.18, tl.yaw, 0);
      r.position.y = 0.05 + Math.sin(engine.time * 1.2) * 0.03;
      const mat = r.material as ShaderMaterial;
      mat.uniforms.uGlow!.value = Math.exp(-Math.max(0, t - fuseAt) * 3) * 1.5;
    }
    if (group.current !== null) {
      group.current.rotation.x = engine.pointerSY * 0.06;
    }
  });

  return (
    <group ref={group}>
      <mesh geometry={altar.g} material={altar.m} rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.78, 0]} />
      <primitive object={sparks} />
      {ingredients.map((ing, i) => (
        <VoxelItem
          key={`${playKey}-${i}-${ing.icon ?? "none"}`}
          item={ing}
          meshRef={(m) => {
            ingMeshes.current[i] = m;
          }}
        />
      ))}
      <VoxelItem
        key={`r-${result.icon ?? "none"}`}
        item={result}
        meshRef={(m) => {
          resultMesh.current = m;
        }}
      />
    </group>
  );
}
