"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { chime } from "@/engine/audio";
import { fetchFeed } from "@/lib/feeds";
import { Icon } from "../Icon";

interface Probe {
  path: string;
  status: number | null;
  ms: number | null;
  bytes: number | null;
  modified: string | null;
}

const FEEDS = ["releases.json", "upcoming.json", "glimpse_manifest.json", "changelog_feed/brands.json"];

/**
 * Live telemetry that a static page can honestly give: the round trip to each feed the bot
 * (and the launcher) polls, measured from this browser right now, with the server's own
 * Last-Modified. It says nothing about whether the bot process is up — the page cannot know.
 */
export function FeedTelemetry({
  labels,
  lazy = false,
}: {
  labels: { feeds: string; ping: string; pinging: string; latency: string; measured: string; unreachable: string };
  /** Measure first when the terminal scrolls into view, instead of on load. */
  lazy?: boolean;
}) {
  const box = useRef<HTMLDivElement>(null);
  const [probes, setProbes] = useState<Probe[]>(FEEDS.map((path) => ({ path, status: null, ms: null, bytes: null, modified: null })));
  const [busy, setBusy] = useState(false);
  const [at, setAt] = useState<string | null>(null);

  const measure = useCallback(async () => {
    setBusy(true);
    const results: Probe[] = [];
    for (const path of FEEDS) {
      const r = await fetchFeed(path);
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

  return (
    <div ref={box} className="ac-term ac-card" role="group" aria-label={labels.feeds}>
      <div className="ac-term-bar" aria-hidden="true">
        <i />
        <i />
        <i />
        <span>corvus@nexus — feeds</span>
      </div>
      <div className="ac-term-body">
        <p className="ac-term-line">
          <span className="ac-term-prompt">$</span> {labels.feeds}
        </p>
        <table className="ac-term-table">
          <thead>
            <tr>
              <th scope="col">feed</th>
              <th scope="col">http</th>
              <th scope="col">{labels.latency}</th>
              <th scope="col">bytes</th>
              <th scope="col">last-modified</th>
            </tr>
          </thead>
          <tbody>
            {probes.map((p) => {
              const ok = p.status === 200;
              return (
                <tr key={p.path} data-ok={p.status === null ? undefined : ok}>
                  <td className="ac-ltr">{p.path}</td>
                  <td>{p.status ?? (busy ? "…" : labels.unreachable)}</td>
                  <td className="ac-ltr">{p.ms === null ? "—" : `${p.ms} ms`}</td>
                  <td className="ac-ltr">{p.bytes === null ? "—" : p.bytes.toLocaleString("en-US")}</td>
                  <td className="ac-ltr">{p.modified ?? "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <div className="ac-term-foot">
          <button type="button" className="ac-btn ac-btn--ghost ac-btn--small" onClick={() => void measure()} disabled={busy}>
            <Icon name="refresh" size={14} />
            {busy ? labels.pinging : labels.ping}
          </button>
          {at ? (
            <span className="ac-small">
              {labels.measured} · <span className="ac-ltr">{at}</span>
            </span>
          ) : null}
          <span className="ac-term-cursor" aria-hidden="true" />
        </div>
      </div>
    </div>
  );
}
