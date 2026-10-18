"use client";

import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { OrbitControls } from "@react-three/drei";
import { type ComponentRef, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  AdditiveBlending,
  Box3,
  BufferAttribute,
  BufferGeometry,
  CylinderGeometry,
  type Group,
  LineBasicMaterial,
  Matrix4,
  type LineSegments,
  type Mesh,
  type PerspectiveCamera,
  MeshBasicMaterial,
  MeshStandardMaterial,
  PlaneGeometry,
  Points,
  PointsMaterial,
  RingGeometry,
  type Texture,
  Vector3,
} from "three";
import type { TomeIngredient, TomeItem } from "./tome-data";
import { disposeVoxelCache, modelFor, pinModel, spriteTexture, type VoxelModel } from "./VoxelExtruder";
import { recipeIcon } from "@/lib/site";

/**
 * The crafting pedestal: the selected item as a voxel model on a dark plinth, and above it the ritual. A recipe
 * with a 3 × 3 grid assembles in a holographic grid (ingredients rise, spiral in, burst, and the item appears);
 * a station recipe gathers its counted inputs in a ring around the station's plate, which takes the place of the
 * grid. Nothing is drawn as a 3 × 3 that the recipe does not have. The stage has its own WebGL canvas (not the
 * shared one), pauses when it is off screen, and falls back to the item's picture where WebGL is missing.
 */

type V3 = [number, number, number];

/** Timeline of the ritual, in seconds. */
const INGRESS = 0.55;
const CONVERGE_AT = 0.75;
const CONVERGE_FOR = 0.7;
const BURST_AT = 1.45;
const MANIFEST_FOR = 0.75;
const RITUAL_END = 2.3;

const ALTAR_Y = 1.9;
const ITEM_Y = 0.1;
const PLINTH_Y = -0.55;
const GRID_GAP = 0.36;
const RING_RADIUS = 1.05;
const SPRITE = 0.3;
const BURST_COUNT = 140;

/** Shared with the page: the pedestal's text and the accent colour of the active model. */
export interface VoxelStageLabels {
  stage: string;
  hint: string;
  explode: string;
  spin: string;
  grid: string;
  reset: string;
  noWebgl: string;
  ritual: string;
  ready: string;
  show: string;
  hide: string;
}

export interface VoxelItemStageProps {
  item: TomeItem;
  ingredients: TomeIngredient[];
  layout: "grid" | "station";
  /** The station plate of a station recipe (its item's picture and name). */
  station: { name: string; icon: string | null } | null;
  accent: string;
  /** Changes when a new recipe is chosen: the ritual plays again. */
  playKey: number;
  reduced: boolean;
  labels: VoxelStageLabels;
  /** Hidden on narrow screens until the reader opens the pedestal. */
  collapsed?: boolean;
}

interface Ritual {
  /** performance.now() / 1000 at the start of the ritual, or -1 before any ritual. */
  start: number;
  reduced: boolean;
}

function clamp01(v: number): number {
  return Math.min(1, Math.max(0, v));
}
function easeOutBack(t: number): number {
  const c1 = 1.70158;
  const c3 = c1 + 1;
  return 1 + c3 * Math.pow(t - 1, 3) + c1 * Math.pow(t - 1, 2);
}
function easeInOut(t: number): number {
  return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
}

/** Where each ingredient gathers: the 3 × 3 holographic grid, or a ring around the station plate. */
function targetsOf(ingredients: TomeIngredient[], layout: "grid" | "station"): V3[] {
  if (layout === "grid") {
    return ingredients.map((i) => {
      const slot = Math.max(0, i.slot);
      const r = Math.floor(slot / 3);
      const c = slot % 3;
      return [(c - 1) * GRID_GAP, ALTAR_Y + (1 - r) * GRID_GAP, 0];
    });
  }
  const n = Math.max(1, ingredients.length);
  return ingredients.map((_, k) => {
    const a = -Math.PI / 2 + (k / n) * Math.PI * 2;
    return [Math.cos(a) * RING_RADIUS, ALTAR_Y + Math.sin(a) * RING_RADIUS * 0.5, 0];
  });
}

