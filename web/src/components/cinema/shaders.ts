/**
 * GLSL ES 3.00 for the Act I stage. One full-screen triangle; the fragment shaders do everything:
 * the footage's cover fit, the depth of field, the chromatic edge, the filmic grade, the sun's glow,
 * the drifting mist, the grain and the vignette (background), and the sunrise grade with a warm rim
 * on the eagle's sun-facing edge (eagle).
 */

export const VERT = `#version 300 es
precision highp float;
void main() {
  // A single oversized triangle that covers the viewport.
  vec2 p = vec2(float((gl_VertexID << 1) & 2), float(gl_VertexID & 2));
  gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}
`;

const COMMON = `
float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}
float vnoise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  f = f * f * (3.0 - 2.0 * f);
  float a = hash(i);
  float b = hash(i + vec2(1.0, 0.0));
  float c = hash(i + vec2(0.0, 1.0));
  float d = hash(i + vec2(1.0, 1.0));
  return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}
float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.5;
  for (int i = 0; i < 5; i++) {
    v += a * vnoise(p);
    p = p * 2.03 + vec2(11.7, 3.1);
    a *= 0.5;
  }
  return v;
}
// ACES filmic tone curve (Narkowicz fit).
vec3 aces(vec3 x) {
  return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0);
}
`;

export const BG_FRAG = `#version 300 es
precision highp float;
${COMMON}
uniform sampler2D uA;
uniform sampler2D uB;
uniform float uMix;
uniform vec2 uRes;
uniform vec2 uScale;
uniform vec2 uSun;
uniform float uBlurPx;
uniform float uTime;
uniform float uGrain;
uniform float uCA;
uniform float uMist;
out vec4 outColor;

// One footage sample with a chromatic split that grows toward the edges (uCA > 0 only).
vec3 samp(sampler2D t, vec2 iuv, float ca) {
  if (ca <= 0.0) {
    return texture(t, iuv).rgb;
  }
  vec2 dir = iuv - 0.5;
  float r = texture(t, iuv + dir * ca).r;
  float g = texture(t, iuv).g;
  float b = texture(t, iuv - dir * ca).b;
  return vec3(r, g, b);
}

// Depth of field: a 9-tap disc whose radius is the blur strength.
vec3 sampleDof(sampler2D t, vec2 iuv, float ca) {
  if (uBlurPx < 0.5) {
    return samp(t, iuv, ca);
  }
  vec2 bo = uBlurPx / uRes * uScale;
  vec3 acc = samp(t, iuv, ca);
  for (int i = 0; i < 4; i++) {
    float an = float(i) * 1.5707963;
    vec2 o = vec2(cos(an), sin(an));
    acc += samp(t, iuv + o * bo * 0.5, ca);
    vec2 o2 = vec2(cos(an + 0.7853982), sin(an + 0.7853982));
    acc += samp(t, iuv + o2 * bo, ca);
  }
  return acc / 9.0;
}

void main() {
  vec2 suv = vec2(gl_FragCoord.x / uRes.x, 1.0 - gl_FragCoord.y / uRes.y);
  vec2 iuv = 0.5 + (suv - 0.5) * uScale;
  float aspect = uRes.x / uRes.y;
  vec2 q = (suv - 0.5) * vec2(aspect, 1.0);
  float edge = smoothstep(0.35, 1.05, length(q));
  float ca = uCA * edge * 0.006;

  vec3 col = sampleDof(uA, iuv, ca);
  if (uMix > 0.001) {
    col = mix(col, sampleDof(uB, iuv, ca), uMix);
  }

  // Sun glow: a tight core and a wide halo, warm.
  vec2 sd = (suv - uSun) * vec2(aspect, 1.0);
  float d2 = dot(sd, sd);
  float glow = exp(-d2 * 26.0) * 0.55 + exp(-d2 * 3.2) * 0.14;
  col += vec3(1.0, 0.74, 0.45) * glow;

  // Mist: fbm drifting slowly, brighter toward the sun (forward scattering).
  if (uMist > 0.0) {
    float t = uTime * 0.012;
    float n = fbm(q * vec2(1.7, 2.6) + vec2(t * 1.3, -t * 0.7));
    float m = smoothstep(0.42, 0.8, n);
    float fwd = exp(-d2 * 1.6) * 0.85 + 0.15;
    col += vec3(1.0, 0.82, 0.58) * 0.09 * m * fwd * uMist;
  }

  // Filmic grade with a golden cast.
  col = aces(col * 1.02);
  col = mix(col, col * col * (3.0 - 2.0 * col), 0.3);
  col *= vec3(1.05, 0.99, 0.88);

  // Vignette.
  col *= 1.0 - 0.45 * smoothstep(0.4, 1.1, length((suv - 0.5) * vec2(1.25, 1.0)));

  // Film grain.
  if (uGrain > 0.0) {
    float g = hash(gl_FragCoord.xy + fract(uTime * 7.3) * vec2(131.0, 71.0)) - 0.5;
    col += g * uGrain;
  }

  outColor = vec4(clamp(col, 0.0, 1.0), 1.0);
}
`;

