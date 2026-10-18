"use client";

import { useEffect, useId, useMemo, useRef, useState, type KeyboardEvent as ReactKeyboardEvent } from "react";
import { asset, BASE_PATH, pathOf } from "@/lib/site";
import type { Lang } from "@/lib/wiki-types";
import type { Shell } from "@/i18n/shell";
import { PALETTE_OPEN_EVENT } from "./event";

/** One line of the search index (portal/search/<lang>.json, written by scripts/prepare-public.mjs). */
interface IndexModel {
  id: string;
  name: string;
  href: string;
  archived: boolean;
}
interface IndexChangelog {
  id: string;
  model: string;
  title: string;
  version: string;
  date: string;
  href: string;
}
interface IndexRecipe {
  id: string;
  name: string;
  href: string;
}
interface SearchIndex {
  models: IndexModel[];
  changelog: IndexChangelog[];
  recipes: IndexRecipe[];
}

type Option =
  | { kind: "models"; key: string; label: string; sub: string; href: string }
  | { kind: "changelog"; key: string; label: string; sub: string; href: string; model: string }
  | { kind: "recipes"; key: string; label: string; sub: string; href: string };

const GROUP_LIMIT = 8;
const norm = (s: string): string => s.normalize("NFKC").toLowerCase().trim();

/**
 * The Cmd/Ctrl+K palette: one search over the seven models, the changelog entries of the live models, and the
 * recipe results. The index is fetched on first open, never inlined into a page. Arrow keys move, Enter opens,
 * Escape closes; the page the palette opened from gets focus back. A selection is a full page load to the target
 * (a deep link reads its hash on mount), so the destination never depends on what the page did before.
 */