function IngredientSprite({ index, target, url, dark, ritual }: { index: number; target: V3; url: string | null; dark: boolean; ritual: { current: Ritual } }) {
  const mesh = useRef<Mesh>(null);
  const tex = useMemo<Texture | null>(() => (url ? spriteTexture(url) : null), [url]);
  const from = useMemo<V3>(() => [target[0] * 0.35, PLINTH_Y + 0.25, 0.3], [target]);
  const pos = useMemo(() => new Vector3(), []);
  useFrame(() => {
    const m = mesh.current;
    if (!m) return;
    const r = ritual.current;
    if (r.start < 0 || r.reduced) {
      m.visible = false;
      return;
    }
    const t = performance.now() / 1000 - r.start - index * 0.04;
    if (t < 0) {
      m.visible = false;
      return;
    }
    m.visible = true;
    if (t < CONVERGE_AT) {
      const p = easeOutBack(clamp01(t / INGRESS));
      pos.set(from[0] + (target[0] - from[0]) * p, from[1] + (target[1] - from[1]) * p, from[2] + (target[2] - from[2]) * p);
      m.scale.setScalar(0.2 + 0.8 * clamp01(t / INGRESS));
    } else {
      const c = clamp01((t - CONVERGE_AT) / CONVERGE_FOR);
      const e = easeInOut(c);
      const spiral = c * Math.PI * 3;
      const rad = (1 - e) * 0.22;
      pos.set(
        target[0] + (-target[0] * e) + Math.cos(spiral) * rad,
        target[1] + (ALTAR_Y + 0.1 - target[1]) * e + Math.sin(spiral) * rad,
        target[2] + (0.2 - target[2]) * e,
      );
      m.scale.setScalar(1 - e * 0.85);
      m.visible = c < 1;
    }
    m.position.copy(pos);
  });
  return (
    <mesh ref={mesh} visible={false} position={target}>
      <planeGeometry args={[SPRITE, SPRITE]} />
      <meshBasicMaterial map={tex} color={dark || tex === null ? 0x2a2f3a : 0xffffff} transparent alphaTest={0.5} toneMapped={false} />
    </mesh>
  );
}

function Burst({ ritual, accent }: { ritual: { current: Ritual }; accent: string }) {
  const geo = useMemo(() => {
    const g = new BufferGeometry();
    g.setAttribute("position", new BufferAttribute(new Float32Array(BURST_COUNT * 3), 3));
    return g;
  }, []);
  const vel = useMemo(() => {
    const v = new Float32Array(BURST_COUNT * 3);
    for (let i = 0; i < BURST_COUNT; i++) {
      const th = Math.random() * Math.PI * 2;
      const ph = Math.acos(2 * Math.random() - 1);
      const s = 0.5 + Math.random() * 1.2;
      v[i * 3] = Math.sin(ph) * Math.cos(th) * s;
      v[i * 3 + 1] = Math.cos(ph) * s + 0.3;
      v[i * 3 + 2] = Math.sin(ph) * Math.sin(th) * s;
    }
    return v;
  }, []);
  const material = useMemo(
    () => new PointsMaterial({ color: accent, size: 0.06, transparent: true, opacity: 0, depthWrite: false, blending: AdditiveBlending }),
    [accent],
  );
  const points = useMemo(() => new Points(geo, material), [geo, material]);
  useEffect(
    () => () => {
      geo.dispose();
      material.dispose();
    },
    [geo, material],
  );
  useFrame(() => {
    const r = ritual.current;
    if (r.start < 0 || r.reduced) {
      material.opacity = 0;
      return;
    }
    const t = performance.now() / 1000 - r.start - BURST_AT;
    if (t < 0 || t > 0.9) {
      material.opacity = 0;
      return;
    }
    const arr = geo.getAttribute("position") as BufferAttribute;
    for (let i = 0; i < BURST_COUNT; i++) {
      arr.setXYZ(i, vel[i * 3]! * t * 0.9, vel[i * 3 + 1]! * t * 0.6, vel[i * 3 + 2]! * t * 0.9);
    }
    arr.needsUpdate = true;
    material.opacity = 1 - t / 0.9;
  });
  return <primitive object={points} position={[0, ALTAR_Y, 0.2]} />;
}

