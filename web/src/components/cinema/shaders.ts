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
uniform sampler2D uC;
uniform sampler2D uD;
uniform float uMix2;
uniform sampler2D uE;
uniform sampler2D uF;
uniform float uMix3;
uniform float uDis3;
uniform float uDusk;
uniform float uDis;
uniform float uFog;
uniform float uTeal;
uniform float uSunAmt;
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

// Two footage frames blended by m.
vec3 sampleBlend(sampler2D t1, sampler2D t2, float m, vec2 iuv, float ca) {
  vec3 c = sampleDof(t1, iuv, ca);
  if (m > 0.001) {
    c = mix(c, sampleDof(t2, iuv, ca), m);
  }
  return c;
}

// The dusk grade: lower exposure, cooler, a deep blue in the shadows and on the water.
vec3 col3grade(vec3 c) {
  vec3 cool = c * vec3(0.62, 0.78, 1.14) + vec3(0.0, 0.012, 0.06);
  return cool * 0.74;
}

void main() {
  vec2 suv = vec2(gl_FragCoord.x / uRes.x, 1.0 - gl_FragCoord.y / uRes.y);
  vec2 iuv = 0.5 + (suv - 0.5) * uScale;
  float aspect = uRes.x / uRes.y;
  vec2 q = (suv - 0.5) * vec2(aspect, 1.0);
  float edge = smoothstep(0.35, 1.05, length(q));
  float ca = uCA * edge * 0.006;

  // Act I footage, then Act II footage; uDis cross-dissolves between them, and uDis3 dissolves into Act III.
  vec3 col = vec3(0.0);
  if (uDis < 0.999) {
    col = sampleBlend(uA, uB, uMix, iuv, ca);
  }
  if (uDis > 0.001) {
    col = mix(col, sampleBlend(uC, uD, uMix2, iuv, ca), uDis);
  }
  if (uDis3 > 0.001) {
    vec3 c3 = sampleBlend(uE, uF, uMix3, iuv, ca);
    // Shot one of Act III is graded toward dusk: cooler, darker, deep blue water.
    float dk = uDusk;
    vec3 cool = col3grade(c3);
    c3 = mix(c3, cool, dk);
    col = mix(col, c3, uDis3);
  }

  // Sun glow: a tight core and a wide halo, warm (Act I only).
  vec2 sd = (suv - uSun) * vec2(aspect, 1.0);
  float d2 = dot(sd, sd);
  float glow = exp(-d2 * 26.0) * 0.55 + exp(-d2 * 3.2) * 0.14;
  col += vec3(1.0, 0.74, 0.45) * glow * uSunAmt;

  // Mist: fbm drifting slowly, brighter toward the sun (forward scattering).
  if (uMist > 0.0) {
    float t = uTime * 0.012;
    float n = fbm(q * vec2(1.7, 2.6) + vec2(t * 1.3, -t * 0.7));
    float m = smoothstep(0.42, 0.8, n);
    float fwd = exp(-d2 * 1.6) * 0.85 + 0.15;
    col += vec3(1.0, 0.82, 0.58) * 0.09 * m * fwd * uMist;
  }

  // Cloud: a dense pale mist that drifts over the footage, thinning as the clouds part (Act II).
  if (uFog > 0.001) {
    float t = uTime * 0.02;
    float fm = smoothstep(0.3, 0.75, fbm(q * vec2(1.1, 1.7) + vec2(t, -t * 0.4)));
    col = mix(col, vec3(0.80, 0.85, 0.85), clamp(uFog * (0.45 + 0.55 * fm), 0.0, 0.95));
  }

  // Cool grade for Act II: teal-green shadows, and distance haze toward the top of the frame.
  if (uTeal > 0.001) {
    float lum = dot(col, vec3(0.3, 0.59, 0.11));
    vec3 teal = col * vec3(0.88, 1.03, 1.0) + vec3(0.0, 0.03, 0.025) * (1.0 - lum);
    col = mix(col, teal, uTeal * 0.85);
    col = mix(col, vec3(0.80, 0.85, 0.85), uTeal * 0.22 * (1.0 - suv.y));
  }

  // Filmic grade with a golden cast (Act I), which fades out as Act II cools.
  col = aces(col * 1.02);
  col = mix(col, col * col * (3.0 - 2.0 * col), 0.3);
  col *= mix(vec3(1.0), vec3(1.05, 0.99, 0.88), 1.0 - uTeal);

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
  // Mirrored: the eagle faces left, toward the title.
  uv.x = 1.0 - uv.x;
  vec4 c = texture(uTex, uv);
  float a = c.a;
  if (a <= 0.001) {
    outColor = vec4(0.0);
    return;
  }
  vec3 rgb = c.rgb / a;

  // Alpha gradient: g points into the bird, so the outward normal is -g.
  float aR = texture(uTex, uv + vec2(uTexel.x * 3.0, 0.0)).a;
  float aL = texture(uTex, uv - vec2(uTexel.x * 3.0, 0.0)).a;
  float aD = texture(uTex, uv + vec2(0.0, uTexel.y * 3.0)).a;
  float aU = texture(uTex, uv - vec2(0.0, uTexel.y * 3.0)).a;
  vec2 g = vec2(aR - aL, aD - aU);
  float gl = length(g);
  vec2 n = gl > 0.0001 ? -g / gl : vec2(0.0);
  float edge = clamp(gl * 1.6, 0.0, 1.0);

  // Rim: only the top and back of the head that face the sun, inside the alpha, a quarter of the old strength.
  float sunSide = smoothstep(0.55, 0.95, dot(n, uLight));
  float crown = smoothstep(0.5, 0.15, uv.y);
  float rim = edge * sunSide * crown * uRim * a;

  // Sunrise grade, and light wrap: the lit edge sinks slightly toward the background tone.
  vec3 col = rgb * uBright * vec3(1.06, 0.9, 0.72);
  col *= 1.0 - 0.12 * edge;
  col += vec3(1.0, 0.66, 0.34) * rim * 0.9;
  if (uGrain > 0.0) {
    float gr = hash(gl_FragCoord.xy + fract(uTime * 7.3) * vec2(57.0, 13.0)) - 0.5;
    col += gr * uGrain;
  }
  col = clamp(col, 0.0, 1.0);
  outColor = vec4(col * a, a);
}
`;

/**
 * The crow: a premultiplied RGBA frame placed in a box on the full-stage canvas. The frame's bottom edge is cut
 * at the treetop (kept beyond the viewport). The black is lifted very slightly toward the mist colour, and
 * soft wisps of mist pass in front, at low alpha, now and then.
 */
export const CROW_FRAG = `#version 300 es
precision highp float;
${COMMON}
uniform sampler2D uTex;
uniform vec2 uRes;
uniform vec4 uBox;
uniform float uAlpha;
uniform float uWisp;
uniform float uTime;
uniform float uDusk;
out vec4 outColor;

