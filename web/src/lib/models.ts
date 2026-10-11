/**
 * The Models menu of the header and the footer, in the owner's order: the id (its icon is
 * icons/<id>.png and its availability the Store's), the name, and its page relative to the
 * language root. Every model has a page of its own.
 */
export const MODELS: readonly (readonly [id: string, name: string, href: string])[] = [
  ["halia", "Halia", "halia/"],
  ["astraea", "ASTRAEA", "astraea/"],
  ["ouka", "OUKA", "ouka/"],
  ["cherry", "Cherry", "cherry/"],
  ["tsubomi", "Tsubomi", "tsubomi/"],
  ["aureum", "Aureum", "aureum/"],
  ["noctua", "Noctua", "noctua/"],
];
