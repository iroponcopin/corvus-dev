"use client";

import { type KeyboardEvent, useEffect, useId, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { recipeIcon } from "@/lib/site";
import { Icon } from "../Icon";

export interface CommandResult {
  id: string;
  name: string;
  sub?: string;
  icon: string | null;
  chapter: string;
}

/**
 * The spotlight: Ctrl K or ⌘K (or the engraved bar on the book) opens it. Results update as the reader types, the
 * first one is highlighted, Enter or a click opens its page in the book. It is a modal dialog: focus starts in the
 * field, Escape closes it and returns focus to the control that opened it.
 */
export function RecipeCommandBar({
  open,
  query,
  onQuery,
  results,
  total,
  onPick,
  onClose,
  title,
  placeholder,
  closeLabel,
  countLabel,
  emptyLabel,
}: {
  open: boolean;
  query: string;
  onQuery: (q: string) => void;
  results: CommandResult[];
  total: number;
  onPick: (id: string) => void;
  onClose: () => void;
  title: string;
  placeholder: string;
  closeLabel: string;
  countLabel: string;
  emptyLabel: string;
}) {
  const [active, setActive] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const listId = useId();
  const titleId = useId();

  useEffect(() => {
    if (open) {
      setActive(0);
      requestAnimationFrame(() => input.current?.focus());
    }
  }, [open]);

  useEffect(() => {
    setActive(0);
  }, [query]);

  useEffect(() => {
    const el = list.current?.querySelector<HTMLElement>(`[data-index="${active}"]`);
    el?.scrollIntoView({ block: "nearest" });
  }, [active]);

  if (!open) return null;

  const onKey = (e: KeyboardEvent<HTMLDivElement>): void => {
    if (e.key === "Escape") {
      e.preventDefault();
      onClose();
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(results.length - 1, a + 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(0, a - 1));
    } else if (e.key === "Enter") {
      const r = results[active];
      if (r) {
        e.preventDefault();
        onPick(r.id);
      }
    }
  };

  // Rendered at the body: the page's own stacking (the book, the header Dock) cannot sit above the spotlight.
  return createPortal(
    <div className="tome-cmd-scrim" onMouseDown={onClose}>
      <div className="tome-cmd" role="dialog" aria-modal="true" aria-labelledby={titleId} onMouseDown={(e) => e.stopPropagation()} onKeyDown={onKey}>
        <h2 id={titleId} className="sr-only">
          {title}
        </h2>
        <label className="tome-cmd-field">
          <Icon name="search" size={18} />
          <input
            ref={input}
            type="search"
            className="tome-cmd-input"
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-autocomplete="list"
            aria-activedescendant={results[active] ? `${listId}-${active}` : undefined}
            placeholder={placeholder}
            aria-label={placeholder}
            value={query}
            onChange={(e) => onQuery(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <button type="button" className="ac-iconbtn" onClick={onClose} aria-label={closeLabel} title={closeLabel}>
            <Icon name="x" size={15} />
          </button>
        </label>
        <p className="ac-small tome-cmd-count" aria-live="polite">
          {results.length} / {total} {countLabel}
        </p>
        {results.length === 0 ? <p className="ac-codex-empty">{emptyLabel}</p> : null}
        <ul id={listId} role="listbox" ref={list} className="tome-cmd-list" aria-label={title}>
          {results.map((r, i) => {
            const icon = recipeIcon(r.icon);
            return (
              <li
                key={r.id}
                id={`${listId}-${i}`}
                role="option"
                aria-selected={i === active}
                data-index={i}
                className="tome-cmd-item"
                onMouseEnter={() => setActive(i)}
                onClick={() => onPick(r.id)}
              >
                {icon ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={icon} alt="" width={28} height={28} className="ac-pixel" />
                ) : (
                  <span className="ac-noicon" aria-hidden="true">
                    ?
                  </span>
                )}
                <span className="tome-cmd-text">
                  <span dir="auto">{r.name}</span>
                  {r.sub ? (
                    <small lang="en" className="ac-small">
                      {r.sub}
                    </small>
                  ) : null}
                </span>
                <small className="tome-badge">{r.chapter}</small>
              </li>
            );
          })}
        </ul>
      </div>
    </div>
  , document.body);
}
