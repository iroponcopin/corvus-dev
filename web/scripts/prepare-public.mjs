#!/usr/bin/env node
/**
 * Lays out web/public/portal/ before a build or a dev server: the portal's own brand art
 * (web/brand/, committed here because it has no other source) and byte copies of the wiki's
 * shared assets the pages use (favicons, OG image, recipe icons, the OUKA theme, the Sparxie
 * preview, the language detector, the Act I footage of the home page). public/ is generated and git-ignored; the wiki's own files
 * stay the only originals.
 *
 * It also writes the content hash of every file it lays out (web/.data/asset-versions.json, the
 * recipe icons aside): next.config.ts hands the table to asset(), which puts a file's hash in its
 * URL, so a changed file gets a new URL and no cache — browser, CDN, link preview — can go on
 * showing the old one. A favicon or an icon replaced in place keeps no stale copy anywhere.
 */
import { createHash } from "node:crypto";
import { cpSync, existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const WIKI = process.env.WIKI_DIR ?? join(WEB, "..");
const OUT = join(WEB, "public", "portal");

const copies = [
  [join(WEB, "brand", "logo.png"), "logo.png"],
  [join(WEB, "brand", "icons"), "icons"],
  [join(WEB, "brand", "art"), "art"],
  [join(WIKI, "assets", "js", "lang.js"), "lang.js"],
  [join(WIKI, "assets", "img", "brand", "favicon.ico"), "wiki/corvus/favicon.ico"],
  [join(WIKI, "assets", "img", "brand", "favicon-16.png"), "wiki/corvus/favicon-16.png"],
  [join(WIKI, "assets", "img", "brand", "favicon-32.png"), "wiki/corvus/favicon-32.png"],
  [join(WIKI, "assets", "img", "brand", "apple-touch-icon.png"), "wiki/corvus/apple-touch-icon.png"],
  [join(WIKI, "assets", "img", "brand", "og-image.png"), "wiki/corvus/og-image.png"],
  [join(WIKI, "assets", "audio", "ouka", "silver-and-petals.m4a"), "wiki/audio/silver-and-petals.m4a"],
  [join(WIKI, "assets", "audio", "ouka", "silver-and-petals.mp3"), "wiki/audio/silver-and-petals.mp3"],
  [join(WIKI, "assets", "img", "recipes"), "wiki/recipes"],
  [join(WIKI, "assets", "video", "announcement"), "wiki/announcement"],
  [join(WIKI, "assets", "cinema", "act1"), "cinema/act1"],
  [join(WIKI, "assets", "cinema", "act2"), "cinema/act2"],
  [join(WIKI, "assets", "cinema", "act3"), "cinema/act3"],
  [join(WIKI, "assets", "img", "sparxie-front.png"), "wiki/skin/sparxie-front.png"],
  [join(WIKI, "assets", "img", "sparxie-model.png"), "wiki/skin/sparxie-model.png"],
  [join(WEB, "src", "app", "fonts", "OFL-Syne.txt"), "fonts/OFL-Syne.txt"],
];

rmSync(OUT, { recursive: true, force: true });
for (const [from, to] of copies) {
  if (!existsSync(from)) {
    console.error(`prepare-public: missing ${from}`);
    process.exit(1);
  }
  const dest = join(OUT, to);
  mkdirSync(dirname(dest), { recursive: true });
  cpSync(from, dest, { recursive: true });
}

// The Cmd/Ctrl+K palette's index, one file per language (fetched on first open, never inlined in a page):
// the seven models, the changelog entries of the live models, and the recipe results. Built from the wiki's
// data (web/.data/wiki.json, written by extract_wiki.py just before this script runs).
const LIVE_MODELS = ["halia", "ouka", "cherry", "tsubomi", "noctua", "aureum"];
const MODEL_PAGES = [["halia", "halia/"], ["ouka", "ouka/"], ["cherry", "cherry/"], ["tsubomi", "tsubomi/"], ["noctua", "noctua/"], ["aureum", "aureum/"], ["astraea", "astraea/"]];
const wikiData = JSON.parse(readFileSync(join(WEB, ".data", "wiki.json"), "utf8"));
const LANG_CODES = Object.keys(wikiData.langs);
mkdirSync(join(OUT, "search"), { recursive: true });
for (const lang of LANG_CODES) {
  const d = wikiData.langs[lang];
  const names = d.recipes.names;
  const models = MODEL_PAGES.map(([id, href]) => ({ id, name: d.products[id]?.name ?? id, href, archived: d.products[id]?.availability === "archived" }));
  const changelog = [];
  for (const b of d.changelog.brands) {
    if (!LIVE_MODELS.includes(b.id)) continue;
    for (const r of b.releases) changelog.push({ id: r.id, model: b.id, title: r.title, version: r.version, date: r.date, href: `changelog/?model=${b.id}#cl-p-${r.id}` });
  }
  const results = [...new Set(wikiData.recipes.recipes.map((r) => r.result))];
  const recipes = results.map((id) => ({ id, name: names[id] ?? wikiData.recipes.items[id]?.en ?? id, href: `recipes/#item=${encodeURIComponent(id)}` }));
  writeFileSync(join(OUT, "search", `${lang}.json`), JSON.stringify({ models, changelog, recipes }));
}

// Recipe icons are named by stable ids and are 219 of them: they keep plain URLs.
const versions = {};
(function walk(dir, rel) {
  for (const e of readdirSync(dir, { withFileTypes: true })) {
    const r = rel === "" ? e.name : `${rel}/${e.name}`;
    if (e.isDirectory()) {
      if (r !== "wiki/recipes") walk(join(dir, e.name), r);
    } else {
      versions[r] = createHash("sha256").update(readFileSync(join(dir, e.name))).digest("hex").slice(0, 10);
    }
  }
})(OUT, "");
mkdirSync(join(WEB, ".data"), { recursive: true });
writeFileSync(join(WEB, ".data", "asset-versions.json"), `${JSON.stringify(versions, null, 1)}\n`);
console.log(`prepare-public: ${copies.length} entries -> public/portal/, ${Object.keys(versions).length} content hashes`);
