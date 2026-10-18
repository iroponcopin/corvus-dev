import type { RecipeShared } from "@/lib/wiki-types";

/**
 * The Recipe Tome's data adapter: pure functions over the shared recipe sheet (web/.data/wiki.json through
 * RecipesPage). Server-safe: no window, no document, no three.js. The book, the command bar, the stage and the
 * deep links all read the same index, so they cannot disagree about which recipes exist or where they sit.
 */

export type RecipeRow = RecipeShared["recipes"][number];
export type ItemKind = "flat" | "cube" | "icon" | "none";

export interface TomeItem {
  id: string;
  name: string;
  sub?: string;
  icon: string | null;
  kind: ItemKind;
}

export interface TomeCat {
  index: number;
  /** The model's name as the sheet prints it (localised where the language has one). */
  name: string;
  /** The model's id ("ouka", "cherry", "tsubomi", "halia"): the value `?model=` takes. */
  model: string;
  icon: string | null;
  count: number;
}

export interface TomeStation {
  id: string;
  item: string | null;
  count: number;
}

/** Everything the page needs, prepared on the server for the one client component that draws the book. */
export interface TomeData {
  total: number;
  cats: TomeCat[];
  allTabIcon: string | null;
  items: Record<string, TomeItem>;
  recipes: RecipeRow[];
  search: Record<string, string>;
  stations: TomeStation[];
}

/** Items per index page (the left page of a spread): a 3 × 3 grid of entries. */
export const PAGE_SIZE = 9;

export interface TomeIndex {
  /** Every result item, in the sheet's order. */
  order: string[];
  /** Recipes per result item, in the sheet's order. */
  byResult: Map<string, RecipeRow[]>;
}

export interface TomeFilter {
  /** Chapter (category index), or null for every chapter. */
  cat: number | null;
  /** Station id, or null for every station. */
  station: string | null;
  /** Normalised search text ("" for none). */
  query: string;
}

/** Ingredient as the page and the 3D ritual draw it: a grid slot, or a counted input of a station recipe. */
export interface TomeIngredient {
  id: string;
  name: string;
  icon: string | null;
  kind: ItemKind;
  /** Crafting-grid slot 0..8 (row-major), or -1 for a counted input. */
  slot: number;
  /** How many of it the recipe takes (grid cells are 1). */
  n: number;
  /** Counted inputs may be "any of its kind" (a tag or alternatives). */
  any: boolean;
}

export function normalise(s: string): string {
  return s
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
}

export function buildIndex(data: TomeData): TomeIndex {
  const byResult = new Map<string, RecipeRow[]>();
  for (const r of data.recipes) {
    const list = byResult.get(r.result);
    if (list) list.push(r);
    else byResult.set(r.result, [r]);
  }
  return { order: Array.from(byResult.keys()), byResult };
}

/** The item ids that match a filter, in sheet order: an item is listed when one of its recipes matches. */
export function filterIds(data: TomeData, index: TomeIndex, f: TomeFilter): string[] {
  return index.order.filter((id) =>
    (index.byResult.get(id) ?? []).some(
      (r) =>
        (f.cat === null || r.cat === f.cat) &&
        (f.station === null || r.station === f.station) &&
        (f.query === "" || (data.search[r.key] ?? "").includes(f.query)),
    ),
  );
}

/** Index pages of a list: PAGE_SIZE items each. A spread is one of these pages on the left and its blueprint on the right. */
export function paginate(ids: readonly string[], size: number = PAGE_SIZE): string[][] {
  const pages: string[][] = [];
  for (let i = 0; i < ids.length; i += size) pages.push(ids.slice(i, i + size));
  return pages;
}

/** The page (spread) index that holds an item in a list, or -1. */
export function pageOf(ids: readonly string[], id: string, size: number = PAGE_SIZE): number {
  const at = ids.indexOf(id);
  return at < 0 ? -1 : Math.floor(at / size);
}

/** Which model a chapter belongs to: the id prefix of the items it makes ("ouka:ouka_caster" is OUKA). */
export function modelOfCat(data: TomeData, cat: number): string {
  const first = data.recipes.find((r) => r.cat === cat);
  return first ? (first.result.split(":")[0] ?? "") : "";
}

/** The chapter index a model id names, or null. `?model=halia` and the chapter ribbons use the same ids. */
export function catOfModel(data: TomeData, model: string): number | null {
  const c = data.cats.find((x) => x.model === model);
  return c ? c.index : null;
}

export function itemOf(data: TomeData, id: string): TomeItem | undefined {
  return data.items[id];
}

/** The recipe the tree and the 3D ritual use for an item: the first one that reliably makes it. */
export function sureRecipe(index: TomeIndex, id: string): RecipeRow | undefined {
  return (index.byResult.get(id) ?? []).find(
    (r) => !(r.outputs ?? []).some((o) => o.chance !== undefined || o.nMax !== undefined || (o.id === id && o.every !== undefined)),
  );
}

/** A station recipe has no crafting grid: it names its machine and counted inputs. */
export function isStationRecipe(r: RecipeRow): boolean {
  return r.grid === null;
}

export function stationItemOf(data: TomeData, stationId: string): TomeItem | undefined {
  const st = data.stations.find((s) => s.id === stationId);
  return st?.item ? data.items[st.item] : undefined;
}

/** The inputs of a recipe, as the page lists them and the ritual animates them. */
export function ingredientsOf(data: TomeData, r: RecipeRow): TomeIngredient[] {
  if (r.grid) {
    return r.grid.flatMap((cell, slot) => {
      if (cell === 0) return [];
      const it = data.items[cell];
      return [{ id: cell, name: it?.name ?? cell, icon: it?.icon ?? null, kind: it?.kind ?? "none", slot, n: 1, any: false }];
    });
  }
  return (r.inputs ?? r.fusion ?? []).map((f) => {
    const it = data.items[f.id];
    return {
      id: f.id,
      name: it?.name ?? f.id,
      icon: it?.icon ?? null,
      kind: it?.kind ?? "none",
      slot: -1,
      n: f.n,
      any: "any" in f && f.any === true,
    };
  });
}
