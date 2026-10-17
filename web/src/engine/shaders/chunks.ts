/**
 * GLSL shared by every material of the scene. Written GLSL ES 1.0-style; three.js maps it to
 * GLSL 3 on WebGL 2. Every function here is allocation-free by nature (it is a shader), and
 * pure: the same inputs give the same pixels on every GPU that honours highp.
 */

export const glsl = String.raw;

export const COMMON = glsl`
#define TAU 6.283185307179586
#define PI 3.141592653589793

float hash11(float p) {
  p = fract(p * 0.1031);
  p *= p + 33.33;
  p *= p + p;
  return fract(p);
}

float hash12(vec2 p) {
  vec3 p3 = fract(vec3(p.xyx) * 0.1031);
  p3 += dot(p3, p3.yzx + 33.33);
  return fract((p3.x + p3.y) * p3.z);
}

vec4 hash42(vec2 p) {
  vec4 p4 = fract(vec4(p.xyxy) * vec4(0.1031, 0.1030, 0.0973, 0.1099));
  p4 += dot(p4, p4.wzxy + 33.33);
  return fract((p4.xxyz + p4.yzzw) * p4.zywx);
}

vec3 hash33(vec3 p3) {
  p3 = fract(p3 * vec3(0.1031, 0.1030, 0.0973));
  p3 += dot(p3, p3.yxz + 33.33);
  return fract((p3.xxy + p3.yxx) * p3.zyx);
}

vec3 rotateByQuat(vec3 v, vec4 q) {
  return v + 2.0 * cross(q.xyz, cross(q.xyz, v) + q.w * v);
}

mat2 rot2(float a) {
  float c = cos(a), s = sin(a);
  return mat2(c, -s, s, c);
}

vec3 toSRGB(vec3 c) {
  c = max(c, vec3(0.0));
  return mix(c * 12.92, 1.055 * pow(c, vec3(1.0 / 2.4)) - 0.055, step(vec3(0.0031308), c));
}

vec3 fromSRGB(vec3 c) {
  return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(vec3(0.04045), c));
}

/** Filmic shoulder (Hable-like, cheap): keeps highlights from clipping to flat white. */
vec3 tonemap(vec3 x) {
  x = max(x, vec3(0.0));
  return x * (1.0 + x * 0.12) / (1.0 + x);
}

/** Visible spectrum, 0 = red .. 1 = violet, for dispersion fire. */
vec3 spectral(float t) {
  t = clamp(t, 0.0, 1.0);
  vec3 c = vec3(
    smoothstep(0.55, 0.0, t) + smoothstep(0.82, 1.0, t) * 0.55,
    1.0 - abs(t - 0.45) * 2.6,
    smoothstep(0.35, 0.85, t)
  );
  return clamp(c, 0.0, 1.0);
}

/** 22 % of the particles are the far star sphere; the rest is formation matter. */
float isStarSeed(vec4 s) {
  return step(fract(s.x * 91.7 + s.w * 13.3), 0.22);
}

/** Interleaved gradient noise: kills 8-bit banding in dark gradients. */
float ign(vec2 fragCoord) {
  return fract(52.9829189 * fract(dot(fragCoord, vec2(0.06711056, 0.00583715))));
}
`;

