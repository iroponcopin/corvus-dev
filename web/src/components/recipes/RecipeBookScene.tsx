"use client";

import { type CSSProperties, type KeyboardEvent, type PointerEvent as ReactPointerEvent, type ReactNode, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { chime } from "@/engine/audio";
import type { Fresh } from "@/i18n/fresh";
import { BRAND_COLOR } from "@/lib/brands";
import { asset, recipeIcon } from "@/lib/site";
import type { Dir, RecipeLabels } from "@/lib/wiki-types";
import { BlueprintPage, fill, IndexPage } from "./BookSpread";
import { useReducedMotion, useWide } from "./hooks";
import { FlipLayer, type FlipHandle, type FlipPlan } from "./PageFlipController";
import { RecipeCommandBar, type CommandResult } from "./RecipeCommandBar";
import {
  buildIndex,
  catOfModel,
  filterIds,
  ingredientsOf,
  normalise,
  pageOf,
  paginate,
  stationItemOf,
  type TomeData,
  type TomeFilter,
  type TomeIngredient,
} from "./tome-data";
import { VoxelItemStage } from "./VoxelItemStage";

type TomeLabels = Fresh["tome"];

/** The accent of "All": the Tome's gold, when no model is in view. */
const ALL_ACCENT = "#e2c07a";
/** Each chapter's emblem, from the portal's icons folder. */
const MODEL_ICON: Record<string, string> = { ouka: "icons/ouka.png", cherry: "icons/cherry.png", tsubomi: "icons/tsubomi.png", halia: "icons/halia.png" };
/** Result rows the command bar draws at most; the count line tells the rest. */
const CMD_LIMIT = 40;
const ALL: TomeFilter = { cat: null, station: null, query: "" };

export interface RecipeBookSceneProps {
  data: TomeData;
  labels: RecipeLabels;
  t: TomeLabels;
  dir: Dir;
}

/** A page turn in flight: the plan, what the book shows under it, and where it lands when it completes. */
interface PlanState extends FlipPlan {
  id: number;
  filter: TomeFilter;
  target: number;
  select: string | null;
  staticLeft: ReactNode;
  staticRight: ReactNode;
}

function countText(n: number, suffix: string): string {
  return `${n}${suffix.startsWith(" ") ? suffix : ` ${suffix}`}`;
}

/**
 * The Recipe Tome: the book (index pages on the left, the blueprint of the selected recipe on the right) with the
 * crafting pedestal beside it. Desktop shows both; narrow screens show one page at a time, the pedestal as an
 * expandable viewport above. Every move (chapter, station, search, page turn, deep link, a part in the tree) goes
 * through one path: it works out the spread it lands on, turns a leaf or riffles when the target is more than a
 * page away, and only then commits the filter, the spread and the selection together.
 */
export function RecipeBookScene({ data, labels, t, dir }: RecipeBookSceneProps) {
  const wide = useWide();
  const reduced = useReducedMotion();
  const index = useMemo(() => buildIndex(data), [data]);

  const [filter, setFilter] = useState<TomeFilter>(ALL);
  const [spread, setSpread] = useState(0);
  const [selected, setSelected] = useState<string | null>(null);
  const [recipeIdx, setRecipeIdx] = useState(0);
  const [playKey, setPlayKey] = useState(0);
  const [plan, setPlan] = useState<PlanState | null>(null);
  const planRef = useRef<PlanState | null>(null);
  const planSeq = useRef(0);
  const flipRef = useRef<FlipHandle | null>(null);
  const [view, setView] = useState<"index" | "blueprint">("index");
  const [stageOpen, setStageOpen] = useState(false);
  const [cmdOpen, setCmdOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const opener = useRef<HTMLElement | null>(null);
  const drag = useRef<{ x: number; id: number; active: boolean; last: number; width: number } | null>(null);

  // ---- the committed state, derived --------------------------------------------------------------------------

  const ids = useMemo(() => filterIds(data, index, filter), [data, index, filter]);
  // One unit everywhere: an ITEM (a distinct result the book lists), counted with the same filter the book uses.
  // The All chip, every chapter ribbon, every station chip, the count line and the command bar all read this.
  const allCount = index.order.length;
  const catCounts = useMemo(() => new Map(data.cats.map((c) => [c.index, filterIds(data, index, { cat: c.index, station: null, query: "" }).length])), [data, index]);
  const stationCounts = useMemo(() => new Map(data.stations.map((s) => [s.id, filterIds(data, index, { cat: null, station: s.id, query: "" }).length])), [data, index]);
  const pages = useMemo(() => paginate(ids), [ids]);
  const last = Math.max(0, pages.length - 1);
  const cur = Math.min(spread, last);
  const pageIds = pages[cur] ?? [];
  const current = selected !== null && pageIds.includes(selected) ? selected : (pageIds[0] ?? null);
  const recipes = current !== null ? (index.byResult.get(current) ?? []) : [];
  const recipe = recipes[Math.min(recipeIdx, Math.max(0, recipes.length - 1))];
  const item = current !== null ? data.items[current] : undefined;

  const catOf = useCallback((id: string | null): number | null => (id === null ? null : (index.byResult.get(id)?.[0]?.cat ?? null)), [index]);
  const catName = useCallback((c: number | null): string => (c === null ? labels.all : (data.cats[c]?.name ?? "")), [data.cats, labels.all]);
  const stationName = useCallback((id: string): string => stationItemOf(data, id)?.name ?? id, [data]);

  const curCat = catOf(current) ?? filter.cat;
  const model = curCat !== null ? data.cats[curCat]?.model : undefined;
  const accent = (model && BRAND_COLOR[model]) || ALL_ACCENT;
  const ingredients: TomeIngredient[] = recipe ? ingredientsOf(data, recipe) : [];
  const layout: "grid" | "station" = recipe?.grid ? "grid" : "station";
  const stationPlate = recipe && !recipe.grid ? { name: stationName(recipe.station), icon: recipeIcon(stationItemOf(data, recipe.station)?.icon ?? null) } : null;

  const stageLabels = useMemo(
    () => ({
      stage: t.stage,
      hint: t.stageHint,
      explode: t.explode,
      spin: t.spin,
      grid: t.grid,
      reset: t.reset,
      noWebgl: t.noWebgl,
      ritual: t.stageRitual,
      ready: t.stageReady,
      show: t.show3d,
      hide: t.hide3d,
    }),
    [t],
  );

  // ---- pages as they read (built for the committed state, or for a snapshot during a turn) -----------------

  const indexPage = (list: string[], picked: string | null, n: number, total: number, cat: number | null, pick: (id: string) => void): ReactNode => (
    <IndexPage
      id={`page-${n + 1}`}
      ids={list}
      data={data}
      selected={picked}
      onPick={pick}
      chapter={catName(cat)}
      count={countText(list.length, t.itemWord)}
      empty={labels.empty}
      eyebrow={fill(t.pageOf, String(n + 1), String(Math.max(1, total)))}
    />
  );
  const bluePage = (id: string | null, idx: number, cat: number | null): ReactNode => (
    <BlueprintPage
      data={data}
      index={index}
      id={id}
      recipeIdx={idx}
      onRecipeIdx={setRecipeIdx}
      onPick={goItem}
      labels={labels}
      t={t}
      chapterName={catName(cat)}
      stationName={stationName}
    />
  );

  // ---- committing a move -------------------------------------------------------------------------------------

  const writeHash = useCallback((id: string | null, c: number | null) => {
    const hash = id !== null ? `#item=${encodeURIComponent(id)}` : c !== null ? `#${c}` : "";
    window.history.replaceState(window.history.state, "", `${window.location.pathname}${window.location.search}${hash}`);
  }, []);

  const pickItem = useCallback(
    (id: string) => {
      setSelected(id);
      setRecipeIdx(0);
      setPlayKey((k) => k + 1);
      chime("tick");
      writeHash(id, null);
    },
    [writeHash],
  );

  const commit = useCallback(
    (f: TomeFilter, target: number, pick: string | null) => {
      planRef.current = null;
      setPlan(null);
      setFilter(f);
      setSpread(target);
      if (pick !== null) pickItem(pick);
      else {
        setSelected(null);
        setRecipeIdx(0);
        writeHash(null, f.cat);
      }
    },
    [pickItem, writeHash],
  );

  const finish = useCallback(
    (committed: boolean) => {
      const p = planRef.current;
      if (p !== null && committed) commit(p.filter, p.target, p.select);
      else {
        planRef.current = null;
        setPlan(null);
      }
    },
    [commit],
  );

  /**
   * One move. Staying on the same spread changes at once; a move of one page turns a leaf; more than one page
   * riffles several. A narrow screen turns index pages only and changes everything else at once. `manual` opens a
   * turn the reader drags: it waits for a release.
   */
  const navigate = useCallback(
    (next: TomeFilter, target: number, pick: string | null, opts?: { manual?: boolean; animate?: boolean }) => {
      const manual = opts?.manual === true;
      // Narrow screens animate page turns (and riffles) only when the caller asks: the rest changes at once.
      const canAnimate = wide || opts?.animate === true;
      const nextPages = paginate(filterIds(data, index, next));
      const to = Math.min(Math.max(0, target), Math.max(0, nextPages.length - 1));
      const pickId = pick ?? nextPages[to]?.[0] ?? null;
      const dist = Math.abs(to - cur);
      const forward = to > cur;
      const single = !wide;
      if (!manual && (!canAnimate || reduced || pages.length === 0 || nextPages.length === 0 || dist === 0)) {
        // Same spread, nothing to show, reduced motion, or no animation asked for: the book changes at once.
        commit(next, to, pickId);
        return;
      }
      const fromL = indexPage(pageIds, current, cur, pages.length, filter.cat, pickItem);
      const fromR = bluePage(current, recipeIdx, curCat);
      const toL = indexPage(nextPages[to] ?? [], pickId, to, nextPages.length, next.cat, pickItem);
      const toR = bluePage(pickId, 0, catOf(pickId));
      const leaves = dist <= 1 ? 1 : dist >= 8 ? 5 : dist >= 4 ? 4 : 3;
      const p: PlanState = {
        id: ++planSeq.current,
        dir: forward || single ? 1 : -1,
        leaves,
        duration: leaves > 1 ? 350 : 900,
        single: single || undefined,
        manual: manual || undefined,
        front: single ? fromL : forward ? fromR : fromL,
        back: single ? toL : forward ? toL : toR,
        staticLeft: single || forward ? fromL : toL,
        staticRight: forward && !single ? toR : fromR,
        filter: next,
        target: to,
        select: pickId,
      };
      planRef.current = p;
      setPlan(p);
    },
    // Reads the committed state; rebuilt when that state changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [data, index, filter, cur, pages.length, pageIds, current, recipeIdx, curCat, wide, reduced, commit, pickItem],
  );

  /** Opens an item wherever it is: on this page, in the filtered list, or in the whole Tome. */
  function goItem(id: string): void {
    const inFilter = ids.includes(id);
    const f = inFilter ? filter : ALL;
    const list = inFilter ? ids : filterIds(data, index, ALL);
    navigate(f, pageOf(list, id), id, { animate: wide });
    if (!wide) setView("blueprint");
  }

  /** A pick on an index page: the item is selected where it stands, the book does not turn. */
  const pickIndex = useCallback(
    (id: string) => {
      pickItem(id);
      if (!wide) setView("blueprint");
    },
    [pickItem, wide],
  );

  const turn = (d: 1 | -1): void => {
    if (plan !== null) return;
    const to = cur + d;
    if (to < 0 || to > last) return;
    navigate(filter, to, null, { animate: true });
  };

  const stepItem = (d: 1 | -1): void => {
    if (current === null) return;
    const next = ids[ids.indexOf(current) + d];
    if (next !== undefined) goItem(next);
  };

  // A chapter or a station is a bookmark: on narrow screens it opens on the index, and the jump riffles.
  const chooseChapter = (c: number | null): void => {
    const f: TomeFilter = { ...filter, cat: c === filter.cat ? null : c, station: null };
    if (!wide) setView("index");
    navigate(f, 0, filterIds(data, index, f)[0] ?? null, { animate: true });
  };

  const chooseStation = (s: string): void => {
    const f: TomeFilter = { ...filter, station: filter.station === s ? null : s };
    if (!wide) setView("index");
    navigate(f, 0, filterIds(data, index, f)[0] ?? null, { animate: true });
  };

  const clearQuery = (): void => {
    const f: TomeFilter = { ...filter, query: "" };
    const list = filterIds(data, index, f);
    const keep = current !== null && list.includes(current) ? current : (list[0] ?? null);
    navigate(f, keep !== null ? pageOf(list, keep) : 0, keep, { animate: wide });
  };

  // ---- command bar -------------------------------------------------------------------------------------------

  const cmdQuery = normalise(draft.trim());
  const cmdIds = useMemo(() => (cmdQuery === "" ? index.order : filterIds(data, index, { cat: null, station: null, query: cmdQuery })), [cmdQuery, data, index]);
  const cmdResults: CommandResult[] = useMemo(
    () =>
      cmdIds.slice(0, CMD_LIMIT).map((id) => {
        const it = data.items[id];
        return { id, name: it?.name ?? id, sub: it?.sub, icon: it?.icon ?? null, chapter: catName(catOf(id)) };
      }),
    [catName, catOf, cmdIds, data.items],
  );

  const openCmd = (): void => {
    opener.current = document.activeElement as HTMLElement | null;
    setDraft(filter.query);
    setCmdOpen(true);
  };
  const closeCmd = useCallback(() => {
    setCmdOpen(false);
    opener.current?.focus();
  }, []);
  const pickCmd = (id: string): void => {
    const f: TomeFilter = { cat: null, station: null, query: cmdQuery };
    setCmdOpen(false);
    navigate(f, pageOf(filterIds(data, index, f), id), id, { animate: wide });
    if (!wide) setView("blueprint");
  };

  // ---- deep links: ?model=<id>, #<chapter>, #item=<id> (read once, at open; no turn) -------------------------

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const h = decodeURIComponent(window.location.hash.slice(1));
    let f: TomeFilter = ALL;
    let pick: string | null = null;
    const modelCat = params.get("model") !== null ? catOfModel(data, params.get("model") ?? "") : null;
    if (modelCat !== null) f = { ...ALL, cat: modelCat };
    if (/^\d+$/.test(h) && Number(h) < data.cats.length) f = { ...ALL, cat: Number(h) };
    if (h.startsWith("item=") && index.byResult.has(h.slice(5))) {
      pick = h.slice(5);
      f = { ...ALL, cat: catOf(pick) };
    }
    if (pick !== null && !filterIds(data, index, f).includes(pick)) f = ALL;
    const list = filterIds(data, index, f);
    setFilter(f);
    setSpread(pick !== null ? Math.max(0, pageOf(list, pick)) : 0);
    if (pick !== null) {
      setSelected(pick);
      if (!wide) setView("blueprint");
    }
    // Only the address the page opened with is read; later moves go through the book.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [data, index]);

  // The page's own spotlight takes ⌘K / Ctrl K before the site palette (a document listener) sees it: this runs in the
  // capture phase on window and stops the event there, so the palette opens only from the header's search button.
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent): void => {
      if ((e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        e.stopImmediatePropagation();
        if (cmdOpen) closeCmd();
        else openCmd();
      }
    };
    window.addEventListener("keydown", onKey, true);
    return () => window.removeEventListener("keydown", onKey, true);
    // openCmd reads only the committed filter; re-binding on the open state is enough.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cmdOpen, closeCmd]);

  // ---- pointer and keyboard turning ---------------------------------------------------------------------------

  const onPointerDown = (e: ReactPointerEvent<HTMLDivElement>): void => {
    if ((e.target as HTMLElement).closest("button, a, input, select, textarea, label")) return;
    if (reduced || planRef.current !== null) return;
    drag.current = { x: e.clientX, id: e.pointerId, active: false, last: 0, width: e.currentTarget.clientWidth / (wide ? 2 : 1) };
  };
  const onPointerMove = (e: ReactPointerEvent<HTMLDivElement>): void => {
    const d = drag.current;
    if (d === null || d.id !== e.pointerId) return;
    const dx = e.clientX - d.x;
    if (!d.active) {
      if (Math.abs(dx) < 12) return;
      // A narrow blueprint is stepped through by swiping, not turned: only index pages curl.
      if (!wide && view === "blueprint") return;
      const to = cur + (dx < 0 ? 1 : -1);
      if (to < 0 || to > last) return;
      d.active = true;
      // The drag is a page turn, not a text selection: any selection it made is cleared.
      window.getSelection()?.removeAllRanges();
      navigate(filter, to, null, { manual: true });
      return;
    }
    d.last = dx;
    flipRef.current?.drag(Math.min(1, Math.abs(dx) / Math.max(1, d.width)));
  };
  const onPointerUp = (e: ReactPointerEvent<HTMLDivElement>): void => {
    const d = drag.current;
    drag.current = null;
    if (d === null || d.id !== e.pointerId) return;
    if (!d.active) {
      if (!wide && view === "blueprint" && Math.abs(e.clientX - d.x) > 40) stepItem(e.clientX < d.x ? 1 : -1);
      return;
    }
    const p = Math.min(1, Math.abs(d.last) / Math.max(1, d.width));
    if (flipRef.current) flipRef.current.release(p > 0.4);
    else finish(false);
  };

  const onBookKey = (e: KeyboardEvent<HTMLDivElement>): void => {
    if (e.target !== e.currentTarget) return;
    const forwardKey = e.key === "ArrowRight" ? (dir === "rtl" ? -1 : 1) : e.key === "ArrowLeft" ? (dir === "rtl" ? 1 : -1) : 0;
    if (forwardKey === 0) return;
    e.preventDefault();
    if (!wide && view === "blueprint") stepItem(forwardKey as 1 | -1);
    else turn(forwardKey as 1 | -1);
  };

  // ---- render --------------------------------------------------------------------------------------------------

  const liveLeft = indexPage(pageIds, current, cur, pages.length, filter.cat, pickIndex);
  const liveRight = bluePage(current, recipeIdx, curCat);
  const shownLeft = plan ? plan.staticLeft : liveLeft;
  const shownRight = plan ? plan.staticRight : liveRight;
  const bookStyle = {
    "--accent": accent,
    "--stack-l": `${Math.min(10, cur)}px`,
    "--stack-r": `${Math.min(10, last - cur)}px`,
  } as CSSProperties;
  const folio = fill(t.pageOf, String(cur + 1), String(Math.max(1, pages.length)));
  const atStart = cur === 0;
  const atEnd = cur >= last;
  const idxInPage = current !== null ? ids.indexOf(current) : -1;

  const chapterButtons = (
    <>
      <li>
        <button type="button" className="tome-ribbon tome-ribbon--all" aria-pressed={filter.cat === null} tabIndex={0} onClick={() => chooseChapter(null)}>
          {data.allTabIcon ? (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={recipeIcon(data.allTabIcon) ?? ""} alt="" width={20} height={20} className="ac-pixel" />
          ) : null}
          <span>{labels.all}</span>
          <small className="ac-count">{allCount}</small>
        </button>
      </li>
      {data.cats.map((c) => (
        <li key={c.index}>
          <button
            type="button"
            className="tome-ribbon"
            aria-pressed={filter.cat === c.index}
            style={{ "--ribbon": BRAND_COLOR[c.model] ?? ALL_ACCENT } as CSSProperties}
            onClick={() => chooseChapter(c.index)}
          >
            {MODEL_ICON[c.model] ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={asset(MODEL_ICON[c.model] ?? "")} alt="" width={20} height={20} className="ac-pixel" />
            ) : null}
            <span>{c.name}</span>
            <small className="ac-count">{catCounts.get(c.index) ?? 0}</small>
          </button>
        </li>
      ))}
    </>
  );

  return (
    <div className="tome" dir={dir} style={{ "--accent": accent } as CSSProperties}>
      <div className="tome-toolbar">
        <button type="button" className="tome-engraved" onClick={openCmd} aria-haspopup="dialog">
          <span className="tome-engraved-text">{filter.query !== "" ? filter.query : labels.search}</span>
          <kbd className="tome-kbd">⌘K / Ctrl K</kbd>
        </button>
        {filter.query !== "" ? (
          <button type="button" className="ac-chip" onClick={clearQuery}>
            {t.clear}
          </button>
        ) : null}
        <span className="ac-small" aria-live="polite">
          {countText(ids.length, t.itemWord)}
        </span>
      </div>

      <div className="tome-layout">
        <div className="tome-book-col">
          <nav className="tome-ribbons" aria-label={t.chapters}>
            <ul className="tome-ribbon-list">{chapterButtons}</ul>
          </nav>
          <div className="tome-stations" role="group" aria-label={labels.stations}>
            <span className="ac-small">{labels.stations}</span>
            {data.stations
              .filter((s) => (stationCounts.get(s.id) ?? 0) > 0)
              .map((s) => (
                <button key={s.id} type="button" className="ac-chip" aria-pressed={filter.station === s.id} onClick={() => chooseStation(s.id)}>
                  {stationName(s.id)}
                  <span className="ac-count">{stationCounts.get(s.id) ?? 0}</span>
                </button>
              ))}
          </div>
          {!wide ? (
            <div className="tome-viewtabs" role="group" aria-label={t.blueprint}>
              <button type="button" className="ac-chip" aria-pressed={view === "index"} onClick={() => setView("index")}>
                {t.index}
              </button>
              <button type="button" className="ac-chip" aria-pressed={view === "blueprint"} onClick={() => setView("blueprint")}>
                {t.blueprint}
              </button>
            </div>
          ) : null}

          <div className="tome-book-wrap">
            <div
              className={`tome-book${wide ? " is-wide" : " is-narrow"}${plan !== null ? " is-turning" : ""}`}
              style={bookStyle}
              tabIndex={0}
              role="group"
              aria-roledescription="book"
              aria-label={t.eyebrow}
              onKeyDown={onBookKey}
            >
              <div className="tome-spine" aria-hidden="true" />
              <nav className="tome-ribbons-edge" aria-hidden="true">
                {data.cats.map((c) => (
                  <button
                    key={c.index}
                    type="button"
                    tabIndex={-1}
                    className="tome-ribbon-edge"
                    aria-pressed={filter.cat === c.index}
                    style={{ "--ribbon": BRAND_COLOR[c.model] ?? ALL_ACCENT } as CSSProperties}
                    onClick={() => chooseChapter(c.index)}
                  >
                    <span>{c.name}</span>
                  </button>
                ))}
              </nav>
              <div className="tome-stack tome-stack--l" aria-hidden="true" />
              <div className="tome-stack tome-stack--r" aria-hidden="true" />
              <div className="tome-pages" onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={onPointerUp} onPointerCancel={onPointerUp}>
                {wide || view === "index" ? (
                  <section className="tome-page tome-page--l" aria-label={t.index}>
                    {shownLeft}
                  </section>
                ) : null}
                {wide || view === "blueprint" ? (
                  <section className="tome-page tome-page--r" aria-label={t.blueprint} aria-live="polite">
                    {wide ? shownRight : liveRight}
                  </section>
                ) : null}
                {plan !== null ? <FlipLayer key={plan.id} ref={flipRef} plan={plan} onDone={finish} /> : null}
              </div>
              <div className="tome-foot">
                <button
                  type="button"
                  className="ac-iconbtn tome-turn"
                  onClick={() => (!wide && view === "blueprint" ? stepItem(-1) : turn(-1))}
                  disabled={plan !== null || (!wide && view === "blueprint" ? idxInPage <= 0 : atStart)}
                  aria-label={t.prev}
                >
                  ‹
                </button>
                <span className="tome-folio ac-small" aria-live="polite">
                  {folio}
                </span>
                <button
                  type="button"
                  className="ac-iconbtn tome-turn"
                  onClick={() => (!wide && view === "blueprint" ? stepItem(1) : turn(1))}
                  disabled={plan !== null || (!wide && view === "blueprint" ? idxInPage >= ids.length - 1 : atEnd)}
                  aria-label={t.next}
                >
                  ›
                </button>
              </div>
            </div>
          </div>
          <p className="ac-small tome-hint">{t.turnHint}</p>
        </div>

        <aside className={`tome-stage-col${wide ? "" : " is-narrow"}`}>
          {!wide ? (
            <button type="button" className="ac-btn ac-btn--ghost ac-btn--small tome-stage-toggle" aria-expanded={stageOpen} onClick={() => setStageOpen((v) => !v)}>
              {stageOpen ? t.hide3d : t.show3d}
            </button>
          ) : null}
          <VoxelItemStage
            item={item ?? { id: "", name: "", icon: null, kind: "none" }}
            ingredients={item ? ingredients : []}
            layout={layout}
            station={stationPlate}
            accent={accent}
            playKey={item ? playKey : 0}
            reduced={reduced}
            labels={stageLabels}
            collapsed={!wide && !stageOpen}
          />
        </aside>
      </div>

      <RecipeCommandBar
        open={cmdOpen}
        query={draft}
        onQuery={setDraft}
        results={cmdResults}
        total={cmdIds.length}
        onPick={pickCmd}
        onClose={closeCmd}
        title={t.commandTitle}
        placeholder={labels.search}
        closeLabel={t.clear}
        countLabel={t.itemWord}
        emptyLabel={labels.empty}
      />
    </div>
  );
}