function Scene({
  model,
  ingredients,
  layout,
  station,
  accent,
  ritual,
  reduced,
  explodeOn,
  spinOn,
  gridOn,
  resetSignal,
  item,
}: {
  model: VoxelModel | null;
  ingredients: TomeIngredient[];
  layout: "grid" | "station";
  station: { name: string; icon: string | null } | null;
  accent: string;
  ritual: { current: Ritual };
  reduced: boolean;
  explodeOn: boolean;
  spinOn: boolean;
  gridOn: boolean;
  resetSignal: number;
  item: TomeItem;
}) {
  const controls = useRef<ComponentRef<typeof OrbitControls>>(null);
  const { camera, size } = useThree();
  const [fit, setFit] = useState<Fit | null>(null);
  const fitRef = useRef<Fit | null>(null);
  const pedestal = useRef<Group>(null);
  const itemGroup = useRef<Group>(null);
  const altar = useRef<Group>(null);
  const gridLines = useRef<LineSegments>(null);
  const targets = useMemo(() => targetsOf(ingredients, layout), [ingredients, layout]);
  const gridGeo = useMemo(() => {
    const pts: number[] = [];
    const half = GRID_GAP * 1.5;
    for (let k = -1; k <= 2; k++) {
      const o = (k - 0.5) * GRID_GAP;
      pts.push(-half, o, 0, half, o, 0, o, -half, 0, o, half, 0);
    }
    const g = new BufferGeometry();
    g.setAttribute("position", new BufferAttribute(new Float32Array(pts), 3));
    return g;
  }, []);
  const gridMat = useMemo(() => new LineBasicMaterial({ color: accent, transparent: true, opacity: 0 }), [accent]);
  const plateGeo = useMemo(() => new PlaneGeometry(GRID_GAP * 0.9, GRID_GAP * 0.9), []);
  const plateMat = useMemo(() => new MeshBasicMaterial({ color: accent, transparent: true, opacity: 0, depthWrite: false }), [accent]);
  const plinthGeo = useMemo(() => new CylinderGeometry(0.85, 0.95, 0.12, 48), []);
  const plinthMat = useMemo(() => new MeshStandardMaterial({ color: 0x14171f, roughness: 0.6, metalness: 0.4 }), []);
  const ringGeo = useMemo(() => new RingGeometry(0.88, 0.92, 72), []);
  const ringMat = useMemo(() => new MeshBasicMaterial({ color: accent, transparent: true, opacity: 0.7, depthWrite: false }), [accent]);
  const stationTex = useMemo<Texture | null>(() => (station?.icon ? spriteTexture(station.icon) : null), [station]);
  const explodeNow = useRef(0);
  const scaleNow = useRef(0);
  const spinNow = useRef(0);

  useEffect(() => {
    if (model?.wire) model.wire.visible = gridOn;
  }, [model, gridOn]);

  // Frame the model: the sphere that holds it, at the distance where it just fits the narrower of the two fields of view
  // (portrait phones are limited by the horizontal one), with a margin. Recomputed when the canvas changes shape.
  const aspect = size.width / Math.max(1, size.height);
  useEffect(() => {
    if (!model) return;
    const s = modelSphere(model.group);
    const vFov = ((camera as PerspectiveCamera).fov * Math.PI) / 180;
    const hFov = 2 * Math.atan(Math.tan(vFov / 2) * aspect);
    const radius = s.r * 1.5;
    const dist = (radius / Math.sin(Math.min(vFov, hFov) / 2)) * 1.12;
    setFit({ target: [0, ITEM_Y + s.c.y * 1.5, 0], dist });
  }, [model, aspect, camera]);

  const poseTo = useCallback(
    (f: Fit) => {
      fitRef.current = f;
      camera.position.set(f.target[0] + VIEW_DIR.x * f.dist, f.target[1] + VIEW_DIR.y * f.dist, f.target[2] + VIEW_DIR.z * f.dist);
      camera.lookAt(f.target[0], f.target[1], f.target[2]);
      const c = controls.current;
      if (c) {
        c.target.set(f.target[0], f.target[1], f.target[2]);
        c.update();
      }
    },
    [camera],
  );

  useEffect(() => {
    if (fit) poseTo(fit);
  }, [fit, poseTo]);

  // Reset returns to the fit (not to the pose the controls were built with, which is the fallback before a model loads).
  useEffect(() => {
    if (resetSignal > 0 && fitRef.current) poseTo(fitRef.current);
  }, [resetSignal, poseTo]);

  useEffect(
    () => () => {
      gridGeo.dispose();
      gridMat.dispose();
      plateGeo.dispose();
      plateMat.dispose();
      plinthGeo.dispose();
      plinthMat.dispose();
      ringGeo.dispose();
      ringMat.dispose();
    },
    [gridGeo, gridMat, plateGeo, plateMat, plinthGeo, plinthMat, ringGeo, ringMat],
  );

  useFrame((_, delta) => {
    const now = performance.now() / 1000;
    const r = ritual.current;
    const t = r.start < 0 || r.reduced ? Infinity : now - r.start;
    const running = t < RITUAL_END;

    // Holographic grid: materialises, then dissolves into the manifestation.
    const holo = running ? clamp01(t / 0.4) * (1 - clamp01((t - BURST_AT) / 0.45)) : 0;
    gridMat.opacity = holo * 0.8;
    plateMat.opacity = holo * 0.22;

    if (pedestal.current) {
      const lift = reduced ? 0 : Math.sin(now * 1.6) * 0.05;
      pedestal.current.position.y = ITEM_Y + lift;
      if (spinOn && !reduced) spinNow.current += delta * 0.5;
      pedestal.current.rotation.y = spinNow.current;
    }
    if (itemGroup.current) {
      const m = t === Infinity ? 1 : clamp01((t - BURST_AT) / MANIFEST_FOR);
      scaleNow.current = t < BURST_AT ? (t === Infinity ? 1 : 0) : easeOutBack(m);
      itemGroup.current.scale.setScalar(Math.max(0.0001, scaleNow.current) * 1.5);
    }
    if (model) {
      const goal = explodeOn ? 1 : 0;
      explodeNow.current += (goal - explodeNow.current) * Math.min(1, delta * (reduced ? 60 : 7));
      model.explode.value = explodeNow.current;
    }
  });

  return (
    <>
      <ambientLight intensity={0.85} />
      <directionalLight position={[2.5, 4, 3]} intensity={1.45} />
      <directionalLight position={[-3, 2, -3]} intensity={1.0} color={accent} />

      <group ref={altar} position={[0, ALTAR_Y, 0]}>
        <lineSegments ref={gridLines} geometry={gridGeo} material={gridMat} />
        {Array.from({ length: 9 }, (_, i) => {
          const r = Math.floor(i / 3);
          const c = i % 3;
          return <mesh key={i} geometry={plateGeo} material={plateMat} position={[(c - 1) * GRID_GAP, (1 - r) * GRID_GAP, -0.01]} visible={layout === "grid"} />;
        })}
        {layout === "station" && stationTex ? (
          <mesh position={[0, 0, 0]}>
            <planeGeometry args={[0.5, 0.5]} />
            <meshBasicMaterial map={stationTex} transparent alphaTest={0.5} toneMapped={false} />
          </mesh>
        ) : null}
      </group>

      {ingredients.map((ing, i) => (
        <IngredientSprite key={`${item.id}-${i}-${ing.id}`} index={i} target={targets[i] ?? [0, ALTAR_Y, 0]} url={recipeIcon(ing.icon)} dark={ing.icon === null} ritual={ritual} />
      ))}
      <Burst ritual={ritual} accent={accent} />

      <group ref={pedestal} position={[0, ITEM_Y, 0]}>
        <group ref={itemGroup} scale={0.0001}>
          {model ? <primitive object={model.group} /> : null}
        </group>
      </group>

      <mesh geometry={plinthGeo} material={plinthMat} position={[0, PLINTH_Y, 0]} />
      <mesh geometry={ringGeo} material={ringMat} position={[0, PLINTH_Y + 0.07, 0]} rotation={[-Math.PI / 2, 0, 0]} />

      <OrbitControls ref={controls} makeDefault enableDamping dampingFactor={0.08} enablePan={false} minDistance={fit ? fit.dist * 0.6 : 3.4} maxDistance={fit ? fit.dist * 1.6 : 9} />
    </>
  );
}

