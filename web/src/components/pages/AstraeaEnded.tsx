import { FRESH } from "@/i18n/fresh";
import type { Lang } from "@/lib/wiki-types";

/**
 * ASTRAEA's end-of-service notice (2026-10-16): the same text, in all 13 languages, at the top of its page and in
 * place of its Download entry. A notice, not an erasure: nothing here offers an install.
 */
export function AstraeaEnded({ lang }: { lang: Lang }) {
  const e = FRESH[lang].astraeaEnded;
  return (
    <section className="ac-card ac-section-card ac-ended ac-reveal" aria-labelledby="astraea-ended-h">
      <p className="ac-eyebrow">{e.badge}</p>
      <h2 id="astraea-ended-h" className="ac-h3">
        {e.title}
      </h2>
      <p>{e.lede}</p>
      <p>{e.thanks}</p>
      <h3 className="ac-req-head">{e.nextTitle}</h3>
      <ol className="ac-req">
        {e.next.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ol>
      <h3 className="ac-req-head">{e.backupTitle}</h3>
      <p>{e.backup}</p>
      <p className="ac-small">{e.ouka}</p>
      <p>{e.closing}</p>
    </section>
  );
}
