#!/usr/bin/env node
/**
 * After `next build` (output: "export"): turn out/ into the tree GitHub Pages serves.
 *
 *  1. Japanese is the root language: move out/ja/** to out/** (the app routes it as /ja/).
 *  2. Write sitemap.xml exactly as scripts/build_sitemap.py did: one absolute <loc> per page, sorted by URL.
 *  3. Write portal/build.json (provenance: which wiki commit and versions this export shows).
 *  4. Refuse to finish if the export contains anything that is a contract file of the wiki —
 *     the launcher and the Discord bot read those, and the portal must never write them.
 */
import { existsSync, readdirSync, readFileSync, renameSync, rmSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(WEB, "out");
const BASE_URL = "https://iroponcopin.github.io/corvus-dev";
const LANGS = ["ja", "en", "es", "fr", "zh", "ko", "pt-br", "it", "ar", "ru", "id", "de", "tr"];
const SECTIONS = ["", "alpha/", "aureum/", "changelog/", "cherry-controls/", "cherry/", "discord/", "download/",
  "launcher/", "ouka/", "recipes/", "skin/", "teasers/", "announcement/", "astraea/", "tsubomi/", "noctua/", "halia/"];
/** What the launcher and the bot read (README "Releasing"); the export may contain none of it. */
const CONTRACT = ["glimpse_manifest.json", "releases.json", "upcoming.json", "changelog_feed", "downloads", "data",
  "robots.txt", ".nojekyll", "assets", "scripts", "README.md", "web", ".gitignore"];

function fail(msg) {
  console.error(`finalize-export: ${msg}`);
  process.exit(1);
}

if (!existsSync(OUT)) fail("out/ does not exist: run next build first");

// 1. Japanese at the root.
const ja = join(OUT, "ja");
if (!existsSync(ja)) fail("out/ja is missing: the Japanese pages were not exported");
for (const entry of readdirSync(ja)) {
  const from = join(ja, entry);
  const to = join(OUT, entry);
  if (existsSync(to)) {
    if (entry === "index.html" || entry === "index.txt" || !statSync(to).isDirectory()) {
      rmSync(to, { recursive: true, force: true });
    } else {
      fail(`out/${entry} already exists and would be overwritten by out/ja/${entry}`);
    }
  }
  renameSync(from, to);
}
rmSync(ja, { recursive: true, force: true });

// The 404 page: Next writes it as 404.html (and _not-found/); GitHub Pages wants /404.html only.
rmSync(join(OUT, "_not-found"), { recursive: true, force: true });
rmSync(join(OUT, "404"), { recursive: true, force: true });
if (!existsSync(join(OUT, "404.html"))) fail("out/404.html is missing");

// Every page of every language must be there, with its RSC payload for client navigation.
const missing = [];
for (const lang of LANGS) {
  for (const section of SECTIONS) {
    const dir = join(OUT, lang === "ja" ? "" : lang, section);
    for (const f of ["index.html", "index.txt"]) if (!existsSync(join(dir, f))) missing.push(relative(OUT, join(dir, f)));
  }
}
if (missing.length) fail(`missing pages:\n  ${missing.slice(0, 20).join("\n  ")}`);

// 2. sitemap.xml
const urls = [];
for (const lang of LANGS) for (const s of SECTIONS) urls.push(`${BASE_URL}/${lang === "ja" ? "" : `${lang}/`}${s}`);
urls.sort();
writeFileSync(
  join(OUT, "sitemap.xml"),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n` +
    urls.map((u) => `  <url><loc>${u}</loc></url>`).join("\n") +
    `\n</urlset>\n`,
);

// 3. provenance
const wiki = JSON.parse(readFileSync(join(WEB, ".data", "wiki.json"), "utf8"));
const pkg = JSON.parse(readFileSync(join(WEB, "package.json"), "utf8"));
writeFileSync(
  join(OUT, "portal", "build.json"),
  JSON.stringify(
    {
      what: `Corvus portal ${pkg.version}, static export. Made by web/ (npm run build); nothing here is a contract file.`,
      wiki_commit: wiki.build.commit,
      wiki_branch: wiki.build.branch,
      wiki_dirty: wiki.build.dataDirty,
      corvus_store: wiki.versions.launcher,
      ouka: wiki.versions.ouka,
      cherry: wiki.versions.cherry,
      aureum: wiki.versions.aureum,
      astraea: wiki.versions.astraea,
      tsubomi: wiki.versions.tsubomi,
      halia: wiki.versions.halia,
      pages: LANGS.length * SECTIONS.length,
    },
    null,
    1,
  ) + "\n",
);

// 4. contract files must not be in the export
const offending = CONTRACT.filter((c) => existsSync(join(OUT, c)));
if (offending.length) fail(`the export contains contract files: ${offending.join(", ")}`);

// The detector script must be the wiki's own, byte for byte.
const ours = readFileSync(join(OUT, "portal", "lang.js"));
const theirs = readFileSync(join(WEB, "..", "assets", "js", "lang.js"));
if (!ours.equals(theirs)) fail("portal/lang.js differs from assets/js/lang.js");

console.log(`finalize-export: ${LANGS.length * SECTIONS.length} pages, sitemap ${urls.length} URLs, out/ ready`);
