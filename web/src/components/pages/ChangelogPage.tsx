import { langData } from "@/lib/wiki";
import type { Lang } from "@/lib/wiki-types";
import { Changelog } from "../changelog/Changelog";

export function ChangelogPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const c = d.changelog;
  return (
    <section id="ac-changelog">
      <div className="ac-wrap ac-page-head">
        <h1 className="ac-h1">{c.title}</h1>
        <p className="ac-lead">{c.description}</p>
      </div>
      <div className="ac-wrap">
        <Changelog brands={c.brands} labels={c.labels} noteBrands={c.noteBrands} />
      </div>
    </section>
  );
}
