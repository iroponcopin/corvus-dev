"use client";

import type { Fresh } from "@/i18n/fresh";
import { recipeIcon } from "@/lib/site";
import type { RecipeLabels } from "@/lib/wiki-types";
import {
  ingredientsOf,
  isStationRecipe,
  itemOf,
  type RecipeRow,
  sureRecipe,
  stationItemOf,
  type TomeData,
  type TomeIndex,
  type TomeIngredient,
} from "./tome-data";

/** The Tome's own copy (fresh.ts, `tome`), passed down so the pages stay free of i18n lookups. */
export type TomeLabels = Fresh["tome"];

/** Fills `{0}` and `{1}` in a template. */
export function fill(t: string, v: string, w = ""): string {
  return t.replace("{0}", v).replace("{1}", w);
}

/** A percentage as a player reads it: 25, 2.5, 0.25. */
function pct(v: number): string {
  return String(Number(v.toPrecision(3)));
}

/** One line of a list: picture, name, count, and an optional note. */
export function ItemLine({ data, id, n, note }: { data: TomeData; id: string; n: string; note?: string }) {
  const it = itemOf(data, id);
  const icon = recipeIcon(it?.icon ?? null);
  return (
    <li className="tome-line">
      {icon ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={icon} alt="" width={24} height={24} className="ac-pixel" />
      ) : (
        <span className="ac-noicon" aria-hidden="true">
          ?
        </span>
      )}
      <span dir="auto">{it?.name ?? id}</span>
      <small className="ac-ltr">{n}</small>
      {note ? <small className="ac-small">{note}</small> : null}
    </li>
  );
}

/** Time, water, experience, and the bore's share of a dimension's veins. */
export function MachineFacts({ facts, labels }: { facts: NonNullable<RecipeRow["facts"]>; labels: RecipeLabels["machine"] }) {
  const parts: string[] = [];
  if (facts.dimension && facts.share !== undefined) parts.push(fill(labels.vein, labels[facts.dimension], pct(facts.share)));
  if (facts.time) parts.push(fill(labels.time, pct(facts.time / 20)));
  if (facts.water) parts.push(fill(labels.water, String(facts.water)));
  if (facts.xp) parts.push(fill(labels.xp, pct(facts.xp)));
  return parts.length ? <p className="ac-small tome-facts">{parts.join(" · ")}</p> : null;
}

