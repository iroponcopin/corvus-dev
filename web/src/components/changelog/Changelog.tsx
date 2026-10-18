"use client";

import { useEffect, useMemo, useState } from "react";
import { chime } from "@/engine/audio";
import type { ChangelogBrand, ChangelogLabels, Release } from "@/lib/wiki-types";
import { BrandStage } from "../BrandStage";
import { Icon } from "../Icon";
import { Rich } from "../Rich";

const BRANDS = ["all", "halia", "ouka", "astraea", "cherry", "tsubomi", "aureum", "alpha", "corvus"] as const;
const COLLAPSE_AFTER = 8;

/**
 * The update history of every model, as the pre-4.0 portal behaved: `?model=` is read once on
 * mount (an old `?brand=` link still works, and is rewritten) and chip clicks rewrite it in
 * place; free-text search over every field; a series
 * (major.minor) select; the first eight rows until "Show more"; "Updated" is the newest date
 * among the current matches. Every row stays in the DOM — filtering only hides.
 */
export function Changelog({
  brands,
  labels,
  noteBrands,
}: {
  brands: ChangelogBrand[];
  labels: ChangelogLabels;
  noteBrands: string[];
}) {
  const [brand, setBrand] = useState<string>("all");
  const [query, setQuery] = useState("");
  const [series, setSeries] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [open, setOpen] = useState<Set<string>>(() => new Set());

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const b = params.get("model") ?? params.get("brand");
    if (b !== null && (BRANDS as readonly string[]).includes(b)) setBrand(b);
    if (params.has("brand")) {
      // The links before 4.2.2 said ?brand=; the address bar says ?model= from here on.
      const url = new URL(window.location.href);
      url.searchParams.delete("brand");
      if (b !== null && b !== "all" && (BRANDS as readonly string[]).includes(b)) url.searchParams.set("model", b);
      window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
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
  const counts = useMemo(() => {
    const c: Record<string, number> = { all: all.length };
    for (const b of brands) c[b.id] = b.releases.length;
    return c;
  }, [all, brands]);

  const inBrand = useMemo(() => all.filter((r) => brand === "all" || r.brand === brand), [all, brand]);
  const seriesOptions = useMemo(() => Array.from(new Set(inBrand.map((r) => r.series))), [inBrand]);
  const q = query.trim().toLowerCase();
  const matches = useMemo(
    () =>
      inBrand.filter((r) => {
        if (series !== "" && r.series !== series) return false;
        if (q === "") return true;
        const hay = [r.version, r.title, r.summary, ...r.highlights, ...r.balance, ...r.warnings, ...r.limits, ...(r.paragraphs ?? []), r.brand]
          .join("\n")
          .toLowerCase();
        return hay.includes(q);
      }),
    [inBrand, series, q],
  );
  const capped = !(q !== "" || series !== "" || expanded || !(matches.length > COLLAPSE_AFTER));
  const visible = new Set((capped ? matches.slice(0, COLLAPSE_AFTER) : matches).map((r) => r.id));
  const newest = matches.reduce<string>((m, r) => (r.date !== null && r.date > m ? r.date : m), "");

  const choose = (b: string): void => {
    setBrand(b);
    setSeries("");
    chime("tick");
    const url = new URL(window.location.href);
    if (b === "all") url.searchParams.delete("model");
    else url.searchParams.set("model", b);
    window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
  };

  const toggle = (id: string): void =>
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  const icon = brand === "all" || brand === "corvus" ? "icons/store.png" : `icons/${brand}.png`;

  return (
    <div className="ac-cl">
      <div className="ac-cl-tools">
        <div className="ac-cl-chips" role="group" aria-label={labels.brand}>
          {BRANDS.filter((b) => b === "all" || counts[b] !== undefined).map((b) => (
            <button key={b} type="button" className="ac-chip" aria-pressed={brand === b} onClick={() => choose(b)}>
              {b === "all" ? labels.all : names[b]}
              <span className="ac-count">{counts[b] ?? 0}</span>
            </button>
          ))}
        </div>
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
          {brand === "all" || noteBrands.includes(brand) ? <p className="ac-small ac-cl-note">{labels.note}</p> : null}
          {brand === "corvus" ? (
            <p className="ac-small ac-cl-note" lang="en" data-note-lang="en">
              {labels.corvusNote}
            </p>
          ) : null}
        </div>
        <div className="ac-cl-plate">
          <BrandStage key={icon} icon={icon} label="" dim={brand === "alpha"} />
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
