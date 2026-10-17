"use client";

import Link from "next/link";
import { Fragment, type ReactNode, useEffect, useMemo, useRef, useState } from "react";
import { chime } from "@/engine/audio";
import type { Fresh } from "@/i18n/fresh";
import { asset } from "@/lib/site";
import { Icon } from "../Icon";
import { scrollToY } from "../SmoothScroll";

export interface ReelTeaser {
  id: string;
  brand: string;
  name: string;
  icon: string;
  color: string;
  announced: string;
  retired: string | null;
  title: string;
  subtitle: string;
  target: string;
  body: string;
  items: string[];
  pageHref: string;
  notesHref: string;
}

type Labels = Fresh["teasers"];
type Scene = { kind: "title" } | { kind: "body" } | { kind: "item"; n: number } | { kind: "end" };

function scenesOf(t: ReelTeaser): Scene[] {
  return [{ kind: "title" }, { kind: "body" }, ...t.items.map((_, n): Scene => ({ kind: "item", n })), { kind: "end" }];
}

/** How long a scene stays up: long enough to read it at a calm pace (density weighs dense scripts). */
function durationOf(t: ReelTeaser, s: Scene, density: number): number {
  const reading = (text: string): number => text.length * density;
  switch (s.kind) {
    case "title":
      return 3400 + Math.min(2400, reading(t.title + t.subtitle) * 18);
    case "body":
      return Math.min(11000, Math.max(3600, 1800 + reading(t.body) * 34));
    case "item":
      return Math.min(9000, Math.max(3200, 1600 + reading(t.items[s.n] ?? "") * 30));
    case "end":
      return 4200;
  }
}

/** A label with a date in it ("Announced {0}"): the date reads left to right in every language. */
function withDate(template: string, date: string): ReactNode {
  const [before = "", after = ""] = template.split("{0}");
  return (
    <>
      {before}
      <span dir="ltr" className="ac-ltr">
        {date}
      </span>
      {after}
    </>
  );
}

const norm = (s: string): string => s.normalize("NFKC").toLowerCase();

/**
 * The teaser player and the archive under it. A teaser plays as it was told: its name, the
 * announcement, one scene for each thing it promised, and an end card that says whether it
 * shipped and where to read about it. One timeout per scene drives it (never the frame loop); the
 * progress bar is a CSS animation of the same length.
 */