/** The index page (the left page of a spread): a 3 × 3 list of real buttons, one per item. */
export function IndexPage({
  ids,
  data,
  selected,
  onPick,
  chapter,
  count,
  empty,
  eyebrow,
  id,
}: {
  ids: string[];
  data: TomeData;
  selected: string | null;
  onPick: (id: string) => void;
  chapter: string;
  count: string;
  empty: string;
  eyebrow: string;
  id: string;
}) {
  return (
    <div className="tome-page-body" data-page={id}>
      <header className="tome-page-head">
        <span className="ac-eyebrow">{eyebrow}</span>
        <h2 className="tome-chapter" dir="auto">
          {chapter}
        </h2>
        <span className="ac-small">{count}</span>
      </header>
      {ids.length === 0 ? <p className="ac-codex-empty">{empty}</p> : null}
      <ul className="tome-index" aria-label={chapter}>
        {ids.map((iid) => {
          const it = itemOf(data, iid);
          const icon = recipeIcon(it?.icon ?? null);
          return (
            <li key={iid}>
              <button type="button" className="tome-card" aria-pressed={iid === selected} onClick={() => onPick(iid)}>
                {icon ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={icon} alt="" width={36} height={36} className="ac-pixel" />
                ) : (
                  <span className="ac-noicon" aria-hidden="true">
                    ?
                  </span>
                )}
                <span dir="auto">{it?.name ?? iid}</span>
              </button>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/** The 3 × 3 crafting grid as a table reads it: left to right even in Arabic, the result beside it. */
function CraftGrid({ data, recipe, resultName }: { data: TomeData; recipe: RecipeRow; resultName: string }) {
  const resultIcon = recipeIcon(itemOf(data, recipe.result)?.icon ?? null);
  return (
    <div className="ac-craft tome-craft" dir="ltr">
      <div className="ac-craft-grid">
        {(recipe.grid ?? []).map((cell, i) => {
          const it = cell === 0 ? undefined : itemOf(data, cell);
          const icon = recipeIcon(it?.icon ?? null);
          return (
            <span key={i} className="ac-slot" title={it?.name}>
              {cell === 0 ? null : icon ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={icon} alt={it?.name ?? ""} width={32} height={32} className="ac-pixel" />
              ) : (
                <span className="ac-noicon" aria-hidden="true">
                  ?
                </span>
              )}
            </span>
          );
        })}
      </div>
      <span className="ac-craft-arrow" aria-hidden="true">
        →
      </span>
      <span className="ac-slot ac-slot--result" title={resultName}>
        {resultIcon ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={resultIcon} alt={resultName} width={32} height={32} className="ac-pixel" />
        ) : (
          <span className="ac-noicon" aria-hidden="true">
            ?
          </span>
        )}
        {recipe.count > 1 ? <b>{recipe.count}</b> : null}
      </span>
    </div>
  );
}

/** What the recipe is made of, three levels deep; each part that has a recipe is a button that opens it. */
function RecipeTree({
  data,
  index,
  id,
  root,
  seen,
  depth,
  onPick,
  empty,
}: {
  data: TomeData;
  index: TomeIndex;
  id: string;
  root?: RecipeRow;
  seen: Set<string>;
  depth: number;
  onPick: (id: string) => void;
  empty: string;
}) {
  const r = root ?? sureRecipe(index, id);
  if (!r || depth >= 3 || seen.has(id)) return depth === 0 ? <p className="ac-small">{empty}</p> : null;
  const parts = new Map<string, number>();
  for (const ing of ingredientsOf(data, r)) parts.set(ing.id, (parts.get(ing.id) ?? 0) + ing.n);
  const next = new Set(seen).add(id);
  return (
    <ul className="tome-tree">
      {Array.from(parts, ([pid, n]) => {
        const p = itemOf(data, pid);
        const icon = recipeIcon(p?.icon ?? null);
        const has = sureRecipe(index, pid) !== undefined;
        return (
          <li key={pid}>
            <button type="button" className="tome-tree-node" onClick={() => onPick(pid)} disabled={!has} data-leaf={!has}>
              {icon ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={icon} alt="" width={20} height={20} />
              ) : (
                <span className="ac-noicon" aria-hidden="true">
                  ?
                </span>
              )}
              <span dir="auto">{p?.name ?? pid}</span>
              <small className="ac-ltr">×{n}</small>
            </button>
            {has ? <RecipeTree data={data} index={index} id={pid} seen={next} depth={depth + 1} onPick={onPick} empty={empty} /> : null}
          </li>
        );
      })}
    </ul>
  );
}

/**
 * The blueprint (the right page): the selected recipe as text first (its station, inputs, outputs, how it is
 * made), then the picture of it. A crafting-grid recipe shows its 3 × 3; a station recipe shows the station and
 * its inputs, and never a fake grid.
 */
export function BlueprintPage({
  data,
  index,
  id,
  recipeIdx,
  onRecipeIdx,
  onPick,
  labels,
  t,
  chapterName,
  stationName,
}: {
  data: TomeData;
  index: TomeIndex;
  id: string | null;
  recipeIdx: number;
  onRecipeIdx: (i: number) => void;
  onPick: (id: string) => void;
  labels: RecipeLabels;
  t: TomeLabels;
  chapterName: string;
  stationName: (stationId: string) => string;
}) {
  const item = id !== null ? itemOf(data, id) : undefined;
  const recipes = id !== null ? (index.byResult.get(id) ?? []) : [];
  const recipe = recipes[Math.min(recipeIdx, Math.max(0, recipes.length - 1))];
  if (id === null || item === undefined || recipe === undefined) {
    return (
      <div className="tome-page-body">
        <header className="tome-page-head">
          <span className="ac-eyebrow">{t.blueprint}</span>
        </header>
        <p className="ac-small">{labels.selectPrompt}</p>
      </div>
    );
  }
  const ingredients: TomeIngredient[] = ingredientsOf(data, recipe);
  const outputs = recipe.outputs ?? [];
  const resultIcon = recipeIcon(item.icon ?? null);
  const note = labels.preview.note[item.kind];
  const sub = item.sub;
  const grouped = new Map<string, TomeIngredient & { total: number }>();
  for (const ing of ingredients) {
    const prev = grouped.get(ing.id);
    if (prev) prev.total += ing.n;
    else grouped.set(ing.id, { ...ing, total: ing.n });
  }

  return (
    <div className="tome-page-body tome-blueprint" id="tome-blueprint">
      <header className="tome-page-head">
        <span className="ac-eyebrow">{t.blueprint}</span>
        <span className="tome-badge">{chapterName}</span>
        {isStationRecipe(recipe) ? <span className="tome-badge tome-badge--station">{stationName(recipe.station)}</span> : null}
        {recipe.count > 1 ? <span className="tome-badge">×{recipe.count}</span> : null}
      </header>
      <div className="tome-title-row">
        {resultIcon ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={resultIcon} alt="" width={44} height={44} className="ac-pixel" />
        ) : null}
        <div>
          <h2 className="tome-title" dir="auto">
            {item.name}
          </h2>
          {sub ? (
            <p className="ac-small" lang="en">
              {sub}
            </p>
          ) : null}
        </div>
      </div>
      <p className="ac-small">{note}</p>

      {recipes.length > 1 ? (
        <div className="ac-chips" role="group" aria-label={t.blueprint}>
          {recipes.map((r, i) => (
            <button key={r.key} type="button" className="ac-chip" aria-pressed={i === recipeIdx} onClick={() => onRecipeIdx(i)}>
              {fill(labels.recipeN, String(i + 1))}
            </button>
          ))}
        </div>
      ) : null}

      {recipe.how && recipe.station === "workbench" ? null : <p className="ac-small ac-made-in">{fill(labels.madeIn, stationName(recipe.station))}</p>}

      {isStationRecipe(recipe) ? (
        <section className="tome-station" aria-label={t.station}>
          <h3 className="ac-eyebrow">{t.station}</h3>
          <StationPlate data={data} stationId={recipe.station} stationName={stationName} />
          <h3 className="ac-eyebrow">{t.inputs}</h3>
          <ul className="tome-lines">
            {Array.from(grouped.values()).map((ing) => (
              <ItemLine key={ing.id} data={data} id={ing.id} n={`×${ing.total}`} note={ing.any ? labels.machine.any : undefined} />
            ))}
          </ul>
          {outputs.length > 0 ? (
            <>
              <h3 className="ac-eyebrow">{t.outputs}</h3>
              <ul className="tome-lines">
                {outputs.map((o) => (
                  <ItemLine
                    key={o.id}
                    data={data}
                    id={o.id}
                    n={o.nMax !== undefined && o.nMax !== o.n ? `×${o.n}–${o.nMax}` : `×${o.n}`}
                    note={
                      o.chance !== undefined
                        ? fill(labels.machine.chance, pct(o.chance * 100))
                        : o.every !== undefined
                          ? fill(labels.machine.every, String(o.every))
                          : undefined
                    }
                  />
                ))}
              </ul>
            </>
          ) : null}
          {recipe.facts ? <MachineFacts facts={recipe.facts} labels={labels.machine} /> : null}
          {recipe.howLine ? (
            <p className="ac-small ac-how-line" lang={recipe.howLine.lang}>
              {recipe.howLine.text}
            </p>
          ) : null}
        </section>
      ) : recipe.grid ? (
        <section className="tome-grid-block" aria-label={t.gridLabel}>
          <CraftGrid data={data} recipe={recipe} resultName={item.name} />
          <h3 className="ac-eyebrow">{labels.howTo}</h3>
          <ul className="tome-lines">
            {Array.from(grouped.values()).map((ing) => (
              <ItemLine key={ing.id} data={data} id={ing.id} n={`×${ing.total}`} />
            ))}
          </ul>
        </section>
      ) : (
        <section className="tome-fusion">
          <p className="ac-small">{labels.howTo}</p>
          <ul className="tome-lines">
            {ingredients.map((f) => (
              <ItemLine key={f.id} data={data} id={f.id} n={`×${f.n}`} note={f.any ? labels.machine.any : undefined} />
            ))}
          </ul>
          {outputs.length > 1 || outputs.some((o) => o.chance !== undefined || o.nMax !== undefined || o.every !== undefined) ? (
            <>
              <p className="ac-small">{labels.machine.outputs}</p>
              <ul className="tome-lines">
                {outputs.map((o) => (
                  <ItemLine key={o.id} data={data} id={o.id} n={o.nMax !== undefined && o.nMax !== o.n ? `×${o.n}–${o.nMax}` : `×${o.n}`} />
                ))}
              </ul>
            </>
          ) : null}
          {recipe.howLine ? (
            <p className="ac-small ac-how-line" lang={recipe.howLine.lang}>
              {recipe.howLine.text}
            </p>
          ) : null}
          {recipe.facts ? <MachineFacts facts={recipe.facts} labels={labels.machine} /> : null}
        </section>
      )}

      {recipe.outputs && (recipe.inputs ?? []).length === 0 ? null : (
        <section className="tome-tree-block">
          <h3 className="ac-eyebrow">{labels.tree}</h3>
          <RecipeTree data={data} index={index} id={id} root={recipe} seen={new Set()} depth={0} onPick={onPick} empty={labels.noRecipe} />
        </section>
      )}
    </div>
  );
}

/** The station's plate: its picture and name, the machine the recipe is made in. */
function StationPlate({ data, stationId, stationName }: { data: TomeData; stationId: string; stationName: (id: string) => string }) {
  const st = stationItemOf(data, stationId);
  const icon = recipeIcon(st?.icon ?? null);
  return (
    <p className="tome-station-plate">
      {icon ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={icon} alt="" width={36} height={36} className="ac-pixel" />
      ) : null}
      <span dir="auto">{stationName(stationId)}</span>
    </p>
  );
}
