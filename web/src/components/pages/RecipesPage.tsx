import { Formation } from "@/engine/store";
import { FRESH } from "@/i18n/fresh";
import { recipeIcon } from "@/lib/site";
import { langData, wiki } from "@/lib/wiki";
import type { Lang } from "@/lib/wiki-types";
import { RealmAnchor } from "../RealmAnchor";
import { Codex, type CodexData } from "../recipes/Codex";

const GOLD: readonly [number, number, number] = [1, 0.74, 0.36];

export function RecipesPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const shared = wiki().recipes;
  const r = d.recipes;
  const data: CodexData = {
    total: shared.total,
    cats: shared.cats.map((c, i) => ({ ...c, name: r.catNames[i] ?? c.name })),
    allTabIcon: shared.allTabIcon,
    items: Object.fromEntries(
      Object.entries(shared.items).map(([id, it]) => [
        id,
        { name: r.names[id] ?? it.en, ...(r.subs[id] ? { sub: r.subs[id] } : {}), icon: it.icon, kind: it.kind },
      ]),
    ),
    recipes: shared.recipes.map((rec) =>
      rec.howText ? { ...rec, howLine: lang === "ja" ? { text: rec.howText.ja, lang: "ja" as const } : { text: rec.howText.en, lang: "en" as const } } : rec,
    ),
    search: r.search,
    stations: shared.stations,
  };
  const f = FRESH[lang];
  return (
    <RealmAnchor config={{ formation: Formation.Codex, x: 0.8, xNarrow: 0.5, y: 0.45, scale: 0.34, scaleNarrow: 0.3, tint: GOLD }}>
      <div className="ac-wrap ac-page-head">
        <h1 className="ac-h1">{r.title}</h1>
        <p className="ac-lead">{r.intro}</p>
      </div>
      <div className="ac-wrap">
        <Codex data={data} labels={r.labels} fresh={{ synthesise: f.synth.synthesise, replay: f.synth.replay, result: f.synth.result, fusing: f.synth.fusing }} />
        <noscript>
          <ul className="ac-cx-all">
            {shared.recipes.map((rec) => {
              const name = data.items[rec.result]?.name ?? rec.result;
              const icon = recipeIcon(data.items[rec.result]?.icon ?? null);
              return (
                <li key={rec.key}>
                  {icon ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img src={icon} alt="" width={24} height={24} className="ac-pixel" />
                  ) : null}
                  <b>{name}</b>{" "}
                  {rec.grid
                    ? rec.grid
                        .filter((c): c is string => c !== 0)
                        .map((c) => data.items[c]?.name ?? c)
                        .join(" + ")
                    : (rec.fusion ?? []).map((x) => `${data.items[x.id]?.name ?? x.id} ×${x.n}`).join(" + ")}
                </li>
              );
            })}
          </ul>
        </noscript>
      </div>
    </RealmAnchor>
  );
}
