"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { chime } from "@/engine/audio";
import { burst, engine } from "@/engine/store";
import { Stage3D } from "@/engine/View";
import { Synthesizer, type SynthIngredient } from "@/realms/Synthesizer";
import { recipeIcon } from "@/lib/site";
import type { RecipeLabels, RecipeShared } from "@/lib/wiki-types";
import { Icon } from "../Icon";

export interface CodexData {
  total: number;
  cats: { index: number; name: string; icon: string | null; count: number }[];
  allTabIcon: string | null;
  items: Record<string, { name: string; sub?: string; icon: string | null; kind: "flat" | "cube" | "icon" | "none" }>;
  recipes: RecipeShared["recipes"];
  search: Record<string, string>;
  stations: { id: string; item: string | null; count: number }[];
}

function normalise(s: string): string {
  return s
    .normalize("NFKC")
    .toLowerCase()
    .replace(/[ァ-ヶ]/g, (c) => String.fromCharCode(c.charCodeAt(0) - 0x60));
}

function fill(t: string, v: string, w = ""): string {
  return t.replace("{0}", v).replace("{1}", w);
}

/** A percentage as a player reads it: 25, 2.5, 0.25. */
function pct(v: number): string {
  return String(Number(v.toPrecision(3)));
}

function ItemLine({ data, id, n, note }: { data: CodexData; id: string; n: string; note?: string }) {
  const it = data.items[id];
  const icon = recipeIcon(it?.icon ?? null);
  return (
    <li>
      {icon ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={icon} alt="" width={24} height={24} className="ac-pixel" />
      ) : null}
      <span dir="auto">{it?.name ?? id}</span>
      <small className="ac-ltr">{n}</small>
      {note ? <small className="ac-small">{note}</small> : null}
    </li>
  );
}

/** Time, water, experience, and the bore's share of a dimension's veins. */
function MachineFacts({ facts, labels }: { facts: NonNullable<CodexData["recipes"][number]["facts"]>; labels: RecipeLabels["machine"] }) {
  const parts: string[] = [];
  if (facts.dimension && facts.share !== undefined) parts.push(fill(labels.vein, labels[facts.dimension], pct(facts.share)));
  if (facts.time) parts.push(fill(labels.time, pct(facts.time / 20)));
  if (facts.water) parts.push(fill(labels.water, String(facts.water)));
  if (facts.xp) parts.push(fill(labels.xp, pct(facts.xp)));
  return parts.length ? <p className="ac-small ac-machine-facts">{parts.join(" · ")}</p> : null;
}

/**
 * The Alchemy Codex: every crafting recipe of OUKA, Cherry and ASTRAEA. Search, category and
 * station filters, the 3×3 grid laid out as on a crafting table (left to right even in Arabic),
 * the ingredient tree three levels deep, and the synthesiser that builds the item in 3D.
 * `#0`–`#2` choose a category and `#item=<id>` an item; choosing writes the hash in place.
 */
