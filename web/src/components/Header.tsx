"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import { getLenis } from "./SmoothScroll";
import { Icon } from "./Icon";
import { SoundToggle } from "./SoundToggle";
import { asset, BASE_PATH, LANGUAGES, pathOf } from "@/lib/site";
import { sectionKey, splitPath } from "@/lib/paths";
import type { Lang } from "@/lib/wiki-types";

export interface HeaderLabels {
  siteTitle: string;
  home: string;
  launcher: string;
  models: string;
  updates: string;
  recipes: string;
  discord: string;
  download: string;
  menu: string;
  close: string;
  language: string;
  primary: string;
  sound: string;
  soundOn: string;
  soundOff: string;
}

/** One line in the Models menu: its icon is icons/<key>.png; `status` is the Store's own word for it. */
export interface ModelLink {
  key: string;
  label: string;
  href: string;
  status: string;
  soon: boolean;
}

/** One entry of the Updates mega menu. */
export interface UpdateLink {
  key: string;
  label: string;
  desc: string;
  href: string;
  icon: "library" | "compass" | "play" | "user";
}

const LANG_KEY = "corvus-dev-lang";
const MODEL_SECTIONS = new Set(["ouka", "cherry", "aureum", "cherry-controls"]);
const UPDATE_SECTIONS = new Set(["changelog", "announcement", "teasers", "skin"]);
type Menu = "models" | "updates" | null;

function rememberLang(code: string): void {
  try {
    localStorage.setItem(LANG_KEY, code);
  } catch {
    /* storage can be unavailable (private mode); the choice simply isn't remembered */
  }
}

/** Close a popover on Escape or on a pointerdown outside it. */
function useDismiss(open: boolean, close: () => void, refs: React.RefObject<HTMLElement | null>[]): void {
  useEffect(() => {
    if (!open) return;
    const onDown = (e: PointerEvent): void => {
      const t = e.target as Node;
      if (refs.some((r) => r.current?.contains(t))) return;
      close();
    };
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") close();
    };
    document.addEventListener("pointerdown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("pointerdown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open, close, refs]);
}

