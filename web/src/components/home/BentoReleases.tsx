"use client";

import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { fetchFeed } from "@/lib/feeds";
import { asset } from "@/lib/site";
import { Rich } from "../Rich";

export interface BentoEntry {
  version: string;
  date: string | null;
  title: string;
  summary: string;
  paragraphs: string[];
  highlights: string[];
  warnings: string[];
}

export interface BentoItem {
  key: string;
  /** The key in glimpse_manifest.json whose `latest` the pill reads. */
  manifest: string;
  name: string;
  icon: string;
  color: string;
  size: "xl" | "l" | "m";
  /** The version the page was built with; the pill shows the manifest's value once it has loaded. */
  version: string;
  entry: BentoEntry;
  href: string;
  changelogHref: string;
}

export interface BentoLabels {
  title: string;
  lede: string;
  open: string;
  close: string;
  modal: string;
  pill: string;
}

/**
 * The latest releases of the live models, as a Bento grid of tiles with mixed sizes. Each pill shows
 * the version the feed publishes (glimpse_manifest.json), so it is current the moment the feed answers;
 * the build-time version is what shows before that, and what stays if the feed does not answer. A tile
 * opens its changelog entry in a native modal dialog, which traps focus, closes on Esc, and hands focus
 * back to the tile.
 */
export function BentoReleases({ items, labels }: { items: BentoItem[]; labels: BentoLabels }) {
  const [latest, setLatest] = useState<Record<string, string>>({});
  const [open, setOpen] = useState<BentoItem | null>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLElement | null>(null);

  useEffect(() => {
    const ac = new AbortController();
    void fetchFeed("glimpse_manifest.json", { body: true, attempts: 2, signal: ac.signal }).then((r) => {
      if (r.text === null) return;
      try {
        const m = JSON.parse(r.text) as Record<string, { latest?: unknown }>;
        const next: Record<string, string> = {};
        for (const [k, v] of Object.entries(m)) if (typeof v?.latest === "string") next[k] = v.latest;
        setLatest(next);
      } catch {
        // A feed that is not JSON leaves the build-time versions in place.
      }
    });
    return () => ac.abort();
  }, []);

  useEffect(() => {
    const d = dialog.current;
    if (d === null) return;
    if (open !== null && !d.open) d.showModal();
    if (open === null && d.open) d.close();
  }, [open]);

  const pillFor = (x: BentoItem): string => {
    const v = latest[x.manifest];
    if (v === undefined) return x.version;
    return x.version.startsWith("V") ? `V${v}` : v;
  };

  const show = (x: BentoItem, el: HTMLElement) => {
    trigger.current = el;
    setOpen(x);
  };

  const close = () => dialog.current?.close();

  return (
    <div className="ac-bento-wrap">
      <ul className="ac-bento">
        {items.map((x) => (
          <li key={x.key} className="ac-bento-cell" data-size={x.size}>
            <button
              type="button"
              className="ac-bento-tile"
              data-model={x.key}
              style={{ "--accent": x.color } as React.CSSProperties}
              onClick={(e) => show(x, e.currentTarget)}
              onPointerMove={(e) => {
                const r = e.currentTarget.getBoundingClientRect();
                e.currentTarget.style.setProperty("--mx", `${e.clientX - r.left}px`);
                e.currentTarget.style.setProperty("--my", `${e.clientY - r.top}px`);
              }}
            >
              <span className="ac-bento-top">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={asset(x.icon)} alt="" width={44} height={44} />
                <span className="ac-bento-name">{x.name}</span>
                <span className="ac-bento-pill ac-ltr" data-state={latest[x.manifest] === undefined ? "build" : "live"}>
                  {pillFor(x)}
                </span>
              </span>
              <span className="ac-bento-title">
                <Rich text={x.entry.title} />
              </span>
              {x.size !== "m" ? <span className="ac-bento-summary">{x.entry.summary}</span> : null}
              <span className="ac-link" aria-hidden="true">
                {labels.open}
              </span>
            </button>
          </li>
        ))}
      </ul>

      <dialog
        ref={dialog}
        className="ac-bento-dialog"
        aria-labelledby="ac-bento-dlg-title"
        onClose={() => {
          setOpen(null);
          trigger.current?.focus();
        }}
        onClick={(e) => {
          if (e.target === e.currentTarget) close();
        }}
      >
        {open !== null ? (
          <article className="ac-bento-sheet" style={{ "--accent": open.color } as React.CSSProperties}>
            <header>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset(open.icon)} alt="" width={52} height={52} />
              <div>
                <p className="ac-eyebrow">
                  {labels.modal} · {open.name}
                </p>
                <h3 id="ac-bento-dlg-title">
                  <span className="ac-ltr">{open.entry.version}</span>
                  {open.entry.date ? (
                    <small className="ac-ltr">
                      {" · "}
                      {open.entry.date}
                    </small>
                  ) : null}
                </h3>
              </div>
              <button type="button" className="ac-btn ac-btn--ghost ac-btn--small" onClick={close} autoFocus>
                {labels.close}
              </button>
            </header>
            <p className="ac-bento-sheet-title">
              <Rich text={open.entry.title} />
            </p>
            {open.entry.summary ? (
              <p className="ac-cl-lede">
                <Rich text={open.entry.summary} />
              </p>
            ) : null}
            {open.entry.paragraphs.map((p, i) => (
              <p key={i} className="ac-cl-lede">
                <Rich text={p} />
              </p>
            ))}
            {open.entry.highlights.length > 0 ? (
              <ul className="ac-bento-list">
                {open.entry.highlights.slice(0, 6).map((h, i) => (
                  <li key={i}>
                    <Rich text={h} />
                  </li>
                ))}
              </ul>
            ) : null}
            {open.entry.warnings.length > 0 ? (
              <ul className="ac-bento-list ac-cl-warn">
                {open.entry.warnings.slice(0, 3).map((h, i) => (
                  <li key={i}>
                    <Rich text={h} />
                  </li>
                ))}
              </ul>
            ) : null}
            <p>
              <Link className="ac-link" href={open.changelogHref}>
                {labels.modal} <span className="ac-flip">→</span>
              </Link>
            </p>
          </article>
        ) : null}
      </dialog>
    </div>
  );
}