export function Palette({
  lang,
  labels,
  modelLabels,
}: {
  lang: Lang;
  labels: Shell["palette"];
  modelLabels: Record<string, string>;
}) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [index, setIndex] = useState<SearchIndex | null>(null);
  const [failed, setFailed] = useState(false);
  const [active, setActive] = useState(0);
  const returnTo = useRef<HTMLElement | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const uid = useId();

  // Cmd/Ctrl+K toggles the palette; the Dock's search button and any other control use the same event.
  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if ((e.metaKey || e.ctrlKey) && !e.shiftKey && !e.altKey && e.key.toLowerCase() === "k") {
        e.preventDefault();
        setOpen((v) => !v);
      } else if (e.key === "Escape") {
        setOpen(false);
      }
    };
    const onOpen = (): void => setOpen(true);
    document.addEventListener("keydown", onKey);
    window.addEventListener(PALETTE_OPEN_EVENT, onOpen);
    return () => {
      document.removeEventListener("keydown", onKey);
      window.removeEventListener(PALETTE_OPEN_EVENT, onOpen);
    };
  }, []);

  // Open: remember where focus was, load the index once, focus the field. Close: give focus back.
  useEffect(() => {
    if (open) {
      returnTo.current = document.activeElement instanceof HTMLElement ? document.activeElement : null;
      document.documentElement.style.overflow = "hidden";
      if (index === null && !failed) {
        fetch(asset(`search/${lang}.json`))
          .then((r) => {
            if (!r.ok) throw new Error(String(r.status));
            return r.json() as Promise<SearchIndex>;
          })
          .then(setIndex)
          .catch(() => setFailed(true));
      }
      const id = window.setTimeout(() => inputRef.current?.focus(), 0);
      return () => window.clearTimeout(id);
    }
    document.documentElement.style.overflow = "";
    returnTo.current?.focus?.();
    returnTo.current = null;
    return undefined;
    // The index is keyed by the language; a language change is a page load, so this runs once per open.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const options = useMemo<Option[]>(() => {
    if (index === null) return [];
    const q = norm(query);
    const modelOpts: Option[] = index.models
      .filter((m) => q === "" || norm(`${m.name} ${m.id}`).includes(q))
      .map((m) => ({ kind: "models", key: `m-${m.id}`, label: m.name, sub: m.archived ? "" : (modelLabels[m.id] ?? ""), href: m.href }));
    const clOpts: Option[] = [];
    if (q !== "") {
      for (const c of index.changelog) {
        if (clOpts.length >= GROUP_LIMIT) break;
        if (!norm(`${c.title} ${c.version} ${c.model}`).includes(q)) continue;
        clOpts.push({ kind: "changelog", key: `c-${c.id}`, label: c.title, sub: `${c.version} · ${c.date}`, href: c.href, model: c.model });
      }
    }
    const rcOpts: Option[] = [];
    if (q !== "") {
      for (const r of index.recipes) {
        if (rcOpts.length >= GROUP_LIMIT) break;
        if (!norm(`${r.name} ${r.id}`).includes(q)) continue;
        rcOpts.push({ kind: "recipes", key: `r-${r.id}`, label: r.name, sub: r.id.split(":")[0] ?? "", href: r.href });
      }
    }
    return [...modelOpts, ...clOpts, ...rcOpts];
  }, [index, query, modelLabels]);

  useEffect(() => setActive(0), [query, index]);

  const choose = (o: Option | undefined): void => {
    if (!o) return;
    setOpen(false);
    window.location.assign(`${BASE_PATH}${pathOf(lang, o.href)}`);
  };

  const onInputKey = (e: ReactKeyboardEvent<HTMLInputElement>): void => {
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      if (options.length === 0) return;
      setActive((i) => (i + (e.key === "ArrowDown" ? 1 : -1) + options.length) % options.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      choose(options[active]);
    }
  };

  if (!open) return null;

  const groups: { kind: Option["kind"]; title: string }[] = [
    { kind: "models", title: labels.models },
    { kind: "changelog", title: labels.changelog },
    { kind: "recipes", title: labels.recipes },
  ];
  const listId = `${uid}-list`;

  return (
    <div className="ac-pal" role="presentation" onMouseDown={(e) => e.target === e.currentTarget && setOpen(false)}>
      <div className="ac-pal-panel ac-glass" role="dialog" aria-modal="true" aria-label={labels.open}>
        <div className="ac-pal-field">
          <svg className="ac-pal-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden="true">
            <circle cx="11" cy="11" r="7" />
            <path d="M21 21l-4.3-4.3" />
          </svg>
          <input
            ref={inputRef}
            type="search"
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={options[active] ? `${uid}-${active}` : undefined}
            aria-label={labels.label}
            placeholder={labels.placeholder}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onInputKey}
            autoComplete="off"
            spellCheck={false}
            className="ac-pal-input"
          />
          <kbd className="ac-pal-esc" aria-label={labels.close}>
            Esc
          </kbd>
        </div>

        <div id={listId} role="listbox" aria-label={labels.results} className="ac-pal-list">
          {failed ? <p className="ac-pal-empty">{labels.empty}</p> : null}
          {!failed && index !== null && options.length === 0 ? <p className="ac-pal-empty">{labels.empty}</p> : null}
          {groups.map((g) => {
            const items = options.map((o, i) => ({ o, i })).filter(({ o }) => o.kind === g.kind);
            if (items.length === 0) return null;
            return (
              <div key={g.kind} role="group" aria-label={g.title} className="ac-pal-group">
                <p className="ac-pal-head" aria-hidden="true">
                  {g.title}
                </p>
                {items.map(({ o, i }) => (
                  <div
                    key={o.key}
                    id={`${uid}-${i}`}
                    role="option"
                    aria-selected={i === active}
                    data-model={o.kind === "changelog" ? o.model : o.kind === "models" ? o.key.slice(2) : undefined}
                    data-active={i === active ? "true" : "false"}
                    className="ac-pal-item"
                    onMouseEnter={() => setActive(i)}
                    onClick={() => choose(o)}
                  >
                    <span className="ac-pal-dot" aria-hidden="true" />
                    <span className="ac-pal-text">
                      <b>{o.label}</b>
                      {o.sub ? <small>{o.sub}</small> : null}
                    </span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>

        <p className="ac-pal-foot">{labels.hint}</p>
      </div>
    </div>
  );
}
