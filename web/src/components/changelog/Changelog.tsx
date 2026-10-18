"use client";

import { flushSync } from "react-dom";
import { useEffect, useMemo, useState } from "react";
import { chime } from "@/engine/audio";
import type { ChangelogBrand, ChangelogLabels, Release } from "@/lib/wiki-types";
import { BrandStage } from "../BrandStage";
import { Icon } from "../Icon";
import { Rich } from "../Rich";

/** The live models, in the order the chips show them. Corvus Store is the launcher's own feed. */
const LIVE = ["halia", "ouka", "cherry", "tsubomi", "aureum", "noctua", "corvus"] as const;
/** The models that have ended: they appear under the Ended filter only, never in All. */
const ENDED = ["astraea", "alpha"] as const;
const COLLAPSE_AFTER = 8;

type Filter = "all" | "ended" | string;

/** Runs a filter change inside a View Transition where the browser has one and motion is allowed. */
function transition(update: () => void): void {
  const doc = document as Document & { startViewTransition?: (cb: () => void) => unknown };
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reduced || typeof doc.startViewTransition !== "function") {
    update();
    return;
  }
  doc.startViewTransition(() => flushSync(update));
}

/**
 * The update history of every model. Glass filter bar: All (live models only), one chip per live
 * model, and an Ended chip whose sub-chips are the ended models. `?model=` and `#cl-p-<id>` deep
 * links are read on mount; chip clicks rewrite `?model=` in place. Free-text search over every
 * field; a series select; the first eight rows until "Show more". Every row stays in the DOM:
 * filtering only hides, so the list animates between states with a View Transition.
 */
