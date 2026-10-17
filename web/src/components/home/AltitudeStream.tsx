"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import { addFrameHook } from "@/engine/loop";
import { asset } from "@/lib/site";

export interface StreamRelease {
  key: string;
  href: string;
  icon: string;
  brand: string;
  version: string;
  date: string | null;
  title: string;
  color: string;
}

/**
 * The altitude stream: the latest releases, newest first, as frosted-glass cards that drift on a wind
 * current. The wind follows the scroll (each card slides a different distance as the section passes), and
 * there is a slow drift on top. Reduced motion: a static grid.
 */
export function AltitudeStream({
  title,
  lede,
  releases,
  openLabel,
}: {
  title: string;
  lede: string;
  releases: StreamRelease[];
  openLabel: string;
}) {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (el === null || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    return addFrameHook(() => {
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight;
      const q = Math.min(1, Math.max(0, (vh - r.top) / (vh + r.height)));
      el.style.setProperty("--wind", (q * 2 - 1).toFixed(3));
    });
  }, []);

  return (
    <section ref={ref} className="ac-altitude" aria-labelledby="ac-altitude-h">
      <div className="ac-wrap">
        <h2 id="ac-altitude-h" className="ac-h2">
          {title}
        </h2>
        <p className="ac-lead ac-altitude-lede">{lede}</p>
        <ul className="ac-altitude-grid">
          {releases.map((r, i) => (
            <li key={r.key}>
              <Link
                href={r.href}
                className="ac-glass ac-altitude-card"
                style={{ "--dx": `${(i % 3 === 0 ? -56 : i % 3 === 1 ? 24 : 80) + (i % 2) * 14}px` } as React.CSSProperties}
                data-brand={r.brand}
              >
                <div className="ac-altitude-top">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={asset(r.icon)} alt="" width={44} height={44} />
                  <div>
                    <p className="ac-altitude-brand" style={{ color: r.color }}>
                      {r.brand}
                    </p>
                    <p className="ac-altitude-version">
                      <b className="ac-ltr">{r.version}</b>
                      {r.date ? (
                        <time className="ac-ltr" dateTime={r.date}>
                          {" · "}
                          {r.date}
                        </time>
                      ) : null}
                    </p>
                  </div>
                </div>
                <p className="ac-altitude-title">{r.title}</p>
                <span className="ac-link" aria-hidden="true">
                  {openLabel}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}
