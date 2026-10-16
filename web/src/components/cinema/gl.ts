/**
 * WebGL2 plumbing for the Act I stage: shader programs, and a frame store that keeps the footage's
 * compressed bytes for every frame (a few megabytes in all) and decodes frames to GPU textures on
 * demand, least recently used first, so the GPU holds a bounded window of frames whatever the scroll.
 */

export function compile(gl: WebGL2RenderingContext, type: number, src: string): WebGLShader {
  const shader = gl.createShader(type);
  if (shader === null) throw new Error("createShader");
  gl.shaderSource(shader, src);
  gl.compileShader(shader);
  if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
    const log = gl.getShaderInfoLog(shader) ?? "";
    gl.deleteShader(shader);
    throw new Error(`shader: ${log}`);
  }
  return shader;
}

export function program(gl: WebGL2RenderingContext, vert: string, frag: string): WebGLProgram {
  const p = gl.createProgram();
  if (p === null) throw new Error("createProgram");
  gl.attachShader(p, compile(gl, gl.VERTEX_SHADER, vert));
  gl.attachShader(p, compile(gl, gl.FRAGMENT_SHADER, frag));
  gl.linkProgram(p);
  if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error(`link: ${gl.getProgramInfoLog(p) ?? ""}`);
  return p;
}

/** The empty vertex array the full-screen triangle is drawn with (positions come from gl_VertexID). */
export function emptyVao(gl: WebGL2RenderingContext): WebGLVertexArrayObject {
  const vao = gl.createVertexArray();
  if (vao === null) throw new Error("createVertexArray");
  return vao;
}

export interface FrameStoreOptions {
  count: number;
  capacity: number;
  /** Premultiply on upload (the eagle, whose edges are semi-transparent). */
  premultiply: boolean;
  url: (index: number) => string;
  /** Called when a frame arrives or reaches the GPU (the stage redraws on it when it is not animating). */
  onChange?: () => void;
}

export class FrameStore {
  private readonly gl: WebGL2RenderingContext;
  private readonly opts: FrameStoreOptions;
  private readonly blobs: (Blob | null)[];
  private readonly tex = new Map<number, { tex: WebGLTexture; used: number }>();
  private readonly pending = new Set<number>();
  private readonly protect = new Set<number>();
  private clock = 0;
  private inflight = 0;
  private disposed = false;

  constructor(gl: WebGL2RenderingContext, opts: FrameStoreOptions) {
    this.gl = gl;
    this.opts = opts;
    this.blobs = new Array<Blob | null>(opts.count).fill(null);
  }

  /** Fetches the compressed frames in the given order, a few at a time. Never throws. */
  async load(order: number[], concurrency = 3): Promise<void> {
    let next = 0;
    const worker = async (): Promise<void> => {
      while (!this.disposed && next < order.length) {
        const i = order[next++];
        if (i === undefined || this.blobs[i] !== null) continue;
        try {
          const res = await fetch(this.opts.url(i), { cache: "force-cache" });
          if (res.ok) {
            this.blobs[i] = await res.blob();
            this.opts.onChange?.();
          }
        } catch {
          // A frame that fails to arrive leaves its neighbours on screen.
        }
      }
    };
    await Promise.all(Array.from({ length: concurrency }, worker));
  }

  has(i: number): boolean {
    return this.tex.has(i);
  }

  /** The texture of a decoded frame (marks it recently used), or null. */
  get(i: number): WebGLTexture | null {
    const e = this.tex.get(i);
    if (e === undefined) return null;
    e.used = ++this.clock;
    return e.tex;
  }

  /** The decoded frame nearest to i, or null while nothing is decoded yet. */
  nearest(i: number): number | null {
    let best: number | null = null;
    for (const k of this.tex.keys()) {
      if (best === null || Math.abs(k - i) < Math.abs(best - i)) best = k;
    }
    return best;
  }

  /** Frames that must not be evicted this frame. */
  setProtected(indices: readonly number[]): void {
    this.protect.clear();
    for (const i of indices) this.protect.add(i);
  }

  /** Starts decoding a frame whose bytes have arrived. Cheap to call every frame. */
  request(i: number): void {
    if (this.disposed || this.tex.has(i) || this.pending.has(i) || this.inflight >= 2) return;
    const blob = this.blobs[i];
    if (blob === null || blob === undefined) return;
    this.pending.add(i);
    this.inflight += 1;
    createImageBitmap(blob)
      .then((bmp) => {
        this.pending.delete(i);
        this.inflight -= 1;
        if (this.disposed) {
          bmp.close();
          return;
        }
        this.upload(i, bmp);
        this.opts.onChange?.();
      })
      .catch(() => {
        this.pending.delete(i);
        this.inflight -= 1;
      });
  }

  dispose(): void {
    this.disposed = true;
    for (const e of this.tex.values()) this.gl.deleteTexture(e.tex);
    this.tex.clear();
  }

  private upload(i: number, bmp: ImageBitmap): void {
    const gl = this.gl;
    if (this.tex.size >= this.opts.capacity) this.evict();
    const tex = gl.createTexture();
    if (tex === null) {
      bmp.close();
      return;
    }
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, this.opts.premultiply);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, bmp);
    gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    bmp.close();
    this.tex.set(i, { tex, used: ++this.clock });
  }

  private evict(): void {
    let victim: number | null = null;
    let oldest = Infinity;
    for (const [k, e] of this.tex) {
      if (this.protect.has(k) || k === 0) continue;
      if (e.used < oldest) {
        oldest = e.used;
        victim = k;
      }
    }
    if (victim === null) return;
    const e = this.tex.get(victim);
    if (e !== undefined) this.gl.deleteTexture(e.tex);
    this.tex.delete(victim);
  }
}
