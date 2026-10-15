/**
 * The Models menu of the header and the footer, in the owner's order: the id (its icon is
 * icons/<id>.png and its availability the Store's), the name, and its page relative to the
 * language root. Every model has a page of its own.
 */
export const MODELS: readonly (readonly [id: string, name: string, href: string])[] = [
  ["halia", "Halia", "halia/"],
  ["ouka", "OUKA", "ouka/"],
  ["astraea", "ASTRAEA", "astraea/"],
  ["cherry", "Cherry", "cherry/"],
  ["tsubomi", "Tsubomi", "tsubomi/"],
  ["noctua", "Noctua", "noctua/"],
  ["aureum", "Aureum", "aureum/"],
];
