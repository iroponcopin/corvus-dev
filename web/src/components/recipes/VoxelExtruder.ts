import {
  BoxGeometry,
  BufferAttribute,
  BufferGeometry,
  Group,
  Mesh,
  MeshBasicMaterial,
  MeshStandardMaterial,
  NearestFilter,
  SRGBColorSpace,
  type Texture,
  TextureLoader,
} from "three";
import { loadPixels, srgbToLinear } from "@/realms/voxel";

/**
 * The 3D pedestal's item models. A recipe's picture is read pixel by pixel (loadPixels and srgbToLinear, shared
 * with the skin and the Synthesizer), every opaque pixel becomes a voxel `depth` cells thick, and only the faces
 * that touch air are kept, so the mesh stays a few thousand triangles. Bright pixels also get an unlit glow layer
 * (the emissive part of the look; there is no bloom pass). Each model is built once and kept in a bounded LRU; an
 * evicted model's geometries, materials and textures are disposed, so a long session does not leak WebGL objects.
 *
 * The explode view is one shared uniform: every vertex carries its voxel's offset from the model's centre, and the
 * shader moves it by uExplode. Nothing is rebuilt to explode a model.
 */

export type ItemKind = "flat" | "cube" | "icon" | "none";

export interface VoxelModel {
  group: Group;
  /** 0 = assembled, 1 = exploded. Shared by every material of the model. */
  explode: { value: number };
  /** The wireframe overlay (the voxel grid), hidden until asked for. Null for blocks. */
  wire: Mesh | null;
  dispose(): void;
}

const LRU_LIMIT = 12;
const TEXTURE_LIMIT = 48;

/** Textures of recipe pictures (nearest filtering: the pixels stay square). Evicted ones are disposed. */
const textures = new Map<string, Texture>();

export function spriteTexture(url: string): Texture {
  const hit = textures.get(url);
  if (hit !== undefined) {
    textures.delete(url);
    textures.set(url, hit);
    return hit;
  }
  const t = new TextureLoader().load(url);
  t.colorSpace = SRGBColorSpace;
  t.magFilter = NearestFilter;
  t.minFilter = NearestFilter;
  t.generateMipmaps = false;
  textures.set(url, t);
  while (textures.size > TEXTURE_LIMIT) {
    const oldest = textures.keys().next().value;
    if (oldest === undefined) break;
    textures.get(oldest)?.dispose();
    textures.delete(oldest);
  }
  return t;
}

/** Adds the explode offset to a material's vertices. Every material shares the same uniform object. */
function withExplode(material: MeshStandardMaterial | MeshBasicMaterial, explode: { value: number }): void {
  material.onBeforeCompile = (shader) => {
    shader.uniforms.uExplode = explode;
    shader.vertexShader = `attribute vec3 aOffset;\nuniform float uExplode;\n${shader.vertexShader}`.replace(
      "#include <begin_vertex>",
      "#include <begin_vertex>\ntransformed += aOffset * uExplode;",
    );
  };
  material.customProgramCacheKey = () => "corvus-voxel-explode";
}

interface Faces {
  positions: number[];
  normals: number[];
  colors: number[];
  offsets: number[];
}

function newFaces(): Faces {
  return { positions: [], normals: [], colors: [], offsets: [] };
}

type V3 = [number, number, number];

/** Emits one quad (two triangles, counter-clockwise seen from its normal) with colour and explode offset. */
function quad(f: Faces, p: [V3, V3, V3, V3], n: V3, c: V3, shade: number, off: V3): void {
  const [a, b, cc, d] = p;
  for (const v of [a, b, cc, a, cc, d]) {
    f.positions.push(v[0], v[1], v[2]);
    f.normals.push(n[0], n[1], n[2]);
    f.colors.push(c[0] * shade, c[1] * shade, c[2] * shade);
    f.offsets.push(off[0], off[1], off[2]);
  }
}

function toGeometry(f: Faces): BufferGeometry {
  const g = new BufferGeometry();
  g.setAttribute("position", new BufferAttribute(new Float32Array(f.positions), 3));
  g.setAttribute("normal", new BufferAttribute(new Float32Array(f.normals), 3));
  g.setAttribute("color", new BufferAttribute(new Float32Array(f.colors), 3));
  g.setAttribute("aOffset", new BufferAttribute(new Float32Array(f.offsets), 3));
  g.computeBoundingSphere();
  return g;
}

