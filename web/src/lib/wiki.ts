import { readFileSync } from "node:fs";
import { join } from "node:path";
import { FRESH } from "@/i18n/fresh";
import { composeLineup, LINEUP } from "./lineup";
import type { Lang, LangData, Wiki } from "./wiki-types";

/**
 * Build-time access to the wiki's data (web/.data/wiki.json, written by scripts/extract_wiki.py).
 * Server components only: this reads the file system, so it never reaches the browser.
 */

let cache: Wiki | null = null;

export function wiki(): Wiki {
  if (cache === null) {
    const path = join(process.cwd(), ".data", "wiki.json");
    let raw: string;
    try {
      raw = readFileSync(path, "utf8");
    } catch {
      throw new Error(`${path} is missing: run "npm run extract" (python3 -B scripts/extract_wiki.py) first`);
    }
    const parsed = JSON.parse(raw) as Wiki;
    if (!parsed.schema.startsWith("corvus.wiki/")) throw new Error(`unexpected wiki schema ${parsed.schema}`);
    cache = parsed;
  }
  return cache;
}

export function langData(lang: Lang): LangData {
  const d = wiki().langs[lang];
  if (d === undefined) throw new Error(`no data for language ${lang}`);
  return d;
}

/** The hero's line-up sentence (and the home page's description), from the Store's availability. */
export function lineupFor(lang: Lang): string {
  const p = langData(lang).products;
  const out: string[] = [];
  const coming: string[] = [];
  for (const [id, name] of LINEUP) {
    const a = p[id]?.availability;
    if (a === "available") out.push(name);
    else if (a === "soon") coming.push(name);
  }
  return composeLineup(FRESH[lang].lineup, out, coming);
}
