import { BoxGeometry, BufferAttribute, BufferGeometry } from "three";

/**
 * Item icons as solid objects, the way Minecraft draws a held item: every opaque pixel of the
 * sprite becomes a voxel one pixel deep, and only the faces that touch air are kept. Blocks
 * ("cube") are the icon on all six faces of a cube instead. Geometries are cached per icon and
 * built once, off the frame loop.
 */

const cache = new Map<string, Promise<BufferGeometry>>();

export function loadPixels(url: string): Promise<{ w: number; h: number; data: Uint8ClampedArray }> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.decoding = "async";
    img.onload = () => {
      // Animation strips (16×48) show their first frame.
      const w = img.naturalWidth;
      const h = Math.min(img.naturalHeight, w);
      const canvas = document.createElement("canvas");
      canvas.width = w;
      canvas.height = h;
      const ctx = canvas.getContext("2d", { willReadFrequently: true });
      if (ctx === null) {
        reject(new Error("no 2d context"));
        return;
      }
      ctx.drawImage(img, 0, 0, w, h, 0, 0, w, h);
      resolve({ w, h, data: ctx.getImageData(0, 0, w, h).data });
    };
    img.onerror = () => reject(new Error(`could not load ${url}`));
    img.src = url;
  });
}

export function srgbToLinear(c: number): number {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

/** Extruded sprite: unit size (the longest side spans 1), centred, one pixel deep. */
async function extrude(url: string): Promise<BufferGeometry> {
  const { w, h, data } = await loadPixels(url);
  const solid = (x: number, y: number): boolean => x >= 0 && y >= 0 && x < w && y < h && (data[(y * w + x) * 4 + 3] ?? 0) > 110;
  const positions: number[] = [];
  const normals: number[] = [];
  const colors: number[] = [];
  const shade: number[] = [];
  const s = 1 / Math.max(w, h);
  const depth = 1 / 16;
  // Quad helper: four corners in order, normal, colour.
  const quad = (
    ax: number, ay: number, az: number,
    bx: number, by: number, bz: number,
    cx: number, cy: number, cz: number,
    dx: number, dy: number, dz: number,
    nx: number, ny: number, nz: number,
    r: number, g: number, b: number, k: number,
  ): void => {
    positions.push(ax, ay, az, bx, by, bz, cx, cy, cz, ax, ay, az, cx, cy, cz, dx, dy, dz);
    for (let i = 0; i < 6; i++) {
      normals.push(nx, ny, nz);
      colors.push(r, g, b);
      shade.push(k);
    }
  };
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      if (!solid(x, y)) continue;
      const i = (y * w + x) * 4;
      const r = srgbToLinear(data[i] ?? 0);
      const g = srgbToLinear(data[i + 1] ?? 0);
      const b = srgbToLinear(data[i + 2] ?? 0);
      const x0 = (x - w / 2) * s;
      const x1 = x0 + s;
      const y1 = (h / 2 - y) * s;
      const y0 = y1 - s;
      const z0 = -depth / 2;
      const z1 = depth / 2;
      // Front and back.
      quad(x0, y0, z1, x1, y0, z1, x1, y1, z1, x0, y1, z1, 0, 0, 1, r, g, b, 1);
      quad(x1, y0, z0, x0, y0, z0, x0, y1, z0, x1, y1, z0, 0, 0, -1, r, g, b, 0.72);
      // Sides only where the neighbour is air (the edge of the sprite).
      if (!solid(x, y - 1)) quad(x0, y1, z1, x1, y1, z1, x1, y1, z0, x0, y1, z0, 0, 1, 0, r, g, b, 0.95);
      if (!solid(x, y + 1)) quad(x0, y0, z0, x1, y0, z0, x1, y0, z1, x0, y0, z1, 0, -1, 0, r, g, b, 0.55);
      if (!solid(x - 1, y)) quad(x0, y0, z0, x0, y0, z1, x0, y1, z1, x0, y1, z0, -1, 0, 0, r, g, b, 0.7);
      if (!solid(x + 1, y)) quad(x1, y0, z1, x1, y0, z0, x1, y1, z0, x1, y1, z1, 1, 0, 0, r, g, b, 0.8);
    }
  }
  const g = new BufferGeometry();
  g.setAttribute("position", new BufferAttribute(new Float32Array(positions), 3));
  g.setAttribute("normal", new BufferAttribute(new Float32Array(normals), 3));
  g.setAttribute("color", new BufferAttribute(new Float32Array(colors), 3));
  g.setAttribute("aShade", new BufferAttribute(new Float32Array(shade), 1));
  g.computeBoundingSphere();
  return g;
}

/** A block: the icon on all six faces of a cube of side 0.86 (the shader samples the texture). */
function cube(): BufferGeometry {
  const g = new BoxGeometry(0.86, 0.86, 0.86);
  const n = g.getAttribute("position").count;
  const shade = new Float32Array(n);
  const normal = g.getAttribute("normal");
  for (let i = 0; i < n; i++) {
    const ny = normal.getY(i);
    const nx = normal.getX(i);
    shade[i] = ny > 0.5 ? 1 : ny < -0.5 ? 0.5 : Math.abs(nx) > 0.5 ? 0.8 : 0.66;
  }
  g.setAttribute("aShade", new BufferAttribute(shade, 1));
  return g;
}

let sharedCube: BufferGeometry | null = null;

export function voxelGeometry(url: string | null, kind: "flat" | "cube" | "icon" | "none"): Promise<BufferGeometry> {
  if (kind === "cube" || url === null || kind === "none") {
    sharedCube ??= cube();
    return Promise.resolve(sharedCube);
  }
  let p = cache.get(url);
  if (p === undefined) {
    p = extrude(url);
    cache.set(url, p);
  }
  return p;
}
