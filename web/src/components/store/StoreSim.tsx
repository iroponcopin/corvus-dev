"use client";

import Link from "next/link";
import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { chime } from "@/engine/audio";
import { burst } from "@/engine/store";
import { asset } from "@/lib/site";
import type { Product, StoreText } from "@/lib/wiki-types";
import { Icon, type IconName } from "../Icon";
import { DownloadClock, RING_C, RING_R } from "./clock";

type Tab = "discover" | "mods" | "library" | "updates";
export type Phase = "get" | "downloading" | "open" | "update" | "soon" | "archived";

export interface AppState {
  phase: Phase;
  /** What a running download is for: a first install or an update. */
  target: "get" | "update" | null;
}

export interface StoreFresh {
  speed: string;
  timeLeft: string;
  perchDemo: string;
  perchFront: string;
  perchLeave: string;
  perchHidden: string;
  perchShown: string;
  nowPlaying: string;
}

export interface StoreSimLabels {
  text: StoreText;
  jar: Record<string, string>;
  perch: Record<string, string>;
  perchToggle: { title: string; description: string };
  fresh: StoreFresh;
  track: string;
}

export const DOWNLOAD_SECONDS = 3.6;
/** The real files' sizes (MB), so the simulated speed reads like the real thing. */
const SIZE_MB: Record<string, number> = { ouka: 4.7, cherry: 3.7, aureum: 0.03, astraea: 2.4, tsubomi: 1.9, halia: 10.2 };

export function fill(t: string, ...v: (string | number)[]): string {
  return t.replace(/\{(\d+)\}/g, (_, i: string) => String(v[Number(i)] ?? ""));
}

export function speedText(template: string, id: string): string {
  const speed = (SIZE_MB[id] ?? 2) / DOWNLOAD_SECONDS;
  return fill(template, speed >= 1 ? `${speed.toFixed(1)} MB` : `${Math.round(speed * 1024)} KB`);
}

function initial(products: Product[]): Record<string, AppState> {
  return Object.fromEntries(
    products.map((p) => [
      p.id,
      { phase: p.availability === "soon" ? "soon" : p.availability === "archived" ? "archived" : "get", target: null } satisfies AppState,
    ]),
  );
}

/** The App Store button: GET → a ring with a stop square → OPEN, or UPDATE. */
export function ActionButton({
  product,
  index,
  state,
  t,
  jar,
  clock,
  onPress,
  small = false,
}: {
  product: Product;
  index: number;
  state: AppState;
  t: StoreText;
  jar: Record<string, string>;
  clock: DownloadClock;
  onPress: () => void;
  small?: boolean;
}) {
  const label =
    state.phase === "get"
      ? t.get
      : state.phase === "open"
        ? t.open
        : state.phase === "update"
          ? t.update
          : state.phase === "soon"
            ? t.comingSoon
            : state.phase === "archived"
              ? t.archived
              : (jar["store.button.stop"] ?? t.stop);
  return (
    <button
      type="button"
      className={`ac-stb ${small ? "ac-stb--small" : ""}`}
      data-phase={state.phase}
      aria-disabled={state.phase === "soon" ? "true" : undefined}
      aria-label={`${label}: ${product.name}`}
      onClick={(e) => {
        e.stopPropagation();
        if (state.phase !== "soon") onPress();
      }}
    >
      {state.phase === "downloading" ? (
        <svg viewBox="0 0 28 28" width="28" height="28" aria-hidden="true">
          <circle cx="14" cy="14" r={RING_R} className="ac-stb-track" />
          <circle
            ref={(el) => (el ? clock.attachRing(index, el) : undefined)}
            cx="14"
            cy="14"
            r={RING_R}
            className="ac-stb-ring"
            strokeDasharray={RING_C}
            transform="rotate(-90 14 14)"
          />
          <rect x="10.5" y="10.5" width="7" height="7" rx="1.2" className="ac-stb-stop" />
        </svg>
      ) : (
        <span>{label}</span>
      )}
    </button>
  );
}