export function Changelog({
  brands,
  labels,
  noteBrands,
  ui,
}: {
  brands: ChangelogBrand[];
  labels: ChangelogLabels;
  noteBrands: string[];
  ui: { ended: string; endedNote: string; filters: string };
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const [query, setQuery] = useState("");
  const [series, setSeries] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [open, setOpen] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const b = params.get("model") ?? params.get("brand");
    const known = (id: string): boolean => (LIVE as readonly string[]).includes(id) || (ENDED as readonly string[]).includes(id) || id === "ended";
    if (b !== null && known(b)) setFilter(b);
    if (params.has("brand")) {
      // The links before 4.2.2 said ?brand=; the address bar says ?model= from here on.
      const url = new URL(window.location.href);
      url.searchParams.delete("brand");
      if (b !== null && b !== "all" && known(b)) url.searchParams.set("model", b);
      window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
    }
    // A deep link from the palette (#cl-p-<release id>) opens that entry and brings it into view.
    const hash = decodeURIComponent(window.location.hash.slice(1));
    if (hash.startsWith("cl-p-")) {
      setOpen(new Set([hash.slice(5)]));
      window.setTimeout(() => document.getElementById(hash)?.closest("article")?.scrollIntoView({ block: "center" }), 0);
    }
  }, []);

  const names = useMemo(() => Object.fromEntries(brands.map((b) => [b.id, b.name])), [brands]);
  const all = useMemo(() => {
    const flat: Release[] = brands.flatMap((b) => b.releases);
    // Newest first; stable, so ties keep the brand order; undated (Corvus Store) rows go last.
    return flat
      .map((r, i) => ({ r, i }))
      .sort((a, b) => (b.r.date ?? "").localeCompare(a.r.date ?? "") || a.i - b.i)
      .map((x) => x.r);
  }, [brands]);

  const isEnded = (id: string): boolean => (ENDED as readonly string[]).includes(id);
  const liveChips = LIVE.filter((id) => brands.some((b) => b.id === id));
  const endedChips = ENDED.filter((id) => brands.some((b) => b.id === id));
  const counts = useMemo(() => {
    const c: Record<string, number> = {
      all: all.filter((r) => !isEnded(r.brand)).length,
      ended: all.filter((r) => isEnded(r.brand)).length,
    };
    for (const b of brands) c[b.id] = b.releases.length;
    return c;
  }, [all, brands]);

  const inFilter = useMemo(
    () =>
      all.filter((r) => {
        if (filter === "all") return !isEnded(r.brand);
        if (filter === "ended") return isEnded(r.brand);
        return r.brand === filter;
      }),
    [all, filter],
  );
  const seriesOptions = useMemo(() => Array.from(new Set(inFilter.map((r) => r.series))), [inFilter]);
  const q = query.trim().toLowerCase();
  const matches = useMemo(
    () =>
      inFilter.filter((r) => {
        if (series !== "" && r.series !== series) return false;
        if (q === "") return true;
        const hay = [r.version, r.title, r.summary, ...r.highlights, ...r.balance, ...r.warnings, ...r.limits, ...(r.paragraphs ?? []), r.brand]
          .join("\n")
          .toLowerCase();
        return hay.includes(q);
      }),
    [inFilter, series, q],
  );
  const capped = !(q !== "" || series !== "" || expanded || !(matches.length > COLLAPSE_AFTER));
  const visible = new Set((capped ? matches.slice(0, COLLAPSE_AFTER) : matches).map((r) => r.id));
  const newest = matches.reduce<string>((m, r) => (r.date !== null && r.date > m ? r.date : m), "");

  const choose = (f: Filter): void => {
    chime("tick");
    transition(() => {
      setFilter(f);
      setSeries("");
    });
    const url = new URL(window.location.href);
    if (f === "all") url.searchParams.delete("model");
    else url.searchParams.set("model", f);
    window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
  };

  const toggle = (id: string): void =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const endedActive = filter === "ended" || isEnded(filter);
  const icon = filter === "all" || filter === "corvus" ? "icons/store.png" : filter === "ended" ? "icons/alpha.png" : `icons/${filter}.png`;

  const chip = (id: Filter, label: string, count: number, group?: string) => (
    <button key={id} type="button" className="ac-chip ac-cl-chip" aria-pressed={filter === id} data-group={group} onClick={() => choose(id)}>
      {label}
      <span className="ac-count">{count}</span>
    </button>
  );

  return (
    <div className="ac-cl">
      <div className="ac-cl-bar" role="region" aria-label={ui.filters}>
        <div className="ac-cl-chips" role="group" aria-label={labels.brand}>
          {chip("all", labels.all, counts.all ?? 0)}
          {liveChips.map((id) => chip(id, names[id] ?? id, counts[id] ?? 0))}
          {endedChips.length > 0 ? chip("ended", ui.ended, counts.ended ?? 0, "ended") : null}
        </div>
        {endedActive ? (
          <div className="ac-cl-chips ac-cl-chips--sub" role="group" aria-label={ui.ended}>
            {endedChips.map((id) => chip(id, names[id] ?? id, counts[id] ?? 0, "ended"))}
          </div>
        ) : null}
        <div className="ac-cl-filters">
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
          <label className="ac-select">
            <span className="ac-small">{labels.series}</span>
            <select value={series} onChange={(e) => setSeries(e.target.value)}>
              <option value="">{labels.allSeries}</option>
              {seriesOptions.map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="ac-cl-head">
        <div>
          <p className="ac-small ac-cl-updated" aria-live="polite">
            {newest ? labels.updated.replace("{date}", newest) : ""}
          </p>
          {filter === "all" || noteBrands.includes(filter) ? <p className="ac-small ac-cl-note">{labels.note}</p> : null}
          {filter === "ended" ? <p className="ac-small ac-cl-note">{ui.endedNote}</p> : null}
          {filter === "corvus" ? (
            <p className="ac-small ac-cl-note" lang="en" data-note-lang="en">
              {labels.corvusNote}
            </p>
          ) : null}
        </div>
        <div className="ac-cl-plate">
          <BrandStage key={icon} icon={icon} label="" dim={endedActive} />
        </div>
      </div>

      <p className="ac-cl-empty" hidden={matches.length > 0}>
        {labels.empty}
      </p>

      <div className="ac-cl-list">
        {all.map((r) => {
          const isOpen = open.has(r.id);
          const corvus = r.brand === "corvus";
          const sections: [string, string[], boolean][] = [
            [labels.highlights, r.highlights, false],
            [labels.balance, r.balance, false],
            [labels.warnings, r.warnings, true],
            [labels.limits, r.limits, false],
          ];
          return (
            <article key={r.id} className="ac-cl-row ac-card" data-brand={r.brand} hidden={!visible.has(r.id)} data-open={isOpen}>
              <h3 className="ac-cl-h">
                <button type="button" aria-expanded={isOpen} aria-controls={`cl-p-${r.id}`} onClick={() => toggle(r.id)}>
                  <span className="ac-cl-brand" data-brand={r.brand}>
                    {names[r.brand]}
                  </span>
                  <span className="ac-cl-ver ac-ltr">{r.version}</span>
                  <span className="ac-cl-title" lang={corvus ? "en" : undefined}>
                    <Rich text={r.title} />
                  </span>
                  <span className="ac-cl-date ac-ltr">{r.date ?? labels.none}</span>
                  <Icon name="chevronDown" size={16} className="ac-cl-chev" />
                </button>
              </h3>
              <div className="ac-cl-detail" id={`cl-p-${r.id}`} data-panel={r.id} hidden={!isOpen} lang={corvus ? "en" : undefined}>
                <span className="ac-tag">{labels.types[r.type] ?? r.type}</span>
                {r.summary ? (
                  <p className="ac-cl-lede">
                    <Rich text={r.summary} />
                  </p>
                ) : null}
                {(r.paragraphs ?? []).map((p, i) => (
                  <p key={i} className="ac-cl-lede">
                    <Rich text={p} />
                  </p>
                ))}
                {sections.map(([title, items, warn]) =>
                  items.length > 0 ? (
                    <div key={title} className="ac-cl-section">
                      <h4>
                        {title} <span>({items.length})</span>
                      </h4>
                      <ul className={warn ? "ac-cl-warn" : undefined}>
                        {items.map((it, i) => (
                          <li key={i}>
                            <Rich text={it} />
                          </li>
                        ))}
                      </ul>
                    </div>
                  ) : null,
                )}
              </div>
            </article>
          );
        })}
      </div>

      {matches.length > COLLAPSE_AFTER && q === "" && series === "" ? (
        <button type="button" className="ac-btn ac-btn--ghost ac-cl-more" onClick={() => setExpanded((v) => !v)} data-more={labels.showMore} data-less={labels.showFewer}>
          {expanded ? labels.showFewer : labels.showMore}
        </button>
      ) : null}
    </div>
  );
}