/** Voxelises a picture: the longest side spans 1 unit, centred on the origin. */
async function voxelise(url: string): Promise<{ body: BufferGeometry; glow: BufferGeometry | null }> {
  const { w, h, data } = await loadPixels(url);
  const depth = Math.max(1, Math.round(Math.max(w, h) / 16));
  const s = 1 / Math.max(w, h);
  const alphaAt = (x: number, y: number): number => (x < 0 || y < 0 || x >= w || y >= h ? 0 : (data[(y * w + x) * 4 + 3] ?? 0));
  const solid = (x: number, y: number, z: number): boolean => z >= 0 && z < depth && alphaAt(x, y) > 110;
  const body = newFaces();
  const glow = newFaces();

  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (alphaAt(x, y) <= 110) continue;
      const i = (y * w + x) * 4;
      const r8 = data[i] ?? 0;
      const g8 = data[i + 1] ?? 0;
      const b8 = data[i + 2] ?? 0;
      const c: V3 = [srgbToLinear(r8), srgbToLinear(g8), srgbToLinear(b8)];
      const luma = 0.2126 * (r8 / 255) + 0.7152 * (g8 / 255) + 0.0722 * (b8 / 255);
      const bright = luma > 0.82 && alphaAt(x, y) > 200;
      const x0 = (x - w / 2) * s;
      const x1 = x0 + s;
      const y1 = (h / 2 - y) * s;
      const y0 = y1 - s;
      for (let z = 0; z < depth; z++) {
        if (!solid(x, y, z)) continue;
        const z0 = (z - depth / 2) * s;
        const z1 = z0 + s;
        // The voxel's offset from the model's centre: the explode view pushes every voxel outward from it.
        const off: V3 = [((x0 + x1) / 2) * 0.7, ((y0 + y1) / 2) * 0.7, ((z0 + z1) / 2) * 1.4];
        const targets = bright ? [body, glow] : [body];
        const emit = (p: [V3, V3, V3, V3], n: V3, k: number): void => {
          for (const f of targets) quad(f, p, n, c, k, off);
        };
        if (z === depth - 1 || !solid(x, y, z + 1)) emit([[x0, y0, z1], [x1, y0, z1], [x1, y1, z1], [x0, y1, z1]], [0, 0, 1], 1);
        if (z === 0 || !solid(x, y, z - 1)) emit([[x1, y0, z0], [x0, y0, z0], [x0, y1, z0], [x1, y1, z0]], [0, 0, -1], 0.72);
        if (!solid(x, y - 1, z)) emit([[x0, y1, z1], [x1, y1, z1], [x1, y1, z0], [x0, y1, z0]], [0, 1, 0], 0.95);
        if (!solid(x, y + 1, z)) emit([[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]], [0, -1, 0], 0.55);
        if (!solid(x - 1, y, z)) emit([[x0, y0, z0], [x0, y0, z1], [x0, y1, z1], [x0, y1, z0]], [-1, 0, 0], 0.7);
        if (!solid(x + 1, y, z)) emit([[x1, y0, z1], [x1, y0, z0], [x1, y1, z0], [x1, y1, z1]], [1, 0, 0], 0.8);
      }
    }
  }
  return { body: toGeometry(body), glow: glow.positions.length > 0 ? toGeometry(glow) : null };
}

/** A voxel picture, a block (the picture on a cube), or no picture (a dark cube). */
async function build(url: string | null, kind: ItemKind): Promise<VoxelModel> {
  const group = new Group();
  const explode = { value: 0 };
  const owned: { dispose(): void }[] = [];
  const dispose = (): void => {
    for (const o of owned) o.dispose();
    group.clear();
  };

  if (url === null || kind === "none" || kind === "cube") {
    const geo = new BoxGeometry(0.9, 0.9, 0.9);
    const blank = url === null || kind === "none";
    const mat = new MeshStandardMaterial({
      color: blank ? 0x1a1d24 : 0xffffff,
      map: blank ? null : spriteTexture(url),
      roughness: blank ? 0.2 : 0.35,
      metalness: 0.15,
    });
    owned.push(geo, mat);
    group.add(new Mesh(geo, mat));
    return { group, explode, wire: null, dispose };
  }

  const { body, glow } = await voxelise(url);
  owned.push(body);
  const bodyMat = new MeshStandardMaterial({ vertexColors: true, roughness: 0.35, metalness: 0.15 });
  withExplode(bodyMat, explode);
  owned.push(bodyMat);
  group.add(new Mesh(body, bodyMat));
  if (glow !== null) {
    owned.push(glow);
    const glowMat = new MeshBasicMaterial({ vertexColors: true, toneMapped: false });
    withExplode(glowMat, explode);
    owned.push(glowMat);
    const glowMesh = new Mesh(glow, glowMat);
    glowMesh.scale.setScalar(1.002);
    group.add(glowMesh);
  }
  const wireMat = new MeshBasicMaterial({ wireframe: true, transparent: true, opacity: 0.22, color: 0xffffff, depthWrite: false });
  withExplode(wireMat, explode);
  owned.push(wireMat);
  const wire = new Mesh(body, wireMat);
  wire.visible = false;
  wire.scale.setScalar(1.003);
  group.add(wire);
  return { group, explode, wire, dispose };
}

const models = new Map<string, Promise<VoxelModel>>();
const liveModels = new Map<string, VoxelModel>();
let pinned: string | null = null;

/**
 * The model for an item, built on first use. The pinned model (the one on the pedestal) is never evicted; when the
 * cache is over its limit the least recently used built model is disposed.
 */
export function modelFor(url: string | null, kind: ItemKind): Promise<VoxelModel> {
  const key = `${kind}|${url ?? ""}`;
  const hit = models.get(key);
  if (hit !== undefined) {
    models.delete(key);
    models.set(key, hit);
    return hit;
  }
  const p = build(url, kind).then((m) => {
    liveModels.set(key, m);
    return m;
  });
  p.catch(() => models.delete(key));
  models.set(key, p);
  if (models.size > LRU_LIMIT) {
    for (const oldest of models.keys()) {
      if (models.size <= LRU_LIMIT) break;
      // A model still building has nothing to dispose yet; the pinned one stays on the pedestal.
      const m = liveModels.get(oldest);
      if (m === undefined || oldest === key || oldest === pinned) continue;
      models.delete(oldest);
      liveModels.delete(oldest);
      m.dispose();
    }
  }
  return p;
}

/** Keeps a model out of eviction while it is on the pedestal. */
export function pinModel(url: string | null, kind: ItemKind): void {
  pinned = `${kind}|${url ?? ""}`;
}

/** Disposes every cached model and texture (the page unmounts). */
export function disposeVoxelCache(): void {
  for (const p of models.values()) void p.then((m) => m.dispose());
  models.clear();
  liveModels.clear();
  for (const t of textures.values()) t.dispose();
  textures.clear();
  pinned = null;
}
