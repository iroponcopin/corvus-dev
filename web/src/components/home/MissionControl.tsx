"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { chime } from "@/engine/audio";
import { fetchFeed } from "@/lib/feeds";
import { Icon } from "../Icon";

/** The inspector shows the first 4 KB of the pretty-printed payload; the rest is said, not shown. */
const INSPECT_LIMIT = 4096;

const FEEDS = ["releases.json", "upcoming.json", "glimpse_manifest.json", "changelog_feed/brands.json"];

interface Probe {
  path: string;
  status: number | null;
  ms: number | null;
  bytes: number | null;
  modified: string | null;
}

export interface MissionControlLabels {
  feeds: string;
  ping: string;
  pinging: string;
  latency: string;
  measured: string;
  unreachable: string;
  inspect: string;
  payload: string;
  bytes: string;
  modified: string;
  truncated: string;
  drawer: string;
}

/** A latency badge's class: green under 250 ms, amber under 900 ms, red beyond. */
function speed(ms: number | null): "fast" | "mid" | "slow" | "none" {
  if (ms === null) return "none";
  if (ms < 250) return "fast";
  if (ms < 900) return "mid";
  return "slow";
}

/** The pretty-printed payload, cut to the inspector's limit with an explicit marker. */
function inspectable(raw: string): { text: string; cut: boolean } {
  let pretty = raw;
  try {
    pretty = JSON.stringify(JSON.parse(raw), null, 2);
  } catch {
    // Not JSON: show it as it came.
  }
  if (pretty.length <= INSPECT_LIMIT) return { text: pretty, cut: false };
  return { text: pretty.slice(0, INSPECT_LIMIT), cut: true };
}

/**
 * Mission Control for the home page: the round trip to each feed the bot and the launcher poll, measured from
 * this browser now, with latency badges, byte counters, the server's Last-Modified, and a payload inspector
 * drawer that shows the feed's own JSON. It says nothing about whether the bot process is up; the page cannot know.
 */
export function MissionControl({ labels, lazy = false }: { labels: MissionControlLabels; lazy?: boolean }) {
  const box = useRef<HTMLDivElement>(null);
  const bodies = useRef<Record<string, string>>({});
  const [probes, setProbes] = useState<Probe[]>(FEEDS.map((path) => ({ path, status: null, ms: null, bytes: null, modified: null })));
  const [busy, setBusy] = useState(false);
  const [at, setAt] = useState<string | null>(null);
  const [open, setOpen] = useState<string | null>(null);
  const [shown, setShown] = useState<{ text: string; cut: boolean } | null>(null);

  const measure = useCallback(async () => {
    setBusy(true);
    const results: Probe[] = [];
    for (const path of FEEDS) {
      const r = await fetchFeed(path, { body: true });
      if (r.text !== null) bodies.current[path] = r.text;
      results.push({ path, status: r.status, ms: r.status === null ? null : r.ms, bytes: r.status === null ? null : r.bytes, modified: r.modified });
    }
    setProbes(results);
    setAt(new Date().toLocaleTimeString());
    setBusy(false);
    chime(results.every((r) => r.status === 200) ? "done" : "error");
  }, []);

  useEffect(() => {
    const el = box.current;
    if (!lazy || el === null || typeof IntersectionObserver === "undefined") {
      void measure();
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        if (entries.some((e) => e.isIntersecting)) {
          io.disconnect();
          void measure();
        }
      },
      { rootMargin: "120px" },
    );
    io.observe(el);
    return () => io.disconnect();
  }, [measure, lazy]);

  const totals = useMemo(() => probes.reduce((n, p) => n + (p.bytes ?? 0), 0), [probes]);
  const okCount = probes.filter((p) => p.status === 200).length;

  const toggle = (path: string) => {
    if (open === path) {
      setOpen(null);
      setShown(null);
      return;
    }
    const raw = bodies.current[path];
    setOpen(path);
    setShown(raw === undefined ? null : inspectable(raw));
  };

  return (
    <div ref={box} className="ac-mc ac-card" role="group" aria-label={labels.feeds}>
      <header className="ac-mc-head">
        <span className="ac-mc-dots" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <p className="ac-mc-title">
          <span className="ac-term-prompt">$</span> {labels.feeds}
        </p>
        <span className="ac-mc-count ac-ltr" data-ok={okCount === FEEDS.length ? "true" : okCount === 0 && !busy ? "false" : undefined}>
          {okCount}/{FEEDS.length}
        </span>
      </header>

      <ul className="ac-mc-rows">
        {probes.map((p) => {
          const ok = p.status === 200;
          const s = speed(p.ms);
          return (
            <li key={p.path} className="ac-mc-row" data-ok={p.status === null ? undefined : ok}>
              <span className="ac-mc-path ac-ltr">{p.path}</span>
              <span className="ac-mc-badge ac-ltr" data-speed={s}>
                {p.ms === null ? "—" : `${p.ms} ms`}
              </span>
              <span className="ac-mc-status ac-ltr">{p.status ?? (busy || at === null ? "…" : labels.unreachable)}</span>
              <span className="ac-mc-meta ac-ltr">
                <span className="ac-mc-k">{labels.bytes}</span> {p.bytes === null ? "—" : p.bytes.toLocaleString("en-US")}
              </span>
              <span className="ac-mc-meta ac-ltr">
                <span className="ac-mc-k">{labels.modified}</span> {p.modified ?? "—"}
              </span>
              <button
                type="button"
                className="ac-mc-inspect"
                aria-expanded={open === p.path}
                aria-controls="ac-mc-drawer"
                disabled={!ok && bodies.current[p.path] === undefined}
                onClick={() => toggle(p.path)}
              >
                {labels.inspect}
              </button>
            </li>
          );
        })}
      </ul>

      <div className="ac-mc-foot">
        <span className="ac-ltr ac-mc-total">
          Σ {totals.toLocaleString("en-US")} {labels.bytes}
        </span>
        <button type="button" className="ac-btn ac-btn--ghost ac-btn--small" onClick={() => void measure()} disabled={busy}>
          <Icon name="refresh" size={14} />
          {busy ? labels.pinging : labels.ping}
        </button>
        {at ? (
          <span className="ac-small">
            {labels.measured} · <span className="ac-ltr">{at}</span>
          </span>
        ) : null}
      </div>

      <section id="ac-mc-drawer" className="ac-mc-drawer" data-open={open !== null} hidden={open === null} aria-label={labels.payload}>
        {open !== null ? (
          <>
            <header className="ac-mc-drawer-head">
              <p>
                <span className="ac-mc-k">{labels.payload}</span> <span className="ac-ltr">{open}</span>
              </p>
              <button
                type="button"
                className="ac-btn ac-btn--ghost ac-btn--small"
                onClick={() => {
                  setOpen(null);
                  setShown(null);
                }}
              >
                {labels.drawer}
              </button>
            </header>
            {shown === null ? (
              <p className="ac-small">—</p>
            ) : (
              <>
                <pre className="ac-mc-code ac-ltr" dir="ltr" tabIndex={0}>
                  {shown.text}
                </pre>
                {shown.cut ? <p className="ac-small ac-mc-cut">{labels.truncated}</p> : null}
              </>
            )}
          </>
        ) : null}
      </section>
    </div>
  );
}