/** Simplex noise 3D (Ashima / Ian McEwan, MIT) and its curl, for the flow field. */
export const NOISE = glsl`
vec4 permute(vec4 x) { return mod(((x * 34.0) + 1.0) * x, 289.0); }
vec4 taylorInvSqrt(vec4 r) { return 1.79284291400159 - 0.85373472095314 * r; }

float snoise(vec3 v) {
  const vec2 C = vec2(1.0 / 6.0, 1.0 / 3.0);
  const vec4 D = vec4(0.0, 0.5, 1.0, 2.0);
  vec3 i = floor(v + dot(v, C.yyy));
  vec3 x0 = v - i + dot(i, C.xxx);
  vec3 g = step(x0.yzx, x0.xyz);
  vec3 l = 1.0 - g;
  vec3 i1 = min(g.xyz, l.zxy);
  vec3 i2 = max(g.xyz, l.zxy);
  vec3 x1 = x0 - i1 + C.xxx;
  vec3 x2 = x0 - i2 + 2.0 * C.xxx;
  vec3 x3 = x0 - 1.0 + 3.0 * C.xxx;
  i = mod(i, 289.0);
  vec4 p = permute(permute(permute(i.z + vec4(0.0, i1.z, i2.z, 1.0)) + i.y + vec4(0.0, i1.y, i2.y, 1.0)) + i.x + vec4(0.0, i1.x, i2.x, 1.0));
  float n_ = 1.0 / 7.0;
  vec3 ns = n_ * D.wyz - D.xzx;
  vec4 j = p - 49.0 * floor(p * ns.z * ns.z);
  vec4 x_ = floor(j * ns.z);
  vec4 y_ = floor(j - 7.0 * x_);
  vec4 x = x_ * ns.x + ns.yyyy;
  vec4 y = y_ * ns.x + ns.yyyy;
  vec4 h = 1.0 - abs(x) - abs(y);
  vec4 b0 = vec4(x.xy, y.xy);
  vec4 b1 = vec4(x.zw, y.zw);
  vec4 s0 = floor(b0) * 2.0 + 1.0;
  vec4 s1 = floor(b1) * 2.0 + 1.0;
  vec4 sh = -step(h, vec4(0.0));
  vec4 a0 = b0.xzyw + s0.xzyw * sh.xxyy;
  vec4 a1 = b1.xzyw + s1.xzyw * sh.zzww;
  vec3 p0 = vec3(a0.xy, h.x);
  vec3 p1 = vec3(a0.zw, h.y);
  vec3 p2 = vec3(a1.xy, h.z);
  vec3 p3 = vec3(a1.zw, h.w);
  vec4 norm = taylorInvSqrt(vec4(dot(p0, p0), dot(p1, p1), dot(p2, p2), dot(p3, p3)));
  p0 *= norm.x;
  p1 *= norm.y;
  p2 *= norm.z;
  p3 *= norm.w;
  vec4 m = max(0.6 - vec4(dot(x0, x0), dot(x1, x1), dot(x2, x2), dot(x3, x3)), 0.0);
  m = m * m;
  return 42.0 * dot(m * m, vec4(dot(p0, x0), dot(p1, x1), dot(p2, x2), dot(p3, x3)));
}

vec3 snoiseVec3(vec3 x) {
  return vec3(snoise(x), snoise(vec3(x.y - 19.1, x.z + 33.4, x.x + 47.2)), snoise(vec3(x.z + 74.2, x.x - 124.5, x.y + 99.4)));
}

/** Divergence-free flow: particles swirl without bunching up or thinning out. */
vec3 curlNoise(vec3 p) {
  const float e = 0.1;
  vec3 dx = vec3(e, 0.0, 0.0);
  vec3 dy = vec3(0.0, e, 0.0);
  vec3 dz = vec3(0.0, 0.0, e);
  vec3 px0 = snoiseVec3(p - dx);
  vec3 px1 = snoiseVec3(p + dx);
  vec3 py0 = snoiseVec3(p - dy);
  vec3 py1 = snoiseVec3(p + dy);
  vec3 pz0 = snoiseVec3(p - dz);
  vec3 pz1 = snoiseVec3(p + dz);
  float x = py1.z - py0.z - pz1.y + pz0.y;
  float y = pz1.x - pz0.x - px1.z + px0.z;
  float z = px1.y - px0.y - py1.x + py0.x;
  return normalize(vec3(x, y, z) / (2.0 * e) + 1e-6);
}
`;

/**
 * A procedural studio environment: OLED-black space, three softboxes (the crisp reflections
 * that make brushed titanium read as metal), a faint aurora in the upper sky and the brand tint.
 * Shared by the titanium, the diamond rings and the gem so they reflect one coherent world.
 */
export const ENVIRONMENT = glsl`
uniform vec3 uTint;
uniform float uTime;

float softbox(vec3 d, vec3 axis, vec3 up, float w, float h, float soft) {
  float facing = dot(d, axis);
  if (facing <= 0.0) return 0.0;
  vec3 side = normalize(cross(axis, up));
  vec2 q = vec2(dot(d, side), dot(d, up)) / facing;
  vec2 e = abs(q) - vec2(w, h);
  float dist = length(max(e, 0.0)) + min(max(e.x, e.y), 0.0);
  return smoothstep(soft, -soft * 0.25, dist);
}

vec3 environment(vec3 d) {
  d = normalize(d);
  vec3 col = vec3(0.0);
  // Deep field: almost black, a breath of blue towards the horizon.
  float horizon = 1.0 - abs(d.y);
  col += vec3(0.004, 0.006, 0.012) * horizon * horizon;
  // A faint light in the upper sky, carried by the brand tint.
  float band = sin(d.x * 3.1 + d.z * 2.3 + uTime * 0.05) * 0.5 + 0.5;
  float aur = smoothstep(0.15, 0.75, d.y) * smoothstep(1.0, 0.55, d.y) * band;
  col += uTint * aur * 0.05;
  // Key softbox overhead-front, two strip lights at the sides, a low rim.
  col += vec3(1.0, 0.985, 0.96) * 2.4 * softbox(d, normalize(vec3(0.15, 0.85, 0.5)), vec3(0.0, 0.0, -1.0), 0.65, 0.42, 0.08);
  col += vec3(0.85, 0.9, 1.0) * 1.35 * softbox(d, normalize(vec3(-1.0, 0.1, 0.2)), vec3(0.0, 1.0, 0.0), 0.08, 0.9, 0.05);
  col += vec3(0.9, 0.93, 1.0) * 1.1 * softbox(d, normalize(vec3(1.0, 0.05, -0.25)), vec3(0.0, 1.0, 0.0), 0.06, 0.9, 0.05);
  col += uTint * 0.9 * softbox(d, normalize(vec3(0.0, -0.55, -1.0)), vec3(0.0, 1.0, 0.0), 1.2, 0.08, 0.12);
  return col;
}
`;
