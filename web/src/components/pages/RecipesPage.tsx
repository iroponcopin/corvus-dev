import { FRESH } from "@/i18n/fresh";
import { recipeIcon } from "@/lib/site";
import { langData, recipeModelList, wiki } from "@/lib/wiki";
import type { Lang } from "@/lib/wiki-types";
import { RecipeBookScene } from "../recipes/RecipeBookScene";
import { modelOfCat, type TomeData } from "../recipes/tome-data";

/**
 * The recipes page: the Recipe Tome (the book and the crafting pedestal). The server prepares the shared sheet for
 * the language (names, search text, chapter names), and the one client component draws it. The static list in the
 * noscript block keeps every recipe readable without JavaScript.
 */
export function RecipesPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const shared = wiki().recipes;
  const r = d.recipes;
  const data: TomeData = {
    total: shared.total,
    cats: shared.cats.map((c, i) => ({
      index: c.index,
      name: r.catNames[i] ?? c.name,
      model: modelOfCat(shared, i),
      icon: c.icon,
      count: c.count,
    })),
    allTabIcon: shared.allTabIcon,
    items: Object.fromEntries(
      Object.entries(shared.items).map(([id, it]) => [
        id,
        { id, name: r.names[id] ?? it.en, ...(r.subs[id] ? { sub: r.subs[id] } : {}), icon: it.icon, kind: it.kind },
      ]),
    ),
    recipes: shared.recipes.map((rec) =>
      rec.howText ? { ...rec, howLine: lang === "ja" ? { text: rec.howText.ja, lang: "ja" as const } : { text: rec.howText.en, lang: "en" as const } } : rec,
    ),
    search: r.search,
    stations: shared.stations,
  };
  const f = FRESH[lang];
  // One unit everywhere: the number of ITEMS (distinct results), the same count the book and the bar show.
  const itemCount = new Set(shared.recipes.map((rec) => rec.result)).size;
  return (
    <section>
      <div className="ac-wrap ac-page-head">
        <h1 className="ac-h1 tome-page-title">{r.title}</h1>
        <p className="ac-lead">{f.tome.intro.replace("{count}", String(itemCount)).replace("{models}", recipeModelList(lang))}</p>
      </div>
      <div className="ac-wrap">
        <RecipeBookScene data={data} labels={r.labels} t={f.tome} dir={d.dir} />
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
    </section>
  );
}
