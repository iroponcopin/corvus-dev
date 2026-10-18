/**
 * The one order every model list follows (the Models menu, the lineup, the Tome's chapters, the launcher ring):
 * the owner's order, Halia, OUKA, Cherry, Tsubomi, then the rest. A model not listed sorts last.
 */
export const MODEL_ORDER: readonly string[] = ["halia", "ouka", "cherry", "tsubomi", "noctua", "aureum", "astraea"];

/** A model's place in MODEL_ORDER (unlisted models come after every listed one). */
export function modelRank(id: string): number {
  const i = MODEL_ORDER.indexOf(id);
  return i < 0 ? MODEL_ORDER.length : i;
}

/**
 * The Models menu of the header and the footer, in the owner's order: the id (its icon is
 * icons/<id>.png and its availability the Store's), the name, and its page relative to the
 * language root. Every model has a page of its own.
 */
export const MODELS: readonly (readonly [id: string, name: string, href: string])[] = [
  ["halia", "Halia", "halia/"],
  ["ouka", "OUKA", "ouka/"],
  ["cherry", "Cherry", "cherry/"],
  ["tsubomi", "Tsubomi", "tsubomi/"],
  ["noctua", "Noctua", "noctua/"],
  ["aureum", "Aureum", "aureum/"],
  // ASTRAEA's service ended on 2026-10-16: it stays in the menu, last, with its service-ended label.
  ["astraea", "ASTRAEA", "astraea/"],
];
