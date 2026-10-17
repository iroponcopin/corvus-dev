#!/usr/bin/env node
/**
 * The export's own gate, run after `npm run build` (and again by `npm run apply` on the tree it
 * produced). It reads web/out/ the way GitHub Pages will serve it, with the wiki's contract files
 * (downloads/, data/, the feeds) taken from this repository, and fails on:
 *
 *  - a page without its <html lang/dir>, <title>, description, canonical URL, 13 hreflang
 *    alternates + x-default, Open Graph title/image, or without its RSC payload (index.txt);
 *  - a local reference that would 404: href/src/srcset and inline style url() in every page,
 *    url() in every stylesheet, asset paths in the JS chunks and chunk paths in the RSC payloads,
 *    same-origin absolute URLs (the download links) included;
 *  - a link to an anchor (#id) that the target page does not contain;
 *  - a SHA-256 printed on a page that is not the SHA-256 of a file that page links to, as the
 *    file is actually served from downloads/ (a release that rebuilt the manifest but not the
 *    pages), or a download link to a file the manifest does not list (the public skin is listed by
 *    data/skin_public.json instead, while the file served is the one it records);
 *  - a 404.html that is missing or that uses a relative reference (it is served at any depth);
 *  - a contract file inside the export.
 */
import { createHash } from "node:crypto";
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { dirname, extname, join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = process.argv[2] ?? join(WEB, "out");
const REPO = join(WEB, "..");
const BASE = "/corvus-dev";
const ORIGIN = "https://iroponcopin.github.io";
const LANGS = ["ja", "en", "es", "fr", "zh", "ko", "pt-br", "it", "ar", "ru", "id", "de", "tr"];
/** Served by this repository, not by the export: the only paths a page may reach outside out/. */
const CONTRACT_ROOTS = ["downloads/", "data/", "changelog_feed/", "glimpse_manifest.json", "releases.json", "upcoming.json", "robots.txt"];
const CONTRACT = ["glimpse_manifest.json", "releases.json", "upcoming.json", "changelog_feed", "downloads", "data", "robots.txt", ".nojekyll"];

const problems = [];
const problem = (where, what) => problems.push(`${where}: ${what}`);

function walk(dir, out = []) {
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    if (statSync(p).isDirectory()) walk(p, out);
    else out.push(p);
  }
  return out;
}

const files = walk(OUT);
const rel = (p) => relative(OUT, p).split(sep).join("/");
const pages = files.filter((f) => f.endsWith(".html"));

/** The file GitHub Pages would serve for a site path (no query, no hash), or null. */
function resolve(sitePath) {
  if (!sitePath.startsWith(`${BASE}/`) && sitePath !== BASE) return { external: true };
  let p = decodeURIComponent(sitePath.slice(BASE.length + 1));
  const inContract = CONTRACT_ROOTS.some((c) => p === c || p.startsWith(c));
  const roots = inContract ? [REPO] : [OUT];
  for (const root of roots) {
    const full = join(root, p);
    if (p === "" || p.endsWith("/")) {
      if (existsSync(join(full, "index.html"))) return { file: join(full, "index.html") };
    } else if (existsSync(full) && statSync(full).isFile()) {
      return { file: full };
    } else if (existsSync(full) && statSync(full).isDirectory() && existsSync(join(full, "index.html"))) {
      return { file: join(full, "index.html") };
    }
  }
  return { file: null };
}