export function TeaserReel({
  teasers,
  labels,
  density,
  arrow,
}: {
  teasers: ReelTeaser[];
  labels: Labels;
  density: number;
  /** The "go there" arrow for the page's direction (→, or ← in Arabic). */
  arrow: string;
}) {
  const [current, setCurrent] = useState(0);
  const [scene, setScene] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [all, setAll] = useState(false);
  const [brand, setBrand] = useState("all");
  const [query, setQuery] = useState("");
  const [open, setOpen] = useState<string | null>(null);
  const stage = useRef<HTMLDivElement>(null);

  const t = teasers[current];
  const scenes = useMemo(() => (t ? scenesOf(t) : []), [t]);
  const active = scenes[scene] ?? scenes[0];
  const duration = t && active ? durationOf(t, active, density) : 0;

  // The clock: the next scene, the next teaser (when playing them all), or a stop at the end card.
  useEffect(() => {
    if (!playing || duration === 0) return;
    const id = window.setTimeout(() => {
      if (scene < scenes.length - 1) setScene(scene + 1);
      else if (all && current < teasers.length - 1) {
        setCurrent(current + 1);
        setScene(0);
      } else setPlaying(false);
    }, duration);
    return () => window.clearTimeout(id);
  }, [playing, scene, current, all, duration, scenes.length, teasers.length]);

  // Each scene lands with a little light, and a tick when the sound is on.
  useEffect(() => {
    if (!playing) return;
    chime("tick");
  }, [playing, scene, current]);

  const brands = useMemo(() => {
    const seen = new Map<string, string>();
    for (const x of teasers) if (!seen.has(x.brand)) seen.set(x.brand, x.name);
    return [...seen.entries()];
  }, [teasers]);
  const visible = useMemo(() => {
    const q = norm(query.trim());
    return teasers
      .map((x, i) => ({ x, i }))
      .filter(({ x }) => brand === "all" || x.brand === brand)
      .filter(({ x }) => q === "" || norm([x.name, x.title, x.subtitle, x.body, ...x.items].join(" ")).includes(q));
  }, [teasers, brand, query]);

  if (t === undefined || active === undefined) return <p className="ac-wrap ac-small">{labels.empty}</p>;

  const goto = (i: number, start: boolean): void => {
    setCurrent(i);
    setScene(0);
    setPlaying(start);
  };
  const playFrom = (i: number): void => {
    goto(i, true);
    const el = stage.current;
    if (el !== null) scrollToY(Math.max(0, el.getBoundingClientRect().top + window.scrollY - 96));
  };
  const toggle = (): void => {
    if (playing) setPlaying(false);
    else {
      if (scene === scenes.length - 1) setScene(0);
      setPlaying(true);
    }
  };
  const step = (by: number): void => {
    setScene((s) => Math.min(scenes.length - 1, Math.max(0, s + by)));
  };

  return (
    <div className="ac-teasers">
      <div
        ref={stage}
        className="ac-wrap ac-reel-wrap"
        role="region"
        aria-roledescription="carousel"
        aria-label={labels.player}
      >
        <div
          className="ac-reel"
          style={{ "--tint": t.color } as React.CSSProperties}
          data-playing={playing}
          tabIndex={0}
          onKeyDown={(e) => {
            const rtl = getComputedStyle(e.currentTarget).direction === "rtl";
            if (e.key === " " || e.key === "k") {
              e.preventDefault();
              toggle();
            } else if (e.key === "ArrowRight") step(rtl ? -1 : 1);
            else if (e.key === "ArrowLeft") step(rtl ? 1 : -1);
          }}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="ac-reel-mark" src={asset(t.icon)} alt="" width={320} height={320} />
          <div className="ac-reel-head">
            <span className="ac-reel-brand">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset(t.icon)} alt="" width={28} height={28} />
              {t.name}
            </span>
            <span className="ac-reel-date">{withDate(labels.announced, t.announced)}</span>
          </div>

          <div className="ac-reel-scenes">
            <section className="ac-reel-scene ac-reel-title" data-active={active.kind === "title"} aria-hidden={active.kind !== "title"}>
              {/* auto: a Latin name keeps its word order on an Arabic page (each word is its own box). */}
              <h2 dir="auto">
                {t.title.split(" ").map((w, i) => (
                  // The space stays outside the word: an inline-block drops its own trailing space.
                  <Fragment key={i}>
                    <span className="ac-reel-word" style={{ "--i": i } as React.CSSProperties}>
                      {w}
                    </span>{" "}
                  </Fragment>
                ))}
              </h2>
              {t.subtitle ? <p>{t.subtitle}</p> : null}
            </section>
            <section className="ac-reel-scene ac-reel-body" data-active={active.kind === "body"} aria-hidden={active.kind !== "body"}>
              <p>{t.body}</p>
            </section>
            {t.items.map((item, n) => {
              const on = active.kind === "item" && active.n === n;
              return (
                <section key={n} className="ac-reel-scene ac-reel-item" data-active={on} aria-hidden={!on}>
                  <span className="ac-reel-count" dir="ltr">
                    {String(n + 1).padStart(2, "0")} / {String(t.items.length).padStart(2, "0")}
                  </span>
                  <p>{item}</p>
                </section>
              );
            })}
            <section className="ac-reel-scene ac-reel-end" data-active={active.kind === "end"} aria-hidden={active.kind !== "end"}>
              <p className="ac-reel-target">{t.target}</p>
              <p className="ac-reel-status" data-shipped={t.retired !== null}>
                {t.retired !== null ? withDate(labels.shipped, t.retired) : labels.onBoard}
              </p>
              <div className="ac-reel-links">
                <Link className="ac-btn ac-btn--small" href={t.notesHref} tabIndex={active.kind === "end" ? 0 : -1}>
                  {labels.releaseNotes}
                </Link>
                <Link className="ac-btn ac-btn--ghost ac-btn--small" href={t.pageHref} tabIndex={active.kind === "end" ? 0 : -1}>
                  {t.name}
                </Link>
              </div>
            </section>
          </div>

          <p className="sr-only" aria-live={playing ? "polite" : "off"}>
            {active.kind === "title"
              ? `${t.title}. ${t.subtitle}`
              : active.kind === "body"
                ? t.body
                : active.kind === "item"
                  ? t.items[active.n]
                  : `${t.target}. ${t.retired !== null ? labels.shipped.replace("{0}", t.retired) : labels.onBoard}`}
          </p>

          <div className="ac-reel-bar">
            {scenes.map((_, n) => (
              <button
                key={n}
                type="button"
                className="ac-reel-seg"
                data-state={n < scene ? "done" : n === scene ? "now" : "next"}
                aria-label={`${n + 1} / ${scenes.length}`}
                aria-current={n === scene ? "step" : undefined}
                onClick={() => setScene(n)}
              >
                {n === scene ? (
                  <i key={`${current}-${scene}-${playing}`} data-run={playing} style={{ animationDuration: `${duration}ms` }} />
                ) : null}
              </button>
            ))}
          </div>
        </div>

        <div className="ac-reel-controls">
          <button type="button" className="ac-iconbtn" aria-label={labels.prev} title={labels.prev} disabled={current === 0} onClick={() => goto(current - 1, playing)}>
            <Icon name="skipBack" size={17} />
          </button>
          <button type="button" className="ac-reel-play" onClick={toggle} aria-pressed={playing}>
            <Icon name={playing ? "pause" : "play"} size={18} />
            <span>{playing ? labels.pause : labels.play}</span>
          </button>
          <button
            type="button"
            className="ac-iconbtn"
            aria-label={labels.next}
            title={labels.next}
            disabled={current === teasers.length - 1}
            onClick={() => goto(current + 1, playing)}
          >
            <Icon name="skipForward" size={17} />
          </button>
          <button type="button" className="ac-chip" onClick={() => goto(current, true)}>
            <Icon name="rotate" size={14} />
            {labels.replay}
          </button>
          <button
            type="button"
            className="ac-chip"
            aria-pressed={all}
            onClick={() => {
              setAll((v) => !v);
              if (!all && !playing) setPlaying(true);
            }}
          >
            <Icon name="repeat" size={14} />
            {labels.playAll}
          </button>
        </div>
      </div>

      <div className="ac-wrap ac-teaser-tools">
        <div className="ac-chips" role="group" aria-label={labels.title}>
          <button type="button" className="ac-chip" aria-pressed={brand === "all"} onClick={() => setBrand("all")}>
            {labels.all}
          </button>
          {brands.map(([id, name]) => (
            <button key={id} type="button" className="ac-chip" aria-pressed={brand === id} onClick={() => setBrand(id)}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset(`icons/${id}.png`)} alt="" width={18} height={18} />
              {name}
            </button>
          ))}
        </div>
        <label className="ac-teaser-search">
          <Icon name="search" size={15} />
          <input type="search" value={query} placeholder={labels.search} aria-label={labels.search} onChange={(e) => setQuery(e.target.value)} />
        </label>
      </div>

      <ol className="ac-wrap ac-teaser-list">
        {visible.length === 0 ? <li className="ac-small">{labels.empty}</li> : null}
        {visible.map(({ x, i }) => {
          const isOpen = open === x.id;
          return (
            <li key={x.id} className="ac-teaser-card ac-card" data-current={i === current} style={{ "--tint": x.color } as React.CSSProperties}>
              <div className="ac-teaser-top">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={asset(x.icon)} alt="" width={44} height={44} />
                <div>
                  <p className="ac-eyebrow">
                    {x.name} · {withDate(labels.announced, x.announced)}
                  </p>
                  <h3>{x.title}</h3>
                  {x.subtitle ? <p className="ac-teaser-sub">{x.subtitle}</p> : null}
                </div>
                <span className="ac-teaser-status" data-shipped={x.retired !== null}>
                  {x.retired !== null ? withDate(labels.shipped, x.retired) : labels.onBoard}
                </span>
              </div>
              <p className="ac-teaser-body">{x.body}</p>
              {isOpen ? (
                <div className="ac-teaser-more" id={`teaser-${x.id}`}>
                  <ul>
                    {x.items.map((item, n) => (
                      <li key={n}>{item}</li>
                    ))}
                  </ul>
                  <p className="ac-small">{x.target}</p>
                  <p className="ac-teaser-links">
                    <Link className="ac-link" href={x.notesHref}>
                      {labels.releaseNotes} <span aria-hidden="true">{arrow}</span>
                    </Link>
                    <Link className="ac-link" href={x.pageHref}>
                      {x.name} <span aria-hidden="true">{arrow}</span>
                    </Link>
                  </p>
                </div>
              ) : null}
              <div className="ac-teaser-actions">
                <button type="button" className="ac-btn ac-btn--small" onClick={() => playFrom(i)}>
                  <Icon name="play" size={14} />
                  {labels.play}
                </button>
                <button
                  type="button"
                  className="ac-btn ac-btn--ghost ac-btn--small"
                  aria-expanded={isOpen}
                  aria-controls={`teaser-${x.id}`}
                  onClick={() => setOpen(isOpen ? null : x.id)}
                >
                  {isOpen ? labels.hide : labels.read}
                </button>
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
