import type { Dir, Lang } from "./wiki-types";

/**
 * Site constants and URL helpers shared by server and client code (no file system here).
 * The language table mirrors scripts/site_common.py LANGUAGES; `meta.ts` checks at build time
 * that the two agree, so a language added on the wiki side cannot be silently dropped here.
 */

export const BASE_PATH = "/aurora-corvus";
export const BASE_URL = "https://iroponcopin.github.io/aurora-corvus";

export const LANGUAGES: readonly { code: Lang; name: string; dir: Dir; hreflang: string }[] = [
  { code: "ja", name: "日本語", dir: "ltr", hreflang: "ja" },
  { code: "en", name: "English", dir: "ltr", hreflang: "en" },
  { code: "es", name: "Español", dir: "ltr", hreflang: "es" },
  { code: "fr", name: "Français", dir: "ltr", hreflang: "fr" },
  { code: "zh", name: "简体中文", dir: "ltr", hreflang: "zh" },
  { code: "ko", name: "한국어", dir: "ltr", hreflang: "ko" },
  { code: "pt-br", name: "Português (Brasil)", dir: "ltr", hreflang: "pt-BR" },
  { code: "it", name: "Italiano", dir: "ltr", hreflang: "it" },
  { code: "ar", name: "العربية", dir: "rtl", hreflang: "ar" },
  { code: "ru", name: "Русский", dir: "ltr", hreflang: "ru" },
  { code: "id", name: "Bahasa Indonesia", dir: "ltr", hreflang: "id" },
  { code: "de", name: "Deutsch", dir: "ltr", hreflang: "de" },
  { code: "tr", name: "Türkçe", dir: "ltr", hreflang: "tr" },
];

export const LANG_CODES: readonly Lang[] = LANGUAGES.map((l) => l.code);

export function isLang(v: string): v is Lang {
  return (LANG_CODES as readonly string[]).includes(v);
}

export function dirOf(lang: Lang): Dir {
  return lang === "ar" ? "rtl" : "ltr";
}

/** The page sections, as path tails with a trailing slash ("" is the home page). */
export const SECTIONS = [
  "",
  "launcher/",
  "download/",
  "recipes/",
  "changelog/",
  "announcement/",
  "skin/",
  "discord/",
  "ouka/",
  "cherry/",
  "cherry-controls/",
  "aureum/",
  "alpha/",
  "astraea/",
  "tsubomi/",
  "halia/",
  "noctua/",
] as const;
export type Section = (typeof SECTIONS)[number];

/** App-relative path of a section in a language (Next adds the basePath to <Link>). */
export function pathOf(lang: Lang, section: string): string {
  return `/${lang === "ja" ? "" : `${lang}/`}${section}`;
}

/** Absolute URL of a section (canonical, hreflang, Open Graph). */
export function urlOf(lang: Lang, section: string): string {
  return `${BASE_URL}${pathOf(lang, section)}`;
}

/**
 * Content hashes of the portal's own files (scripts/prepare-public.mjs, through next.config.ts).
 * Recipe icons carry none (stable ids); outside a build the table is empty.
 */
const VERSIONS = JSON.parse(process.env.NEXT_PUBLIC_ASSET_VERSIONS ?? "{}") as Record<string, string>;

/**
 * A file under the portal's own assets (`/portal/...`), basePath included, for <img> and fetch.
 * The file's content hash rides in the URL (`?v=`), so a file replaced in place — an icon, a
 * favicon, the share card — gets a new URL, and no cache can go on serving the old one.
 */
export function asset(path: string): string {
  const p = path.replace(/^\/+/, "");
  const v = VERSIONS[p];
  return `${BASE_PATH}/portal/${p}${v === undefined ? "" : `?v=${v}`}`;
}

/** A recipe icon by its stable id (`t62` → /portal/wiki/recipes/t62.png). */
export function recipeIcon(id: string | null): string | null {
  return id === null ? null : asset(`wiki/recipes/${id}.png`);
}

/** A file published by the wiki itself (downloads/, data/): basePath-absolute. */
export function wikiFile(path: string): string {
  return `${BASE_PATH}/${path.replace(/^\/+/, "")}`;
}