export function Header({
  lang,
  labels,
  models,
  updates,
}: {
  lang: Lang;
  labels: HeaderLabels;
  models: ModelLink[];
  updates: UpdateLink[];
}) {
  const pathname = usePathname();
  const { section } = splitPath(pathname);
  const key = sectionKey(section);
  const [menu, setMenu] = useState<Menu>(null);
  const [langOpen, setLangOpen] = useState(false);
  const [sheet, setSheet] = useState(false);
  const [suffix, setSuffix] = useState("");
  const [compact, setCompact] = useState(false);
  const modelsBtn = useRef<HTMLButtonElement>(null);
  const modelsPop = useRef<HTMLDivElement>(null);
  const updatesBtn = useRef<HTMLButtonElement>(null);
  const updatesPop = useRef<HTMLDivElement>(null);
  const langBtn = useRef<HTMLButtonElement>(null);
  const langPop = useRef<HTMLDivElement>(null);
  const modelsId = useId();
  const updatesId = useId();
  const langId = useId();
  const sheetId = useId();

  const closeMenu = useCallback(() => setMenu(null), []);
  const closeLang = useCallback(() => {
    setLangOpen(false);
    langBtn.current?.focus();
  }, []);
  useDismiss(menu === "models", closeMenu, [modelsBtn, modelsPop]);
  useDismiss(menu === "updates", closeMenu, [updatesBtn, updatesPop]);
  useDismiss(langOpen, closeLang, [langBtn, langPop]);

  // The language links carry the query and hash of the page (so ?model= survives a switch).
  useEffect(() => {
    setSuffix(window.location.search + window.location.hash);
    setMenu(null);
    setSheet(false);
  }, [pathname]);

  useEffect(() => {
    const onScroll = (): void => setCompact(window.scrollY > 24);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // The mobile sheet locks the page underneath it.
  useEffect(() => {
    if (!sheet) return;
    const root = document.documentElement;
    const prev = root.style.overflow;
    root.style.overflow = "hidden";
    getLenis()?.stop();
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "Escape") setSheet(false);
    };
    document.addEventListener("keydown", onKey);
    return () => {
      root.style.overflow = prev;
      getLenis()?.start();
      document.removeEventListener("keydown", onKey);
    };
  }, [sheet]);

  // Footer links (and any other a[data-lang]) remember the choice too.
  useEffect(() => {
    const onClick = (e: MouseEvent): void => {
      const a = (e.target as Element | null)?.closest?.("a[data-lang]");
      const code = a?.getAttribute("data-lang");
      if (code) rememberLang(code);
    };
    document.addEventListener("click", onClick);
    document.addEventListener("auxclick", onClick);
    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("auxclick", onClick);
    };
  }, []);

  // Focus management inside the language list.
  useEffect(() => {
    if (!langOpen) return;
    const items = Array.from(langPop.current?.querySelectorAll<HTMLAnchorElement>("a") ?? []);
    const current = items.find((a) => a.getAttribute("aria-current") === "true") ?? items[0];
    current?.focus();
    const onKey = (e: KeyboardEvent): void => {
      const i = items.indexOf(document.activeElement as HTMLAnchorElement);
      let next = -1;
      if (e.key === "ArrowDown") next = (i + 1) % items.length;
      else if (e.key === "ArrowUp") next = (i - 1 + items.length) % items.length;
      else if (e.key === "Home") next = 0;
      else if (e.key === "End") next = items.length - 1;
      if (next >= 0) {
        e.preventDefault();
        items[next]?.focus();
      }
    };
    const pop = langPop.current;
    pop?.addEventListener("keydown", onKey);
    return () => pop?.removeEventListener("keydown", onKey);
  }, [langOpen]);

  const current = (k: string): "page" | undefined => (k === key ? "page" : undefined);
  const toggle = (m: Exclude<Menu, null>): void => setMenu((v) => (v === m ? null : m));
  return (
    <header className="ac-header" data-compact={compact ? "true" : "false"}>
      <div className="ac-header-pill ac-glass">
        <Link href={pathOf(lang, "")} className="ac-brand" aria-label={`${labels.siteTitle} · ${labels.home}`}>
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={asset("logo.png")} alt="" width={22} height={22} />
          <span>{labels.siteTitle}</span>
        </Link>

        <nav className="ac-nav" aria-label={labels.primary}>
          <Link href={pathOf(lang, "launcher/")} className="ac-nav-link" aria-current={current("launcher")}>
            {labels.launcher}
          </Link>
          <div className="ac-nav-menu">
            <button
              ref={modelsBtn}
              type="button"
              className="ac-nav-link"
              aria-expanded={menu === "models"}
              aria-haspopup="true"
              aria-controls={modelsId}
              aria-current={MODEL_SECTIONS.has(key) ? "page" : undefined}
              onClick={() => toggle("models")}
            >
              {labels.models}
              <Icon name="chevronDown" size={13} className="ac-chev" data-open={menu === "models"} />
            </button>
            <div ref={modelsPop} id={modelsId} className="ac-pop ac-pop--models ac-glass" hidden={menu !== "models"}>
              <ul className="ac-models">
                {models.map((m) => (
                  <li key={m.key}>
                    <Link href={m.href} className="ac-model" aria-current={current(m.key)} onClick={closeMenu}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={asset(`icons/${m.key}.png`)} alt="" width={36} height={36} />
                      <span>
                        <b>{m.label}</b>
                        <small data-soon={m.soon}>{m.status}</small>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <Link href={pathOf(lang, "recipes/")} className="ac-nav-link" aria-current={current("recipes")}>
            {labels.recipes}
          </Link>
          <div className="ac-nav-menu">
            <button
              ref={updatesBtn}
              type="button"
              className="ac-nav-link"
              aria-expanded={menu === "updates"}
              aria-haspopup="true"
              aria-controls={updatesId}
              aria-current={UPDATE_SECTIONS.has(key) ? "page" : undefined}
              onClick={() => toggle("updates")}
            >
              {labels.updates}
              <Icon name="chevronDown" size={13} className="ac-chev" data-open={menu === "updates"} />
            </button>
            <div ref={updatesPop} id={updatesId} className="ac-pop ac-mega ac-glass" hidden={menu !== "updates"}>
              <ul className="ac-mega-grid">
                {updates.map((u) => (
                  <li key={u.key}>
                    <Link href={u.href} className="ac-mega-item" aria-current={current(u.key)} onClick={closeMenu}>
                      <span className="ac-mega-icon" data-k={u.key} aria-hidden="true">
                        <Icon name={u.icon} size={18} />
                      </span>
                      <span className="ac-mega-text">
                        <b>{u.label}</b>
                        <small>{u.desc}</small>
                      </span>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <Link href={pathOf(lang, "discord/")} className="ac-nav-link" aria-current={current("discord")}>
            {labels.discord}
          </Link>
        </nav>

        <div className="ac-header-end">
          <SoundToggle label={labels.sound} on={labels.soundOn} off={labels.soundOff} />
          <div className="ac-lang">
            <button
              ref={langBtn}
              type="button"
              className="ac-iconbtn"
              aria-label={labels.language}
              title={labels.language}
              aria-haspopup="true"
              aria-expanded={langOpen}
              aria-controls={langId}
              onClick={() => (langOpen ? closeLang() : setLangOpen(true))}
            >
              <Icon name="globe" size={17} />
            </button>
            <div ref={langPop} id={langId} className="ac-pop ac-pop--lang ac-glass" hidden={!langOpen}>
              <ul>
                {LANGUAGES.map((l) => (
                  <li key={l.code}>
                    <a
                      href={`${BASE_PATH}${pathOf(l.code, section)}${suffix}`}
                      lang={l.code}
                      hrefLang={l.code}
                      data-lang={l.code}
                      dir={l.dir === "rtl" ? "rtl" : undefined}
                      aria-current={l.code === lang ? "true" : undefined}
                      className="ac-pop-item"
                    >
                      <span>{l.name}</span>
                      {l.code === lang ? <small aria-hidden="true">✓</small> : null}
                    </a>
                  </li>
                ))}
              </ul>
            </div>
          </div>
          <Link
            href={pathOf(lang, "download/")}
            className="ac-btn ac-btn--small ac-cta"
            aria-current={current("download")}
          >
            {labels.download}
          </Link>
          <button
            type="button"
            className="ac-iconbtn ac-menu-btn"
            aria-label={sheet ? labels.close : labels.menu}
            aria-expanded={sheet}
            aria-controls={sheetId}
            onClick={() => setSheet((v) => !v)}
          >
            <Icon name={sheet ? "x" : "menu"} size={18} />
          </button>
        </div>
      </div>

      {sheet ? (
        <div id={sheetId} className="ac-sheet" style={{ pointerEvents: "auto" }}>
          <nav aria-label={labels.primary} className="ac-sheet-nav">
            <Link href={pathOf(lang, "launcher/")} onClick={() => setSheet(false)} aria-current={current("launcher")}>
              {labels.launcher}
            </Link>
            <p className="ac-eyebrow">{labels.models}</p>
            {models.map((m) => (
              <Link key={m.key} href={m.href} onClick={() => setSheet(false)} aria-current={current(m.key)}>
                {m.label}
                {m.soon ? <small className="ac-sheet-soon">{m.status}</small> : null}
              </Link>
            ))}
            <p className="ac-eyebrow" aria-hidden="true">
              {" "}
            </p>
            <Link href={pathOf(lang, "recipes/")} onClick={() => setSheet(false)} aria-current={current("recipes")}>
              {labels.recipes}
            </Link>
            <p className="ac-eyebrow">{labels.updates}</p>
            {updates.map((u) => (
              <Link key={u.key} href={u.href} onClick={() => setSheet(false)} aria-current={current(u.key)}>
                {u.label}
              </Link>
            ))}
            <p className="ac-eyebrow" aria-hidden="true">
              {" "}
            </p>
            <Link href={pathOf(lang, "discord/")} onClick={() => setSheet(false)} aria-current={current("discord")}>
              {labels.discord}
            </Link>
            <Link
              href={pathOf(lang, "download/")}
              className="ac-btn ac-sheet-cta"
              onClick={() => setSheet(false)}
              aria-current={current("download")}
            >
              {labels.download}
            </Link>
          </nav>
        </div>
      ) : null}
    </header>
  );
}
