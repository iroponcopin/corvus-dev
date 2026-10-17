import type { Lang } from "@/lib/wiki-types";

const RTL_SCRIPT = /[֐-ࣿיִ-﷿ﹰ-﻿]/;
const LTR_SCRIPT = /[A-Za-zÀ-ɏͰ-ϿЀ-ӿ]/;

/** Right-to-left text as staggered units: one per word, a run of Latin words kept as one unit. */
function rtlUnits(words: string[]): { text: string; ltr: boolean }[] {
  const units: { text: string; ltr: boolean }[] = [];
  let run: string[] = [];
  let gap = "";
  const flush = (): void => {
    if (run.length > 0) units.push({ text: run.join(""), ltr: true });
    if (gap !== "") units.push({ text: " ", ltr: false });
    run = [];
    gap = "";
  };
  for (const w of words) {
    if (/^\s+$/.test(w)) {
      if (run.length > 0) gap += w;
      else units.push({ text: " ", ltr: false });
      continue;
    }
    if (!RTL_SCRIPT.test(w) && LTR_SCRIPT.test(w)) {
      if (run.length > 0 && gap !== "") run.push(gap);
      gap = "";
      run.push(w);
      continue;
    }
    flush();
    units.push({ text: w, ltr: false });
  }
  flush();
  return units;
}

/**
 * Text that arrives one grapheme at a time (CSS only, no JavaScript). Words stay unbreakable
 * boxes so lines still wrap at spaces. Right-to-left text is staggered by word instead of by
 * letter, since splitting a cursive script into separate boxes would break its letter joins,
 * and a run of Latin words inside it travels as one left-to-right box; a line with no
 * right-to-left letters at all is laid out left to right even on an Arabic page, so the order
 * stays the one the reader expects ("Corvus." never turns into ".Corvus Glow").
 * Screen readers get the sentence once, whole.
 */
export function Stagger({ text, lang, offset = 0, className }: { text: string; lang: Lang; offset?: number; className?: string }) {
  const words = Array.from(new Intl.Segmenter(lang, { granularity: "word" }).segment(text), (s) => s.segment);
  const graphemes = new Intl.Segmenter(lang, { granularity: "grapheme" });
  const rtl = RTL_SCRIPT.test(text);
  let i = offset;
  return (
    <span className={`ac-stagger ${className ?? ""}`} dir={!rtl && lang === "ar" ? "ltr" : undefined}>
      <span className="sr-only">{text}</span>
      <span aria-hidden="true">
        {rtl
          ? rtlUnits(words).map((u, ui) => {
              if (u.text === " ") return " ";
              const n = i++;
              return (
                <span key={ui} className="ac-stagger-unit" dir={u.ltr ? "ltr" : undefined} style={{ ["--ac-i" as string]: n }}>
                  {u.text}
                </span>
              );
            })
          : words.map((w, wi) => {
              if (/^\s+$/.test(w)) return " ";
              return (
                <span key={wi} className="ac-stagger-word">
                  {Array.from(graphemes.segment(w), (g, gi) => {
                    const n = i++;
                    return (
                      <span key={gi} className="ac-stagger-unit" style={{ ["--ac-i" as string]: n }}>
                        {g.segment}
                      </span>
                    );
                  })}
                </span>
              );
            })}
      </span>
    </span>
  );
}
