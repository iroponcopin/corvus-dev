import { FRESH } from "@/i18n/fresh";
import { pathOf } from "@/lib/site";
import { langData } from "@/lib/wiki";
import type { Lang } from "@/lib/wiki-types";
import { BRAND_COLOR } from "@/lib/brands";
import { type ReelTeaser, TeaserReel } from "../teasers/TeaserReel";


/** How much reading a character is worth: the scripts that pack a word into one or two characters read slower per character. */
const DENSITY: Partial<Record<Lang, number>> = { ja: 2.2, zh: 2.2, ko: 1.5 };

/** "Cherry V1.2.0 — Celestial Crucible: guns, a Moon boss" → the name, and what it brings. */
function splitHeadline(headline: string): [string, string] {
  const at = headline.indexOf(": ");
  return at > 0 ? [headline.slice(0, at), headline.slice(at + 2)] : [headline, ""];
}

/**
 * Teasers: every advance notice the Coming-next board has published (data/teasers.json, kept by
 * scripts/build_teaser_archive.py), to play again as it was told and to read in full.
 */
export function TeasersPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const t = FRESH[lang].teasers;
  const teasers: ReelTeaser[] = d.teasers.map((x) => {
    const [title, subtitle] = splitHeadline(x.headline);
    return {
      id: x.id,
      brand: x.brand,
      name: x.name,
      icon: x.icon,
      color: BRAND_COLOR[x.brand] ?? "#ff9fc4",
      announced: x.announced,
      retired: x.retired,
      title,
      subtitle,
      target: x.target,
      body: x.body,
      items: x.items,
      pageHref: pathOf(lang, x.href),
      notesHref: `${pathOf(lang, "changelog/")}?model=${encodeURIComponent(x.brand)}`,
    };
  });
  return (
    <section id="ac-teasers">
      <div className="ac-wrap ac-page-head">
        <h1 className="ac-h1">{t.title}</h1>
        <p className="ac-lead">{t.lede}</p>
      </div>
      <TeaserReel teasers={teasers} labels={t} density={DENSITY[lang] ?? 1} arrow={d.dir === "rtl" ? "←" : "→"} />
    </section>
  );
}
