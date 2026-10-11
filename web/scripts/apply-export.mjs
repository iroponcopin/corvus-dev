#!/usr/bin/env node
/**
 * Lays web/out/ over this repository's root, which GitHub Pages serves — README "Releasing" step 5,
 * done from here: the previous export's hashed chunks and portal assets go first (`_next/`,
 * `portal/`), then the export is copied over the tree without deleting anything else, and then
 * the diff filter runs: against HEAD, only pages (index.html / index.txt), 404.html,
 * sitemap.xml, _next/** and portal/** may differ, and no contract file may. Anything else and
 * the script stops with the list (the working tree is left as it is, for inspection).
 *
 * The export is checked first (scripts/check-export.mjs), so a broken one is never laid over
 * the live tree.
 */
import { execFileSync } from "node:child_process";
import { cpSync, existsSync, readdirSync, rmSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const WEB = join(dirname(fileURLToPath(import.meta.url)), "..");
const OUT = join(WEB, "out");
const REPO = join(WEB, "..");
const LANGS = ["en", "es", "fr", "zh", "ko", "pt-br", "it", "ar", "ru", "id", "de", "tr"];
const SECTIONS = ["alpha", "aureum", "changelog", "cherry-controls", "cherry", "discord", "download", "launcher", "ouka", "recipes", "skin", "teasers", "announcement", "astraea", "tsubomi", "noctua", "halia"];
const CONTRACT = [/^glimpse_manifest\.json$/, /^releases\.json$/, /^upcoming\.json$/, /^changelog_feed\//, /^downloads\//, /^data\//, /^robots\.txt$/, /^\.nojekyll$/];

function fail(msg) {
  console.error(`apply-export: ${msg}`);
  process.exit(1);
}

function git(...args) {
  return execFileSync("git", ["-C", REPO, ...args], { encoding: "utf8", maxBuffer: 64 * 1024 * 1024 });
}

/** A path the export is allowed to change. */
function allowed(path) {
  if (["404.html", "sitemap.xml", "index.html", "index.txt"].includes(path)) return true;
  if (path.startsWith("_next/") || path.startsWith("portal/")) return true;
  const parts = path.split("/");
  const file = parts[parts.length - 1];
  if (file !== "index.html" && file !== "index.txt") return false;
  const dirs = parts.slice(0, -1);
  if (dirs.length === 1) return LANGS.includes(dirs[0]) || SECTIONS.includes(dirs[0]);
  if (dirs.length === 2) return LANGS.includes(dirs[0]) && SECTIONS.includes(dirs[1]);
  return false;
}

if (!existsSync(join(OUT, "portal", "build.json"))) fail("web/out/ is not a finished export: run `npm run build` first");
try {
  execFileSync(process.execPath, [join(WEB, "scripts", "check-export.mjs")], { stdio: "inherit" });
} catch {
  fail("the export did not pass check-export; nothing was changed");
}

// The previous export's chunks and assets are replaced wholesale (their names are content hashes).
rmSync(join(REPO, "_next"), { recursive: true, force: true });
rmSync(join(REPO, "portal"), { recursive: true, force: true });
for (const entry of readdirSync(OUT)) cpSync(join(OUT, entry), join(REPO, entry), { recursive: true, force: true });

// The diff filter: what changed against HEAD, untracked files included, the source tree aside.
const changed = git("status", "--porcelain", "-uall", "--no-renames")
  .split("\n")
  .filter(Boolean)
  .map((line) => line.slice(3))
  .filter((p) => !p.startsWith("web/") && p !== "README.md");
const contract = changed.filter((p) => CONTRACT.some((re) => re.test(p)));
const foreign = changed.filter((p) => !allowed(p));
if (contract.length > 0) fail(`contract files changed (they must never be):\n  ${contract.join("\n  ")}`);
if (foreign.length > 0) fail(`paths outside what an export may change:\n  ${foreign.slice(0, 40).join("\n  ")}`);

console.log(`apply-export: ${changed.length} paths changed, all of them pages, 404.html, sitemap.xml, _next/ or portal/; contract files untouched`);