/** The speed and the seconds left of a running download; the seconds are written by the clock. */
export function DownloadLine({ name, speed, index, clock }: { name?: string; speed: string; index: number; clock: DownloadClock }) {
  return (
    <p className="ac-st-progress ac-ltr">
      {name ? `${name} · ` : ""}
      {speed} · <span ref={(el) => (el ? clock.attachClock(index, el) : undefined)} />
    </p>
  );
}

/**
 * Corvus Store 3.0, live in the page: Discover's big cards grow into their article (and back),
 * GET runs the App Store's download ring, Updates offers Update All at two or more, the
 * account sheet holds Automatic Updates and Perch, and Perch itself sits below the menu bar,
 * stepping aside while the player is in front. Everything is a simulation (nothing is
 * downloaded) and every string is the Store's own (its jar) or the site's.
 */
export function StoreSim({ products, labels, hrefs }: { products: Product[]; labels: StoreSimLabels; hrefs: Record<string, string> }) {
  const t = labels.text;
  const jar = labels.jar;
  const pl = labels.perch;
  const [tab, setTab] = useState<Tab>("discover");
  const [query, setQuery] = useState("");
  const [apps, setApps] = useState<Record<string, AppState>>(() => initial(products));
  const [article, setArticle] = useState<{ id: string; from: DOMRect | null } | null>(null);
  const [account, setAccount] = useState(false);
  const [auto, setAuto] = useState(true);
  const [perchOn, setPerchOn] = useState(true);
  const [playerFront, setPlayerFront] = useState(false);
  const [perchOpen, setPerchOpen] = useState(false);
  const [playing, setPlaying] = useState(true);
  const [shuffle, setShuffle] = useState(false);
  const [repeat, setRepeat] = useState(false);
  const [favourite, setFavourite] = useState(false);
  const [volume, setVolume] = useState(70);
  const [restart, setRestart] = useState(0);
  const [sheet, setSheet] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [announce, setAnnounce] = useState("");
  const [narrow, setNarrow] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  const main = useRef<HTMLDivElement>(null);
  const articleRef = useRef<HTMLDivElement>(null);
  const toastTimer = useRef<number | null>(null);
  const queued = useRef<number[]>([]);
  const byId = useMemo(() => Object.fromEntries(products.map((p) => [p.id, p])), [products]);
  const indexOf = useMemo(() => Object.fromEntries(products.map((p, i) => [p.id, i])), [products]);
  const [clock] = useState(() => new DownloadClock(products.length, DOWNLOAD_SECONDS));

  useEffect(() => {
    clock.setLeftTemplate(labels.fresh.timeLeft);
  }, [clock, labels.fresh.timeLeft]);

  // A download that completes: the clock calls this from the frame loop, once.
  useEffect(() => {
    clock.onDone = (i: number) => {
      const p = products[i];
      if (p === undefined) return;
      setApps((prev) => ({ ...prev, [p.id]: { phase: "open", target: null } }));
      setAnnounce(fill(t.announce.done, p.name));
      chime("done");
    };
    return () => {
      clock.onDone = () => {};
    };
  }, [clock, products, t.announce.done]);

  useEffect(() => {
    const timers = queued.current;
    return () => {
      clock.dispose();
      for (const id of timers) window.clearTimeout(id);
    };
  }, [clock]);

  useEffect(() => {
    const el = root.current;
    if (el === null) return;
    const ro = new ResizeObserver(([e]) => setNarrow((e?.contentRect.width ?? 900) < 640));
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const start = useCallback(
    (id: string, target: "get" | "update") => {
      const i = indexOf[id];
      if (i === undefined) return;
      clock.start(i);
      setApps((prev) => ({ ...prev, [id]: { phase: "downloading", target } }));
      setAnnounce(fill(t.announce.started, byId[id]?.name ?? id));
      chime("get");
    },
    [byId, clock, indexOf, t.announce.started],
  );

  const later = (fn: () => void, ms: number): void => {
    queued.current.push(window.setTimeout(fn, ms));
  };

  const press = (id: string): void => {
    const a = apps[id];
    const p = byId[id];
    if (a === undefined || p === undefined) return;
    switch (a.phase) {
      case "get":
        start(id, "get");
        break;
      case "update":
        start(id, "update");
        break;
      case "downloading":
        clock.stop(indexOf[id] ?? -1);
        setApps((prev) => ({ ...prev, [id]: { phase: a.target === "update" ? "update" : "get", target: null } }));
        setAnnounce(fill(t.announce.stopped, p.name));
        break;
      case "open":
        setToast(fill(t.demoOpen, p.name));
        chime("tick");
        if (toastTimer.current !== null) window.clearTimeout(toastTimer.current);
        toastTimer.current = window.setTimeout(() => setToast(null), 2600);
        queued.current.push(toastTimer.current);
        break;
      case "archived":
        setSheet(true);
        break;
      default:
        break;
    }
  };

  const simulateUpdate = (): void => {
    const installed = products.filter((p) => apps[p.id]?.phase === "open");
    if (installed.length === 0) {
      setAnnounce(t.announce.nothing);
      return;
    }
    setApps((prev) => {
      const next = { ...prev };
      for (const p of installed) next[p.id] = { phase: "update", target: null };
      return next;
    });
    setAnnounce(t.announce.update);
    setAccount(false);
    setTab("updates");
    setQuery("");
    if (auto) installed.forEach((p, i) => later(() => start(p.id, "update"), 300 + i * 400));
  };

  const updateAll = (): void => {
    // One after another, as the Store does it.
    const list = products.filter((p) => apps[p.id]?.phase === "update");
    list.forEach((p, i) => later(() => start(p.id, "update"), i * DOWNLOAD_SECONDS * 1000));
  };

  const reset = (): void => {
    clock.reset();
    for (const id of queued.current) window.clearTimeout(id);
    queued.current.length = 0;
    setApps(initial(products));
    setTab("discover");
    setQuery("");
    setArticle(null);
    setAnnounce(t.announce.reset);
  };

  // Keyboard: Escape closes the innermost thing that is open.
  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.key !== "Escape") return;
      if (sheet) setSheet(false);
      else if (article) setArticle(null);
      else if (account) setAccount(false);
      else if (perchOpen) setPerchOpen(false);
      else if (query) setQuery("");
      else return;
      e.stopPropagation();
    };
    const el = root.current;
    el?.addEventListener("keydown", onKey);
    return () => el?.removeEventListener("keydown", onKey);
  }, [sheet, article, account, perchOpen, query]);

  // Shared-element expansion: the article starts at the card's rectangle and grows (FLIP).
  useLayoutEffect(() => {
    const el = articleRef.current;
    const host = main.current;
    if (el === null || host === null || article === null) return;
    el.focus({ preventScroll: true });
    if (article.from === null || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const to = host.getBoundingClientRect();
    const from = article.from;
    const sx = from.width / to.width;
    const sy = from.height / to.height;
    el.animate(
      [
        { transform: `translate(${from.left - to.left}px, ${from.top - to.top}px) scale(${sx}, ${sy})`, borderRadius: "22px", opacity: 0.6 },
        { transform: "none", borderRadius: "14px", opacity: 1 },
      ],
      { duration: 540, easing: "cubic-bezier(0.32, 0.72, 0, 1)" },
    );
  }, [article]);

  const open = (id: string, el: HTMLElement | null): void => {
    setArticle({ id, from: el?.getBoundingClientRect() ?? null });
    chime("tick");
  };

  const q = query.trim().toLowerCase();
  const found = q ? products.filter((p) => `${p.name} ${p.jp ?? ""} ${p.category} ${p.tagline}`.toLowerCase().includes(q)) : [];
  const installed = products.filter((p) => apps[p.id]?.phase === "open" || (apps[p.id]?.phase === "downloading" && apps[p.id]?.target === "update"));
  const waiting = products.filter((p) => apps[p.id]?.phase === "update" || (apps[p.id]?.phase === "downloading" && apps[p.id]?.target === "update"));
  const pending = products.filter((p) => apps[p.id]?.phase === "update").length;
  const downloading = products.filter((p) => apps[p.id]?.phase === "downloading");

  const tabs: { id: Tab; label: string; icon: IconName }[] = [
    { id: "discover", label: t.discover, icon: "compass" },
    { id: "mods", label: t.mods, icon: "blocks" },
    { id: "library", label: t.library, icon: "library" },
    { id: "updates", label: t.updates, icon: "refresh" },
  ];

  const status = (p: Product): string => (p.availability === "soon" ? t.comingSoon : p.availability === "archived" ? t.archived : t.available);

  const button = (p: Product, small: boolean) => (
    <ActionButton product={p} index={indexOf[p.id] ?? 0} state={apps[p.id]!} t={t} jar={jar} clock={clock} onPress={() => press(p.id)} small={small} />
  );

  const row = (p: Product) => (
    <li key={p.id} className="ac-st-row">
      <button type="button" className="ac-st-row-hit" onClick={(e) => open(p.id, e.currentTarget.closest("li"))} aria-label={`${p.name}: ${p.headline}`}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={asset(p.icon)} alt="" width={52} height={52} data-dim={p.availability === "archived"} />
        <span className="ac-st-row-text">
          <b>
            {p.name}
            {p.jp ? <i lang="ja"> {p.jp}</i> : null}
          </b>
          <small>{p.badge ? `${p.badge} · ${p.category}` : p.category}</small>
        </span>
      </button>
      {button(p, true)}
    </li>
  );

  const card = (p: Product, size: "big" | "small") => (
    <article key={p.id} className={`ac-st-card ac-st-card--${size}`} data-dim={p.availability === "archived"} data-brand={p.id}>
      <button type="button" className="ac-st-card-hit" aria-label={`${p.name}: ${p.headline}`} onClick={(e) => open(p.id, e.currentTarget.parentElement)} />
      <div className="ac-st-card-art">
        {p.art ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={asset(p.art)} alt="" loading="lazy" />
        ) : (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={asset(p.icon)} alt="" className="ac-st-card-icon" loading="lazy" />
        )}
      </div>
      <div className="ac-st-card-copy">
        <span className="ac-st-eyebrow">{p.availability === "available" ? t.featured : (p.badge ?? status(p))}</span>
        <h3>{p.headline}</h3>
      </div>
      <div className="ac-st-card-foot">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={asset(p.icon)} alt="" width={34} height={34} />
        <span>
          <b>{p.name}</b>
          <small>{p.tagline}</small>
        </span>
        {button(p, true)}
      </div>
    </article>
  );

  const art = article ? byId[article.id] : undefined;
  const pair = (a: string, b: string) => (
    <div className="ac-st-pair">{products.filter((p) => p.id === a || p.id === b).map((p) => card(p, "small"))}</div>
  );

  const restartTrack = (): void => {
    setRestart((r) => r + 1);
    setPlaying(true);
    chime("tick");
  };

  return (
    <div ref={root} className="ac-stp" data-mode={narrow ? "narrow" : "wide"} lang={t.lang} dir={t.dir} role="region" aria-label={t.region}>
      {/* Perch: the capsule below the menu bar; it steps aside while the player is in front. */}
      {perchOn ? (
        <div className="ac-perch" data-hidden={playerFront} data-open={perchOpen} onMouseEnter={() => setPerchOpen(true)} onMouseLeave={() => setPerchOpen(false)}>
          <button
            type="button"
            className="ac-perch-pill"
            aria-expanded={perchOpen}
            aria-label={`${labels.fresh.perchDemo}: ${labels.fresh.nowPlaying} — ${labels.track}`}
            onClick={() => setPerchOpen((v) => !v)}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={asset("icons/ouka.png")} alt="" width={18} height={18} />
            <span key={restart} className="ac-perch-eq" data-on={playing} aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
          </button>
          <div className="ac-perch-deck" hidden={!perchOpen}>
            <div className="ac-perch-now">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset("icons/ouka.png")} alt="" width={54} height={54} />
              <div className="ac-perch-meta">
                <small>{labels.fresh.nowPlaying}</small>
                <b lang="en">{labels.track}</b>
                <span lang="en">OUKA</span>
              </div>
              <button
                type="button"
                className="ac-perch-fav"
                aria-label={pl.favourite}
                title={pl.favourite}
                aria-pressed={favourite}
                onClick={() => {
                  setFavourite((v) => !v);
                  chime("tick");
                }}
              >
                <Icon name="heart" size={15} fill={favourite ? "currentColor" : "none"} />
              </button>
            </div>
            <div className="ac-perch-transport" dir="ltr">
              <button type="button" aria-label={pl.shuffle} title={pl.shuffle} aria-pressed={shuffle} onClick={() => setShuffle((v) => !v)}>
                <Icon name="shuffle" size={14} />
              </button>
              <button type="button" aria-label={pl.previous} title={pl.previous} onClick={restartTrack}>
                <Icon name="skipBack" size={14} />
              </button>
              <button type="button" className="ac-perch-play" aria-label={pl.playPause} title={pl.playPause} aria-pressed={playing} onClick={() => setPlaying((v) => !v)}>
                <Icon name={playing ? "pause" : "play"} size={16} />
              </button>
              <button
                type="button"
                aria-label={pl.next}
                title={pl.next}
                onClick={() => {
                  // A queue of one: the next track is this one again with Repeat or Shuffle on, the end without.
                  if (repeat || shuffle) restartTrack();
                  else setPlaying(false);
                }}
              >
                <Icon name="skipForward" size={14} />
              </button>
              <button type="button" aria-label={pl.repeat} title={pl.repeat} aria-pressed={repeat} onClick={() => setRepeat((v) => !v)}>
                <Icon name="repeat" size={14} />
              </button>
            </div>
            <label className="ac-perch-vol" dir="ltr">
              <Icon name={volume === 0 ? "mute" : "volume"} size={14} />
              <input type="range" min={0} max={100} value={volume} aria-label={pl.volume} onChange={(e) => setVolume(Number(e.target.value))} />
            </label>
            <button type="button" className="ac-perch-close" aria-label={pl.close} title={pl.close} onClick={() => setPerchOpen(false)}>
              <Icon name="x" size={13} />
            </button>
          </div>
        </div>
      ) : null}

      <div className="ac-stp-window">
        <div className="ac-stp-titlebar" aria-hidden="true">
          <i />
          <i />
          <i />
        </div>
        {!narrow ? (
          <aside className="ac-stp-side" aria-label="Corvus Store">
            <div className="ac-stp-brand">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset("logo.png")} alt="" width={20} height={20} />
              <span>Corvus Store</span>
            </div>
            <label className="ac-stp-search">
              <Icon name="search" size={13} />
              <input type="search" placeholder={t.search} aria-label={t.search} value={query} onChange={(e) => setQuery(e.target.value)} />
            </label>
            <nav className="ac-stp-nav">
              {tabs.map((x) => (
                <button
                  key={x.id}
                  type="button"
                  aria-current={tab === x.id && q === "" ? "page" : undefined}
                  onClick={() => {
                    setTab(x.id);
                    setQuery("");
                  }}
                >
                  <Icon name={x.icon} size={15} />
                  <span>{x.label}</span>
                  {x.id === "updates" && pending > 0 ? <span className="ac-stp-badge">{pending}</span> : null}
                </button>
              ))}
            </nav>
            <button type="button" className="ac-stp-account" aria-haspopup="dialog" aria-expanded={account} onClick={() => setAccount((v) => !v)}>
              <span className="ac-stp-avatar">
                <Icon name="user" size={14} />
              </span>
              <span>{t.account}</span>
            </button>
          </aside>
        ) : (
          <div className="ac-stp-topbar">
            <label className="ac-stp-search">
              <Icon name="search" size={13} />
              <input type="search" placeholder={t.search} aria-label={t.search} value={query} onChange={(e) => setQuery(e.target.value)} />
            </label>
            <button
              type="button"
              className="ac-stp-avatar ac-stp-avatar-btn"
              aria-label={t.account}
              aria-haspopup="dialog"
              aria-expanded={account}
              onClick={() => setAccount((v) => !v)}
            >
              <Icon name="user" size={14} />
            </button>
          </div>
        )}

        <div ref={main} className="ac-stp-main">
          <div className="ac-stp-head">
            <h2 className="ac-stp-title">{q ? t.search : tabs.find((x) => x.id === tab)?.label}</h2>
            {tab === "updates" && q === "" && pending >= 2 ? (
              <button type="button" className="ac-stp-textbtn" onClick={updateAll}>
                {t.updateAll}
              </button>
            ) : null}
          </div>
          <div className="ac-stp-body" data-lenis-prevent>
            {q ? (
              found.length ? (
                <ul className="ac-st-rows">{found.map(row)}</ul>
              ) : (
                <div className="ac-st-empty">
                  <p>{fill(t.noResults, query)}</p>
                  <small>{t.searchHint}</small>
                </div>
              )
            ) : tab === "discover" ? (
              <div className="ac-st-discover">
                {products.filter((p) => p.id === "halia").map((p) => card(p, "big"))}
                {pair("ouka", "astraea")}
                {pair("cherry", "tsubomi")}
                {pair("noctua", "aureum")}
                <div className="ac-st-pair">{products.filter((p) => p.id === "alpha").map((p) => card(p, "small"))}</div>
              </div>
            ) : tab === "mods" ? (
              <ul className="ac-st-rows">{products.map(row)}</ul>
            ) : tab === "library" ? (
              installed.length ? (
                <ul className="ac-st-rows">{installed.map(row)}</ul>
              ) : (
                <div className="ac-st-empty">
                  <p>{t.libraryEmptyTitle}</p>
                  <small>{t.libraryEmptyBody}</small>
                  <button type="button" className="ac-btn ac-btn--small" onClick={() => setTab("discover")}>
                    {t.browse}
                  </button>
                </div>
              )
            ) : waiting.length ? (
              <>
                <p className="ac-st-sub">{t.updatesAvailable}</p>
                <ul className="ac-st-rows">{waiting.map(row)}</ul>
              </>
            ) : (
              <div className="ac-st-empty">
                <p>{t.updatesEmptyTitle}</p>
                <small>{t.updatesEmptyBody}</small>
                <button type="button" className="ac-btn ac-btn--small" onClick={simulateUpdate}>
                  {t.simulate}
                </button>
              </div>
            )}
            {downloading.map((p) => (
              <DownloadLine key={p.id} name={p.name} speed={speedText(labels.fresh.speed, p.id)} index={indexOf[p.id] ?? 0} clock={clock} />
            ))}
          </div>
          <p className="ac-stp-note">{t.demoNote}</p>

          {art ? (
            <div ref={articleRef} className="ac-stp-article" role="dialog" aria-modal="true" aria-label={art.name} tabIndex={-1} data-brand={art.id}>
              <div className="ac-stp-article-hero">
                {art.art ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={asset(art.art)} alt="" />
                ) : (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={asset(art.icon)} alt="" className="ac-st-card-icon" />
                )}
                <div className="ac-stp-article-copy">
                  <span className="ac-st-eyebrow">{art.availability === "available" ? t.featured : (art.badge ?? status(art))}</span>
                  <h3>{art.headline}</h3>
                </div>
                <button type="button" className="ac-stp-close" aria-label={t.close} onClick={() => setArticle(null)}>
                  <Icon name="x" size={16} />
                </button>
              </div>
              <div className="ac-stp-article-body" data-lenis-prevent>
                <div className="ac-stp-article-head">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={asset(art.icon)} alt="" width={64} height={64} data-dim={art.availability === "archived"} />
                  <div>
                    <h4>
                      {art.name}
                      {art.jp ? <i lang="ja"> {art.jp}</i> : null}
                    </h4>
                    <p>{art.tagline}</p>
                  </div>
                  {button(art, false)}
                </div>
                {apps[art.id]?.phase === "downloading" ? (
                  <DownloadLine speed={speedText(labels.fresh.speed, art.id)} index={indexOf[art.id] ?? 0} clock={clock} />
                ) : null}
                <dl className="ac-stp-metrics">
                  <div>
                    <dt>{t.category}</dt>
                    <dd>{art.category}</dd>
                  </div>
                  <div>
                    <dt>{t.compat}</dt>
                    <dd dir="ltr">{art.compat || "—"}</dd>
                  </div>
                  <div>
                    <dt>{t.version}</dt>
                    <dd dir="ltr">{art.version || "—"}</dd>
                  </div>
                </dl>
                <p className="ac-stp-about">{art.about}</p>
                <p className="ac-small">{status(art)}</p>
                {art.requires.length ? (
                  <dl className="ac-stp-info" dir="ltr">
                    <dt>{t.compat}</dt>
                    <dd>{art.requires.join(" · ")}</dd>
                  </dl>
                ) : null}
                {hrefs[art.id] !== undefined ? (
                  <Link className="ac-link" href={hrefs[art.id]!}>
                    {art.name} <span className="ac-flip">{t.readMore}</span>
                  </Link>
                ) : null}
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {narrow ? (
        <nav className="ac-stp-tabs">
          {tabs.map((x) => (
            <button
              key={x.id}
              type="button"
              aria-current={tab === x.id && q === "" ? "page" : undefined}
              onClick={() => {
                setTab(x.id);
                setQuery("");
              }}
            >
              <Icon name={x.icon} size={17} />
              <span>{x.label}</span>
              {x.id === "updates" && pending > 0 ? <span className="ac-stp-badge">{pending}</span> : null}
            </button>
          ))}
        </nav>
      ) : null}

      {account ? (
        <div className="ac-stp-pop" role="dialog" aria-label={t.account}>
          <h4>{t.account}</h4>
          <div className="ac-stp-setting">
            <div>
              <b id="stp-auto">{t.autoUpdateTitle}</b>
              <small>{t.autoUpdateDesc}</small>
            </div>
            <button type="button" className="ac-switch" role="switch" aria-checked={auto} aria-labelledby="stp-auto" onClick={() => setAuto((v) => !v)} />
          </div>
          <div className="ac-stp-setting">
            <div>
              <b id="stp-perch">{labels.perchToggle.title}</b>
              <small>{labels.perchToggle.description}</small>
            </div>
            <button type="button" className="ac-switch" role="switch" aria-checked={perchOn} aria-labelledby="stp-perch" onClick={() => setPerchOn((v) => !v)} />
          </div>
          <div className="ac-stp-pop-actions">
            <button type="button" className="ac-btn ac-btn--small" onClick={simulateUpdate}>
              {t.simulate}
            </button>
            <button type="button" className="ac-btn ac-btn--ghost ac-btn--small" onClick={reset}>
              {t.reset}
            </button>
          </div>
          <small>{t.settingsNote}</small>
        </div>
      ) : null}

      {sheet ? (
        <div className="ac-stp-scrim" onClick={() => setSheet(false)}>
          <div className="ac-stp-sheet" role="alertdialog" aria-modal="true" aria-labelledby="stp-sheet-h" onClick={(e) => e.stopPropagation()}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={asset("icons/alpha.png")} alt="" width={64} height={64} data-dim="true" />
            <h4 id="stp-sheet-h">{t.archivedTitle}</h4>
            <p>{t.archivedBody}</p>
            <button
              ref={(el) => el?.focus({ preventScroll: true })}
              type="button"
              className="ac-btn ac-btn--small"
              onClick={() => {
                setSheet(false);
                setTab("mods");
              }}
            >
              {t.browse}
            </button>
          </div>
        </div>
      ) : null}

      {toast ? (
        <div className="ac-stp-toast" role="status">
          {toast}
        </div>
      ) : null}

      <div className="ac-stp-perchdemo">
        <span className="ac-small">{labels.fresh.perchDemo}</span>
        <button
          type="button"
          className="ac-chip"
          aria-pressed={playerFront}
          disabled={!perchOn}
          onClick={() => {
            setPlayerFront((v) => !v);
            setAnnounce(playerFront ? labels.fresh.perchShown : labels.fresh.perchHidden);
            if (playerFront) burst(0, 0, 0, 0.3);
          }}
        >
          {playerFront ? labels.fresh.perchLeave : labels.fresh.perchFront}
        </button>
        <span className="ac-small ac-stp-perchnote">{perchOn ? (playerFront ? labels.fresh.perchHidden : labels.fresh.perchShown) : labels.perchToggle.description}</span>
      </div>

      <div className="sr-only" role="status" aria-live="polite">
        {announce}
      </div>
    </div>
  );
}