const idsCache = new Map();
function idsOf(file) {
  if (!idsCache.has(file)) {
    const html = readFileSync(file, "utf8");
    idsCache.set(file, new Set(Array.from(html.matchAll(/\sid="([^"]+)"/g), (m) => m[1])));
  }
  return idsCache.get(file);
}

function checkRef(where, raw, fromFile, { allowRelative = true } = {}) {
  let ref = raw.trim().replace(/&amp;/g, "&");
  if (ref === "" || /^(data:|blob:|mailto:|tel:|javascript:)/.test(ref)) return;
  if (ref.startsWith(ORIGIN)) ref = ref.slice(ORIGIN.length);
  else if (/^[a-z]+:\/\//i.test(ref) || ref.startsWith("//")) return;
  const hashAt = ref.indexOf("#");
  const hash = hashAt >= 0 ? ref.slice(hashAt + 1) : "";
  let path = hashAt >= 0 ? ref.slice(0, hashAt) : ref;
  path = path.split("?")[0];
  if (path === "") {
    if (hash && fromFile && !idsOf(fromFile).has(decodeURIComponent(hash))) problem(where, `#${hash} is not on this page`);
    return;
  }
  if (!path.startsWith("/")) {
    if (!allowRelative) {
      problem(where, `relative reference ${raw} (this page is served at any depth)`);
      return;
    }
    path = new URL(path, `https://x${BASE}/${rel(fromFile)}`).pathname;
  }
  const r = resolve(path);
  if (r.external) {
    problem(where, `reference outside ${BASE}/: ${raw}`);
    return;
  }
  if (r.file === null) {
    problem(where, `404: ${raw}`);
    return;
  }
  if (hash && r.file.endsWith(".html") && !idsOf(r.file).has(decodeURIComponent(hash))) problem(where, `${raw}: no id="${hash}" there`);
}

// Pages
let refs = 0;
for (const f of pages) {
  const where = rel(f);
  const html = readFileSync(f, "utf8");
  const is404 = where === "404.html";
  if (!is404) {
    if (!/<html[^>]*\slang="[a-z-]+"[^>]*\sdir="(ltr|rtl)"/.test(html)) problem(where, "no <html lang dir>");
    if (!/<title>[^<]+<\/title>/.test(html)) problem(where, "no <title>");
    if (!/<meta name="description" content="[^"]+"/.test(html)) problem(where, "no description");
    if (!/<link rel="canonical" href="https:\/\/iroponcopin\.github\.io\/corvus-dev\/[^"]*"/.test(html)) problem(where, "no canonical");
    const alternates = Array.from(html.matchAll(/<link rel="alternate" hrefLang="([^"]+)" href="([^"]+)"/gi), (m) => m[1]);
    if (alternates.length !== LANGS.length + 1 || !alternates.includes("x-default")) problem(where, `hreflang alternates: ${alternates.length}`);
    if (!/<meta property="og:title" content="[^"]+"/.test(html)) problem(where, "no og:title");
    if (!/<meta property="og:image" content="https:[^"]+"/.test(html)) problem(where, "no og:image");
    const txt = join(dirname(f), "index.txt");
    if (f.endsWith(`${sep}index.html`) && !existsSync(txt)) problem(where, "no RSC payload (index.txt)");
  }
  for (const m of html.matchAll(/\s(?:href|src)="([^"]*)"/g)) {
    refs += 1;
    checkRef(where, m[1], f, { allowRelative: !is404 });
  }
  for (const m of html.matchAll(/\ssrcSet="([^"]*)"/gi)) {
    for (const part of m[1].split(",")) {
      refs += 1;
      checkRef(where, part.trim().split(/\s+/)[0] ?? "", f, { allowRelative: !is404 });
    }
  }
  for (const m of html.matchAll(/url\((?:&quot;|["'])?([^)"'&]+)(?:&quot;|["'])?\)/g)) {
    refs += 1;
    checkRef(where, m[1], f, { allowRelative: !is404 });
  }
}

// Stylesheets
for (const f of files.filter((x) => extname(x) === ".css")) {
  const css = readFileSync(f, "utf8");
  for (const m of css.matchAll(/url\(\s*["']?([^)"']+)["']?\s*\)/g)) {
    if (m[1].startsWith("data:")) continue;
    refs += 1;
    checkRef(rel(f), m[1], f);
  }
}

// Asset paths written into the JS chunks (images, audio, the detector, feeds the pages fetch).
for (const f of files.filter((x) => extname(x) === ".js")) {
  const js = readFileSync(f, "utf8");
  for (const m of js.matchAll(/["'`](\/corvus-dev\/(?:portal|downloads|data)\/[^"'`$\s]+?)["'`]/g)) {
    refs += 1;
    checkRef(rel(f), m[1], null);
  }
}

// Chunk paths in the RSC payloads (client-side navigation loads them).
const seenChunks = new Set();
for (const f of files.filter((x) => x.endsWith("index.txt"))) {
  const txt = readFileSync(f, "utf8");
  for (const m of txt.matchAll(/"(\/_next\/static\/[^"]+|static\/(?:chunks|css|media)\/[^"]+)"/g)) {
    const p = m[1].startsWith("/") ? m[1] : `/_next/${m[1]}`;
    if (seenChunks.has(p)) continue;
    seenChunks.add(p);
    refs += 1;
    checkRef(rel(f), `${BASE}${p}`, null);
  }
}

// Every printed SHA-256 is the hash of a file the page links to, as served; every download is in the manifest.
const manifest = JSON.parse(readFileSync(join(REPO, "glimpse_manifest.json"), "utf8"));
const listed = new Set();
(function collect(o) {
  if (o === null || typeof o !== "object") return;
  if (typeof o.download_url === "string") listed.add(o.download_url.replace(ORIGIN, ""));
  for (const v of Object.values(o)) collect(v);
})(manifest);
const hashes = new Map();
function servedHash(sitePath) {
  if (!hashes.has(sitePath)) {
    const r = resolve(sitePath);
    hashes.set(sitePath, r.file ? createHash("sha256").update(readFileSync(r.file)).digest("hex") : null);
  }
  return hashes.get(sitePath);
}
// The public skin is the one download outside the manifest: data/skin_public.json lists it, and only
// while the file as served is the one that record describes.
if (existsSync(join(REPO, "data", "skin_public.json"))) {
  const pub = JSON.parse(readFileSync(join(REPO, "data", "skin_public.json"), "utf8"));
  const sitePath = `${BASE}/${pub.file}`;
  if (servedHash(sitePath) === pub.sha256) listed.add(sitePath);
  else problem("data/skin_public.json", `${pub.file} as served is not the file this record describes`);
}
let printed = 0;
for (const f of pages) {
  const html = readFileSync(f, "utf8");
  const links = Array.from(html.matchAll(/\shref="((?:https:\/\/iroponcopin\.github\.io)?\/corvus-dev\/downloads\/[^"#?]+)"/g), (m) =>
    m[1].replace(ORIGIN, "").replace(/&amp;/g, "&"),
  );
  const served = new Set();
  for (const l of links) {
    if (!listed.has(l)) problem(rel(f), `download not in glimpse_manifest.json: ${l}`);
    const h = servedHash(l);
    if (h) served.add(h);
  }
  for (const m of html.matchAll(/class="ac-hash">([0-9a-f]{64})</g)) {
    printed += 1;
    if (!served.has(m[1])) problem(rel(f), `SHA-256 ${m[1].slice(0, 12)}… is not the hash of any file this page links to`);
  }
}

// "Model", never "brand" (owner, 2026-10-04: 「ライブサイトからブランドという単語を全て削除 モデルに置き換えてください」):
// no page shows the word in any of its 13 languages — not in its text, its titles and descriptions, its alt and
// aria labels, nor in the client data that renders the rest. Kept, because they do not mean "brand": the
// trademark line ("Minecraft is a trademark of Mojang Studios"), the Discord glosses' verb "mark", and
// Spanish "you mark the route". Class names, data-* attributes, file paths and code identifiers are not text.
const BRAND_WORD = /\bbrand(?:s|'s|ed)?\b|ブランド|品牌|브랜드|бренд|\bmarcas?\b|\bmarchi[oa]?\b|\bmarques?\b|\bmerek\b|\bmarken?\b|\bmarka\p{L}*|علامة|علامات|العلامة|ماركة/giu;
const NOT_BRAND = [/Mojang/u, /\b(?:Marca|Marque) (?:un|una|um|une) /u, /يضع علامة على/u, /marcas la ruta/u];
const ENTITIES = { amp: "&", quot: '"', apos: "'", lt: "<", gt: ">", nbsp: " " };
const decode = (t) =>
  t.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (m, e) =>
    e[0] === "#" ? String.fromCodePoint(e[1] === "x" || e[1] === "X" ? parseInt(e.slice(2), 16) : Number(e.slice(1))) : ENTITIES[e] ?? m,
  );
function brandWords(where, text) {
  for (const m of text.matchAll(BRAND_WORD)) {
    // A file path is an identifier, not a word: changelog_feed/brands.json is the feed the launcher and the bot read.
    if (text[m.index - 1] === "/") continue;
    const around = text.slice(Math.max(0, m.index - 90), m.index + 90);
    if (NOT_BRAND.some((r) => r.test(around))) continue;
    problem(where, `shows "${m[0]}" (say "model"): …${around.replace(/\s+/g, " ").trim()}…`);
  }
}
let brandChecked = 0;
for (const f of pages) {
  const html = readFileSync(f, "utf8").replace(/<script\b[\s\S]*?<\/script>/g, " ").replace(/<style\b[\s\S]*?<\/style>/g, " ");
  const attrs = Array.from(html.matchAll(/\s(?:alt|title|aria-label|placeholder|content)="([^"]*)"/g), (m) => m[1]);
  brandWords(rel(f), decode(`${html.replace(/<[^>]+>/g, " ")}\n${attrs.join("\n")}`));
  brandChecked += 1;
  // The client data: every string literal that reads as prose (identifiers, class names and paths are not text).
  const payload = join(dirname(f), "index.txt");
  if (existsSync(payload)) {
    for (const m of readFileSync(payload, "utf8").matchAll(/"((?:[^"\\]|\\.)*)"/g)) {
      let str;
      try {
        str = JSON.parse(`"${m[1]}"`);
      } catch {
        continue;
      }
      if (/^[\w$.\/:#?=&%@+-]*$/.test(str)) continue;
      if (/^[\w-]+(?: [\w-]+)*$/.test(str) && /(?:^| )ac-/.test(str)) continue; // a className list
      brandWords(`${rel(payload)} (client data)`, str);
    }
  }
}

// 404 and contract files
if (!existsSync(join(OUT, "404.html"))) problem("404.html", "missing");
for (const c of CONTRACT) if (existsSync(join(OUT, c))) problem(c, "a contract file is inside the export");

const unique = Array.from(new Set(problems));
if (unique.length > 0) {
  console.error(`check-export: ${unique.length} problem(s)`);
  const shown = Number(process.env.CHECK_EXPORT_SHOW ?? 80);
  for (const p of unique.slice(0, shown)) console.error(`  ${p}`);
  if (unique.length > shown) console.error(`  … and ${unique.length - shown} more (CHECK_EXPORT_SHOW=n shows more)`);
  process.exit(1);
}
console.log(
  `check-export: ${pages.length} pages, ${refs} references, ${seenChunks.size} chunk paths: all resolve; ` +
    `${printed} printed SHA-256 match the files served; no contract file in the export; ` +
    `no page says "brand" (${brandChecked} pages and their client data, 13 languages)`,
);
