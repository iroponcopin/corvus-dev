"use client";

import Link from "next/link";
import { useEffect, useRef, useState, type CSSProperties } from "react";
import { addFrameHook } from "@/engine/loop";
import { asset } from "@/lib/site";

export interface LineupItem {
  key: string;
  name: string;
  line: string;
  status: string;
  icon: string;
  accent: string;
  href: string;
  /** A micro-demo that plays while the model is the active one. */
  demo: "power" | "blade" | null;
}

/**
 * The Lineup: a pinned, horizontal showcase in the manner of a product line page. The page scrolls down
 * through a tall section; the track moves sideways under a sticky stage. Hover, focus or scrub makes a
 * model active: the section's ambient light takes its accent, and its micro-demo plays. Below 640px the
 * stage is a plain vertical list with no pinning, and reduced motion gets the same list.
 */
export function Lineup({
  items,
  labels,
}: {
  items: LineupItem[];
  labels: { title: string; lede: string; scrub: string; open: string; power: string; blade: string };
}) {
  const section = useRef<HTMLElement>(null);
  const track = useRef<HTMLUListElement>(null);
  const [active, setActive] = useState(0);
  const activeRef = useRef(0);

  const activate = (i: number) => {
    if (i === activeRef.current) return;
    activeRef.current = i;
    setActive(i);
  };

  useEffect(() => {
    const sec = section.current;
    const tr = track.current;
    if (sec === null || tr === null) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const stacked = window.matchMedia("(max-width: 639px)").matches;
    if (still || stacked) return;
    return addFrameHook(() => {
      const r = sec.getBoundingClientRect();
      const span = sec.offsetHeight - window.innerHeight;
      const p = span <= 0 ? 0 : Math.min(1, Math.max(0, -r.top / span));
      const travel = Math.max(0, tr.scrollWidth - window.innerWidth + 2 * 16);
      tr.style.transform = `translate3d(${(-p * travel).toFixed(1)}px, 0, 0)`;
      const i = Math.min(items.length - 1, Math.floor(p * items.length));
      activate(i);
      sec.style.setProperty("--lineup-accent", items[activeRef.current]?.accent ?? "#2997ff");
    });
  }, [items]);

  useEffect(() => {
    section.current?.style.setProperty("--lineup-accent", items[active]?.accent ?? "#2997ff");
  }, [active, items]);

  return (
    <section ref={section} className="ac-lineup" aria-labelledby="ac-lineup-h" style={{ "--lineup-accent": items[0]?.accent ?? "#2997ff" } as CSSProperties}>
      <div className="ac-lineup-sticky">
        <header className="ac-lineup-head">
          <h2 id="ac-lineup-h" className="ac-h2">
            {labels.title}
          </h2>
          <p className="ac-lead">{labels.lede}</p>
          <p className="ac-small ac-lineup-scrub" aria-hidden="true">
            {labels.scrub}
          </p>
        </header>
        <ul ref={track} className="ac-lineup-track">
          {items.map((x, i) => (
            <li
              key={x.key}
              className="ac-lineup-card"
              data-active={i === active ? "true" : undefined}
              style={{ "--accent": x.accent } as CSSProperties}
              onPointerEnter={() => activate(i)}
              onFocus={() => activate(i)}
            >
              <Link href={x.href} className="ac-lineup-link" aria-label={`${x.name} — ${x.status}`}>
                <div className="ac-lineup-media">
                  {x.demo === "power" ? <PowerGrid label={labels.power} /> : null}
                  {x.demo === "blade" ? <BladeCombo label={labels.blade} /> : null}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img className="ac-lineup-icon" src={asset(x.icon)} alt="" width={120} height={120} />
                </div>
                <h3 className="ac-lineup-name">{x.name}</h3>
                <p className="ac-lineup-line">{x.line}</p>
                <span className="ac-lineup-status">{x.status}</span>
                <span className="ac-link" aria-hidden="true">
                  {labels.open}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </div>
    </section>
  );
}

/** OUKA's power grid: nodes that pulse, and pulses that run along the lines between them. */
function PowerGrid({ label }: { label: string }) {
  const nodes: [number, number][] = [
    [20, 60],
    [60, 24],
    [60, 96],
    [110, 60],
    [160, 24],
    [160, 96],
    [188, 60],
  ];
  const links: [number, number][] = [
    [0, 1],
    [0, 2],
    [1, 3],
    [2, 3],
    [3, 4],
    [3, 5],
    [4, 6],
    [5, 6],
  ];
  return (
    <svg className="ac-demo ac-demo--power" viewBox="0 0 200 120" role="img" aria-label={label}>
      {links.map(([a, b], i) => {
        const [x1, y1] = nodes[a] ?? [0, 0];
        const [x2, y2] = nodes[b] ?? [0, 0];
        return <line key={`l${i}`} className="ac-demo-line" pathLength={100} x1={x1} y1={y1} x2={x2} y2={y2} style={{ animationDelay: `${(i * 0.23).toFixed(2)}s` }} />;
      })}
      {nodes.map(([x, y], i) => (
        <circle key={`n${i}`} className="ac-demo-node" cx={x} cy={y} r={6} style={{ animationDelay: `${(i * 0.31).toFixed(2)}s` }} />
      ))}
    </svg>
  );
}

/** Halia's blade combo: three slash arcs drawn in turn, each one fading as the next begins. */
function BladeCombo({ label }: { label: string }) {
  const arcs = ["M20 96 Q 90 10 180 40", "M24 70 Q 100 30 186 92", "M40 110 Q 110 60 180 20"];
  return (
    <svg className="ac-demo ac-demo--blade" viewBox="0 0 200 120" role="img" aria-label={label}>
      {arcs.map((d, i) => (
        <path key={i} className="ac-demo-slash" d={d} pathLength={100} style={{ animationDelay: `${(i * 0.5).toFixed(2)}s` }} />
      ))}
    </svg>
  );
}