/**
 * The voxel model's bounds in its own units, read from the geometry through the group's frame. Not read from the
 * live scene: the item starts at scale 0.0001 during the ritual and the pedestal turns, so the scene is the wrong
 * thing to measure. Returns the centre and the half-diagonal (a sphere that holds the whole box).
 */
function modelSphere(group: Group): { c: Vector3; r: number } {
  group.updateWorldMatrix(true, true);
  const inv = new Matrix4().copy(group.matrixWorld).invert();
  const box = new Box3();
  const p = new Vector3();
  group.traverse((o) => {
    const mesh = o as Mesh;
    if (!mesh.isMesh || !mesh.geometry) return;
    mesh.geometry.computeBoundingBox();
    const bb = mesh.geometry.boundingBox;
    if (!bb) return;
    const toLocal = new Matrix4().multiplyMatrices(inv, mesh.matrixWorld);
    for (let i = 0; i < 8; i++) {
      p.set(i & 1 ? bb.max.x : bb.min.x, i & 2 ? bb.max.y : bb.min.y, i & 4 ? bb.max.z : bb.min.z).applyMatrix4(toLocal);
      box.expandByPoint(p);
    }
  });
  if (box.isEmpty()) return { c: new Vector3(), r: 1 };
  return { c: box.getCenter(new Vector3()), r: box.getSize(new Vector3()).length() / 2 };
}

/** The camera pose that frames the item: the look-at point, and the distance along the default viewing direction. */
interface Fit {
  target: V3;
  dist: number;
}
/** The default viewing direction (the pose the stage opens with): a little above, looking down the item. */
const VIEW_DIR = new Vector3(0, 0.25, 1).normalize();