/**
 * The eagle: premultiplied RGBA frames. The grade is the sunrise: about two-thirds the brightness, warmer,
 * with a soft warm rim on the edge that faces the sun (the alpha gradient gives the edge and its outward normal).
 */
export const EAGLE_FRAG = `#version 300 es
precision highp float;
${COMMON}
uniform sampler2D uTex;
uniform vec2 uRes;
uniform vec2 uTexel;
uniform vec2 uLight;
uniform float uBright;
uniform float uRim;
uniform float uGrain;
uniform float uTime;
out vec4 outColor;

void main() {
  vec2 uv = vec2(gl_FragCoord.x / uRes.x, 1.0 - gl_FragCoord.y / uRes.y);
  vec4 c = texture(uTex, uv);
  float a = c.a;
  if (a <= 0.001) {
    outColor = vec4(0.0);
    return;
  }
  vec3 rgb = c.rgb / a;
  // The footage is cut at its own frame edges: fade those out so no hard line shows.
  float feather = smoothstep(0.0, 0.07, uv.x) * smoothstep(0.0, 0.07, 1.0 - uv.x) * smoothstep(1.0, 0.92, uv.y);
  a *= feather;

  // Alpha gradient: g points into the bird, so the outward normal is -g.
  float aR = texture(uTex, uv + vec2(uTexel.x * 3.0, 0.0)).a;
  float aL = texture(uTex, uv - vec2(uTexel.x * 3.0, 0.0)).a;
  float aD = texture(uTex, uv + vec2(0.0, uTexel.y * 3.0)).a;
  float aU = texture(uTex, uv - vec2(0.0, uTexel.y * 3.0)).a;
  vec2 g = vec2(aR - aL, aD - aU);
  float gl = length(g);
  vec2 n = gl > 0.0001 ? -g / gl : vec2(0.0);
  float edge = clamp(gl * 1.6, 0.0, 1.0);
  float facing = clamp(dot(n, uLight) * 0.5 + 0.5, 0.0, 1.0);
  float rim = edge * facing * facing * uRim * a;

  // Sunrise grade: two-thirds of the brightness, warmer; the rim is the only light on the edge.
  vec3 col = rgb * uBright * vec3(1.06, 0.9, 0.72);
  col += vec3(1.0, 0.66, 0.34) * rim * 0.9;
  if (uGrain > 0.0) {
    float gr = hash(gl_FragCoord.xy + fract(uTime * 7.3) * vec2(57.0, 13.0)) - 0.5;
    col += gr * uGrain;
  }
  col = clamp(col, 0.0, 1.0);
  outColor = vec4(col * a, a);
}
`;
