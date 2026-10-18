import type { Fresh } from "@/i18n/fresh";
import { MODEL_NAMES, MODEL_ORDER } from "@/lib/models";

/**
 * The brand line in MODEL_ORDER (the owner's order: Halia, OUKA, Cherry, Tsubomi, then the rest),
 * spelt as the copy spells them in every language.
 */
export const LINEUP: readonly (readonly [id: string, name: string])[] = MODEL_ORDER.map(
  (id) => [id, MODEL_NAMES[id] ?? id] as const,
);

type Lineup = Fresh["lineup"];

function list(names: readonly string[], l: Lineup["list"]): string {
  if (names.length === 2) return `${names[0]}${l.pair}${names[1]}`;
  let s = "";
  for (let i = 0; i < names.length; i++) {
    if (i > 0) s += i === names.length - 1 ? l.last : l.sep;
    s += names[i];
  }
  return s;
}

/** The Korean topic particle after a Latin-script name: 는 after a vowel, 은 after a consonant. */
function topic(name: string): string {
  return /[aeiouy]$/i.test(name) ? "는" : "은";
}

function clause(forms: readonly [string, string], names: readonly string[], l: Lineup["list"]): string {
  return forms[names.length === 1 ? 0 : 1]
    .replace("{0}", list(names, l))
    .replace("{p}", topic(names[names.length - 1] ?? ""));
}

/**
 * The hero's line-up sentence ("OUKA, Cherry and Aureum are out. Noctua is coming. Corvus Store
 * keeps it all up to date."), composed from what the Store says is out and what is coming, so it
 * cannot fall behind a release. Given the facts of the legacy copy, every language's templates
 * give back its translator's sentence exactly.
 */
export function composeLineup(t: Lineup, out: readonly string[], coming: readonly string[]): string {
  const parts: string[] = [];
  if (out.length > 0) parts.push(clause(t.out, out, t.list));
  if (coming.length > 0) parts.push(clause(t.coming, coming, t.list));
  parts.push(t.keeps);
  return parts.join(t.join);
}