void main() {
  vec2 fc = vec2(gl_FragCoord.x, uRes.y - gl_FragCoord.y);
  vec4 crow = vec4(0.0);
  vec2 lp = (fc - uBox.xy) / uBox.zw;
  if (uAlpha > 0.001 && lp.x >= 0.0 && lp.x <= 1.0 && lp.y >= 0.0 && lp.y <= 1.0) {
    vec4 c = texture(uTex, lp);
    if (c.a > 0.001) {
      vec3 rgb = c.rgb / c.a;
      rgb = mix(rgb, vec3(0.42, 0.48, 0.47), 0.07);
      // Act III: the bird is graded into the twilight, with a faint purple-blue sheen on the feathers.
      rgb = mix(rgb, rgb * vec3(0.8, 0.86, 1.06) * 0.82 + vec3(0.02, 0.012, 0.05), uDusk);
      rgb += uDusk * vec3(0.05, 0.035, 0.12) * (1.0 - rgb.r);
      crow = vec4(rgb * c.a * uAlpha, c.a * uAlpha);
    }
  }

  float wa = 0.0;
  if (uWisp > 0.001) {
    vec2 suv = fc / uRes;
    vec2 q = vec2(suv.x * uRes.x / uRes.y, suv.y);
    float ev = smoothstep(0.55, 0.85, vnoise(vec2(uTime * 0.05, 3.7)));
    float n = fbm(vec2(q.x * 1.4 - uTime * 0.04, q.y * 3.0 + uTime * 0.01));
    float band = smoothstep(0.45, 0.8, n) * smoothstep(0.2, 0.5, suv.y) * (1.0 - smoothstep(0.85, 1.0, suv.y));
    wa = band * ev * 0.14 * uWisp;
  }
  vec3 wcol = vec3(0.86, 0.9, 0.9);
  // Over-composite the wisp onto the crow (premultiplied).
  vec3 outRgb = wcol * wa + crow.rgb * (1.0 - wa);
  float outA = wa + crow.a * (1.0 - wa);
  outColor = vec4(outRgb, outA);
}
`;