function webglAvailable(): boolean {
  try {
    const c = document.createElement("canvas");
    return c.getContext("webgl2") !== null;
  } catch {
    return false;
  }
}

export function VoxelItemStage(props: VoxelItemStageProps) {
  const { item, ingredients, layout, station, accent, playKey, reduced, labels } = props;
  const box = useRef<HTMLDivElement>(null);
  const ritual = useRef<Ritual>({ start: -1, reduced });
  const [model, setModel] = useState<VoxelModel | null>(null);
  const pictureUrl = recipeIcon(item.icon);
  const [webgl, setWebgl] = useState<"unknown" | "yes" | "no">("unknown");
  const [visible, setVisible] = useState(false);
  const [explodeOn, setExplodeOn] = useState(false);
  const [spinOn, setSpinOn] = useState(true);
  const [gridOn, setGridOn] = useState(false);
  const [resetSignal, setResetSignal] = useState(0);
  const [status, setStatus] = useState("");

  useEffect(() => {
    setWebgl(webglAvailable() ? "yes" : "no");
    return () => disposeVoxelCache();
  }, []);

  useEffect(() => {
    ritual.current.reduced = reduced;
  }, [reduced]);

  useEffect(() => {
    const el = box.current;
    if (!el || typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const io = new IntersectionObserver(([e]) => setVisible(e?.isIntersecting ?? false), { threshold: 0.01 });
    io.observe(el);
    return () => io.disconnect();
  }, []);

  // A model is built once per picture (the cache), and pinned while it is on the pedestal.
  useEffect(() => {
    let alive = true;
    pinModel(pictureUrl, item.kind);
    void modelFor(pictureUrl, item.kind).then((m) => {
      if (alive) setModel(m);
    });
    return () => {
      alive = false;
    };
  }, [pictureUrl, item.kind]);

  // A new recipe starts the ritual; the status line announces it for screen readers.
  useEffect(() => {
    if (playKey === 0) return;
    ritual.current = { start: performance.now() / 1000, reduced };
    setStatus(labels.ritual.replace("{0}", item.name));
    const id = window.setTimeout(() => setStatus(labels.ready.replace("{0}", item.name)), RITUAL_END * 1000);
    return () => window.clearTimeout(id);
    // The ritual restarts on a new recipe only; the labels and reduced flag are read when it starts.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playKey]);

  const frame = webgl === "yes" && visible && !props.collapsed;
  const ready = !reduced && playKey > 0;

  return (
    <div className={`tome-stage-inner${props.collapsed ? " is-collapsed" : ""}`} style={{ ["--accent" as string]: accent }}>
      <div ref={box} className="tome-stage-canvas" role="img" aria-label={`${labels.stage}: ${item.name}. ${labels.hint}`}>
        {webgl === "no" || webgl === "unknown" ? (
          <div className="tome-stage-poster">
            {pictureUrl ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={pictureUrl} alt="" width={160} height={160} className="ac-pixel" />
            ) : null}
            {webgl === "no" ? <p className="ac-small">{labels.noWebgl}</p> : null}
          </div>
        ) : (
          <Canvas
            dpr={[1, 2]}
            frameloop={frame ? "always" : "never"}
            camera={{ position: [0, 1.0, 6.2], fov: 30, near: 0.1, far: 60 }}
            gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
            style={{ background: "transparent" }}
          >
            <Scene
              model={model}
              ingredients={ready ? ingredients : []}
              layout={layout}
              station={station}
              accent={accent}
              ritual={ritual}
              reduced={reduced}
              explodeOn={explodeOn}
              spinOn={spinOn}
              gridOn={gridOn}
              resetSignal={resetSignal}
              item={item}
            />
          </Canvas>
        )}
      </div>
      <div className="tome-stage-controls" role="group" aria-label={labels.stage}>
        <button type="button" className="ac-chip" aria-pressed={explodeOn} onClick={() => setExplodeOn((v) => !v)}>
          {labels.explode}
        </button>
        <button type="button" className="ac-chip" aria-pressed={spinOn} onClick={() => setSpinOn((v) => !v)}>
          {labels.spin}
        </button>
        <button type="button" className="ac-chip" aria-pressed={gridOn} onClick={() => setGridOn((v) => !v)}>
          {labels.grid}
        </button>
        <button type="button" className="ac-chip" onClick={() => setResetSignal((n) => n + 1)}>
          {labels.reset}
        </button>
      </div>
      <p className="sr-only" aria-live="polite">
        {status}
      </p>
    </div>
  );
}