export function Codex({
  data,
  labels,
  fresh,
}: {
  data: CodexData;
  labels: RecipeLabels;
  fresh: { synthesise: string; replay: string; result: string; fusing: string };
}) {
  const [query, setQuery] = useState("");
  const [cat, setCat] = useState<number | null>(null);
  const [station, setStation] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [recipeIdx, setRecipeIdx] = useState(0);
  const [playKey, setPlayKey] = useState(0);
  const [fusing, setFusing] = useState(false);
  const [spinning, setSpinning] = useState(true);
  const turn = useRef(0);
  const drag = useRef<{ x: number; id: number } | null>(null);

  // Recipes per result item, in the sheet's order.
  const byResult = useMemo(() => {
    const m = new Map<string, CodexData["recipes"]>();
    for (const r of data.recipes) {
      const list = m.get(r.result);
      if (list) list.push(r);
      else m.set(r.result, [r]);
    }
    return m;
  }, [data.recipes]);
  const order = useMemo(() => Array.from(byResult.keys()), [byResult]);

  // While the synthesiser flies the ingredients in (until its fuseAt), the button says so.
  useEffect(() => {
    if (playKey === 0 || engine.reducedMotion) return;
    setFusing(true);
    const id = window.setTimeout(() => setFusing(false), 1150);
    return () => window.clearTimeout(id);
  }, [playKey]);

  useEffect(() => {
    const h = decodeURIComponent(window.location.hash.slice(1));
    if (/^\d+$/.test(h) && Number(h) < data.cats.length) setCat(Number(h));
    else if (h.startsWith("item=")) {
      const id = h.slice(5);
      if (byResult.has(id)) setSelected(id);
    }
  }, [byResult, data.cats.length]);

  const q = normalise(query.trim());
  const visible = useMemo(
    () =>
      order.filter((id) =>
        (byResult.get(id) ?? []).some(
          (r) => (cat === null || r.cat === cat) && (station === null || r.station === station) && (q === "" || (data.search[r.key] ?? "").includes(q)),
        ),
      ),
    [order, byResult, cat, station, q, data.search],
  );

  const current = selected ?? visible[0] ?? order[0] ?? null;
  const recipes = current !== null ? (byResult.get(current) ?? []) : [];
  const recipe = recipes[Math.min(recipeIdx, recipes.length - 1)];
  const item = current !== null ? data.items[current] : undefined;

  const choose = useCallback((id: string) => {
    setSelected(id);
    setRecipeIdx(0);
    setPlayKey((k) => k + 1);
    chime("tick");
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${window.location.search}#item=${encodeURIComponent(id)}`);
  }, []);

  const pickCat = (c: number | null): void => {
    setCat(c);
    chime("tick");
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}${window.location.search}${c === null ? "" : `#${c}`}`,
    );
  };

  const stationName = (id: string): string => {
    const st = data.stations.find((s) => s.id === id);
    return st?.item ? (data.items[st.item]?.name ?? id) : id;
  };

  const ingredients: SynthIngredient[] = useMemo(() => {
    if (recipe === undefined) return [];
    if (recipe.grid) {
      return recipe.grid.flatMap((cell, slot) => {
        if (cell === 0) return [];
        const it = data.items[cell];
        return [{ slot, icon: recipeIcon(it?.icon ?? null), kind: it?.kind ?? "none" }];
      });
    }
    return (recipe.fusion ?? []).flatMap((f) => {
      const it = data.items[f.id];
      const copies = Math.min(f.n, 3);
      return Array.from({ length: copies }, () => ({ slot: -1, icon: recipeIcon(it?.icon ?? null), kind: it?.kind ?? "none" }));
    });
  }, [recipe, data.items]);

  // The tree: each ingredient's first recipe, three levels deep.
  // A part's own recipe in the tree is the first one that reliably makes it: not a centrifuge's chance nor a bore's vein.
  const sureRecipe = (id: string): CodexData["recipes"][number] | undefined =>
    (byResult.get(id) ?? []).find((r) => !(r.outputs ?? []).some((o) => o.chance !== undefined || o.nMax !== undefined || (o.id === id && o.every !== undefined)));
  const tree = (id: string, depth: number, seen: Set<string>, root?: CodexData["recipes"][number]): React.ReactNode => {
    const r = root ?? sureRecipe(id);
    if (!r || depth >= 3 || seen.has(id)) return null;
    const parts = new Map<string, number>();
    if (r.grid) for (const c of r.grid) if (c !== 0) parts.set(c, (parts.get(c) ?? 0) + 1);
    for (const f of r.fusion ?? []) parts.set(f.id, (parts.get(f.id) ?? 0) + f.n);
    const next = new Set(seen).add(id);
    return (
      <ul>
        {Array.from(parts, ([pid, n]) => {
          const p = data.items[pid];
          const icon = recipeIcon(p?.icon ?? null);
          return (
            <li key={pid}>
              <button type="button" className="ac-tree-node" onClick={() => (byResult.has(pid) ? choose(pid) : undefined)} data-leaf={!sureRecipe(pid)}>
                {icon ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={icon} alt="" width={20} height={20} />
                ) : (
                  <span className="ac-noicon">?</span>
                )}
                <span>{p?.name ?? pid}</span>
                <small className="ac-ltr">×{n}</small>
              </button>
              {sureRecipe(pid) ? tree(pid, depth + 1, next) : null}
            </li>
          );
        })}
      </ul>
    );
  };

  const onPointerDown = (e: React.PointerEvent<HTMLDivElement>): void => {
    drag.current = { x: e.clientX, id: e.pointerId };
    e.currentTarget.setPointerCapture(e.pointerId);
  };
  const onPointerMove = (e: React.PointerEvent<HTMLDivElement>): void => {
    if (drag.current === null || drag.current.id !== e.pointerId) return;
    turn.current += (e.clientX - drag.current.x) * 0.012;
    drag.current.x = e.clientX;
  };
  const onPointerUp = (): void => {
    drag.current = null;
  };
  const onKeyDown = (e: React.KeyboardEvent<HTMLDivElement>): void => {
    if (e.key === "ArrowLeft") turn.current -= 0.3;
    else if (e.key === "ArrowRight") turn.current += 0.3;
  };

  const resultIcon = recipeIcon(item?.icon ?? null);
  const note = item ? labels.preview.note[item.kind] : "";

  return (
    <div className="ac-codex">
      <div className="ac-codex-tools">
        <label className="ac-search">
          <Icon name="search" size={16} />
          <input
            type="search"
            className="ac-input"
            placeholder={labels.search}
            aria-label={labels.search}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </label>
        <div className="ac-chips" role="group">
          <button type="button" className="ac-chip" aria-pressed={cat === null} onClick={() => pickCat(null)}>
            {labels.all}
            <span className="ac-count">{data.total}</span>
          </button>
          {data.cats.map((c) => (
            <button key={c.index} type="button" className="ac-chip" aria-pressed={cat === c.index} onClick={() => pickCat(c.index)}>
              {c.icon ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={recipeIcon(c.icon) ?? ""} alt="" width={18} height={18} className="ac-pixel" />
              ) : null}
              {c.name}
              <span className="ac-count">{c.count}</span>
            </button>
          ))}
        </div>
        <div className="ac-chips ac-stations" role="group" aria-label={labels.stations}>
          <span className="ac-small">{labels.stations}</span>
          {data.stations.map((s) => {
            const icon = s.item ? recipeIcon(data.items[s.item]?.icon ?? null) : null;
            return (
              <button
                key={s.id}
                type="button"
                className="ac-chip"
                aria-pressed={station === s.id}
                onClick={() => {
                  setStation((v) => (v === s.id ? null : s.id));
                  chime("tick");
                }}
              >
                {icon ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={icon} alt="" width={18} height={18} className="ac-pixel" />
                ) : null}
                {stationName(s.id)}
                <span className="ac-count">{s.count > 0 ? s.count : "—"}</span>
              </button>
            );
          })}
        </div>
        {station === "fabricator" && (data.stations.find((s) => s.id === "fabricator")?.count ?? 0) === 0 ? (
          <p className="ac-small ac-codex-note">{labels.stationNoneFabricator}</p>
        ) : null}
      </div>

      <div className="ac-codex-body">
        <div>
          <p className="ac-small" aria-live="polite">
            {visible.length}
            {labels.countSuffix.startsWith(" ") ? labels.countSuffix : ` ${labels.countSuffix}`}
          </p>
          {visible.length === 0 ? <p className="ac-codex-empty">{labels.empty}</p> : null}
          <ul className="ac-codex-grid">
            {visible.map((id) => {
              const it = data.items[id];
              const icon = recipeIcon(it?.icon ?? null);
              return (
                <li key={id}>
                  <button type="button" className="ac-item ac-card" aria-pressed={id === current} onClick={() => choose(id)}>
                    {icon ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={icon} alt="" width={32} height={32} className="ac-pixel" loading="lazy" />
                    ) : (
                      <span className="ac-noicon">?</span>
                    )}
                    <span dir="auto">{it?.name ?? id}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </div>

        <aside className="ac-codex-detail ac-card" aria-live="polite">
          {item === undefined || recipe === undefined ? (
            <p className="ac-small">{labels.selectPrompt}</p>
          ) : (
            <>
              <div
                className="ac-synth"
                tabIndex={0}
                role="group"
                aria-label={`${labels.preview.title}: ${item.name}. ${labels.preview.drag}`}
                onPointerDown={onPointerDown}
                onPointerMove={onPointerMove}
                onPointerUp={onPointerUp}
                onPointerCancel={onPointerUp}
                onKeyDown={onKeyDown}
              >
                <Stage3D
                  className="ac-synth-stage"
                  fov={30}
                  position={[0, 0.18, 4.4]}
                  fallback={
                    resultIcon ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={resultIcon} alt="" width={128} height={128} className="ac-pixel" />
                    ) : null
                  }
                >
                  <Synthesizer
                    result={{ icon: resultIcon, kind: item.kind }}
                    ingredients={ingredients}
                    playKey={playKey * 31 + recipeIdx}
                    spinning={spinning}
                    turn={turn}
                  />
                </Stage3D>
                <div className="ac-synth-controls">
                  <button
                    type="button"
                    className="ac-iconbtn"
                    aria-label={spinning ? labels.preview.pause : labels.preview.rotate}
                    title={spinning ? labels.preview.pause : labels.preview.rotate}
                    onClick={() => setSpinning((v) => !v)}
                  >
                    <Icon name={spinning ? "pause" : "rotate"} size={15} />
                  </button>
                  <button
                    type="button"
                    className="ac-btn ac-btn--ghost ac-btn--small"
                    onClick={() => {
                      setPlayKey((k) => k + 1);
                      burst(0, 0, 0, 0.6);
                    }}
                  >
                    <Icon name="sparkle" size={14} />
                    <span aria-live="polite">{fusing ? fresh.fusing : playKey === 0 ? fresh.synthesise : fresh.replay}</span>
                  </button>
                </div>
              </div>
              <p className="ac-small ac-synth-note">{note}</p>

              <p className="ac-eyebrow ac-codex-result">{fresh.result}</p>
              <h2 className="ac-h3 ac-codex-name">{item.name}</h2>
              {item.sub ? (
                <p className="ac-small" lang="en">
                  {item.sub}
                </p>
              ) : null}

              {recipes.length > 1 ? (
                <div className="ac-chips">
                  {recipes.map((r, i) => (
                    <button
                      key={r.key}
                      type="button"
                      className="ac-chip"
                      aria-pressed={i === recipeIdx}
                      onClick={() => {
                        setRecipeIdx(i);
                        setPlayKey((k) => k + 1);
                      }}
                    >
                      {fill(labels.recipeN, String(i + 1))}
                    </button>
                  ))}
                </div>
              ) : null}

              {/* A how-to card is for something a workbench cannot make (a campfire, a machine). Only a machine that
          was named in its text is a station; the default "workbench" would be a false statement. */}
              {recipe.how && recipe.station === "workbench" ? null : (
                <p className="ac-small ac-made-in">{fill(labels.madeIn, stationName(recipe.station))}</p>
              )}
              {recipe.grid ? (
                <div className="ac-craft" dir="ltr">
                  <div className="ac-craft-grid">
                    {recipe.grid.map((cell, i) => {
                      const it = cell === 0 ? undefined : data.items[cell];
                      const icon = recipeIcon(it?.icon ?? null);
                      return (
                        <span key={i} className="ac-slot" title={it?.name}>
                          {cell === 0 ? null : icon ? (
                            // eslint-disable-next-line @next/next/no-img-element
                            <img src={icon} alt={it?.name ?? ""} width={32} height={32} className="ac-pixel" />
                          ) : (
                            <span className="ac-noicon">?</span>
                          )}
                        </span>
                      );
                    })}
                  </div>
                  <span className="ac-craft-arrow" aria-hidden="true">
                    →
                  </span>
                  <span className="ac-slot ac-slot--result" title={item.name}>
                    {resultIcon ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={resultIcon} alt={item.name} width={32} height={32} className="ac-pixel" />
                    ) : (
                      <span className="ac-noicon">?</span>
                    )}
                    {recipe.count > 1 ? <b>{recipe.count}</b> : null}
                  </span>
                </div>
              ) : (
                <div className="ac-fusion">
                  <p className="ac-small">{labels.howTo}</p>
                  {recipe.outputs && (recipe.inputs ?? []).length === 0 ? <p className="ac-small">{labels.machine.drill}</p> : null}
                  <ul>
                    {(recipe.inputs ?? recipe.fusion ?? []).map((f) => (
                      <ItemLine key={f.id} data={data} id={f.id} n={`×${f.n}`} note={"any" in f && f.any ? labels.machine.any : undefined} />
                    ))}
                  </ul>
                  {recipe.outputs && (recipe.outputs.length > 1 || recipe.outputs.some((o) => o.chance !== undefined || o.nMax !== undefined || o.every !== undefined)) ? (
                    <>
                      <p className="ac-small">{labels.machine.outputs}</p>
                      <ul>
                        {recipe.outputs.map((o) => (
                          <ItemLine
                            key={o.id}
                            data={data}
                            id={o.id}
                            n={o.nMax !== undefined && o.nMax !== o.n ? `×${o.n}–${o.nMax}` : `×${o.n}`}
                            note={o.chance !== undefined ? fill(labels.machine.chance, pct(o.chance * 100)) : o.every !== undefined ? fill(labels.machine.every, String(o.every)) : undefined}
                          />
                        ))}
                      </ul>
                    </>
                  ) : null}
                  {recipe.facts ? <MachineFacts facts={recipe.facts} labels={labels.machine} /> : null}
                </div>
              )}

              {recipe.outputs && (recipe.inputs ?? []).length === 0 ? null : (
                <div className="ac-tree">
                  <h3 className="ac-eyebrow">{labels.tree}</h3>
                  {tree(current!, 0, new Set(), recipe) ?? <p className="ac-small">{labels.noRecipe}</p>}
                </div>
              )}
            </>
          )}
        </aside>
      </div>
    </div>
  );
}
