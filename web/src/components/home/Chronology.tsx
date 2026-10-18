"use client";

import Link from "next/link";
import { useEffect, useLayoutEffect, useRef } from "react";
import { addFrameHook } from "@/engine/loop";
import { asset } from "@/lib/site";

export interface ChronoItem {
  key: string;
  brand: string;
  icon: string;
  color: string;
  version: string;
  date: string | null;
  title: string;
  summary: string;
  href: string;
  /** Corvus' own copy is set in English, whatever the page language. */
  english: boolean;
  now: boolean;
}

/** The spline's path: a gentle S through the centre column, one bend per release. */
function splinePath(points: [number, number][], amp: number): string {
  if (points.length < 2) return "";
  const first = points[0];
  if (first === undefined) return "";
  let d = `M ${first[0]} ${first[1]}`;
  for (let i = 1; i < points.length; i++) {
    const prev = points[i - 1];
    const next = points[i];
    if (prev === undefined || next === undefined) continue;
    const [x0, y0] = prev;
    const [x1, y1] = next;
    const side = i % 2 === 0 ? amp : -amp;
    const dy = (y1 - y0) / 2;
    d += ` C ${x0 + side} ${y0 + dy}, ${x1 + side} ${y1 - dy}, ${x1} ${y1}`;
  }
  return d;
}

/**
 * The chronology: one card per live model, newest first, joined by an SVG spline down the centre. The spline
 * draws itself as the section scrolls (stroke-dashoffset, the only thing animated on it); each node lights as
 * the drawing reaches it; each card springs in once as it enters. Reduced motion: the spline is drawn, every
 * node lit, every card in place, with no motion.
 */
export function Chronology({
  items,
  labels,
}: {
  items: ChronoItem[];
  labels: { now: string; shipped: string; open: string };
}) {
  const list = useRef<HTMLOListElement>(null);
  const svg = useRef<SVGSVGElement>(null);
  const path = useRef<SVGPathElement>(null);
  const nodes = useRef<(HTMLSpanElement | null)[]>([]);
  const cards = useRef<(HTMLLIElement | null)[]>([]);
  const geo = useRef({ top: 0, height: 0 });
  const still = useRef(false);

  // Lay out the spline and the nodes from the cards' positions; again whenever the list resizes.
  useLayoutEffect(() => {
    const el = list.current;
    const s = svg.current;
    const p = path.current;
    if (el === null || s === null || p === null) return;
    const layout = () => {
      const W = el.offsetWidth;
      const H = el.offsetHeight;
      const narrow = W < 720;
      const cx = narrow ? 14 : W / 2;
      const amp = narrow ? 0 : Math.min(90, W * 0.08);
      s.setAttribute("viewBox", `0 0 ${W} ${H}`);
      const pts: [number, number][] = [];
      cards.current.forEach((c, i) => {
        if (c === null) return;
        const y = c.offsetTop + 34;
        pts.push([cx, y]);
        const node = nodes.current[i];
        if (node) {
          node.style.left = `${cx}px`;
          node.style.top = `${y}px`;
        }
      });
      p.setAttribute("d", splinePath(pts, amp));
      geo.current = { top: 0, height: H };
    };
    layout();
    const ro = new ResizeObserver(layout);
    ro.observe(el);
    return () => ro.disconnect();
  }, [items]);

  // The draw: progress from the list's position in the viewport; nodes light as it reaches them.
  useEffect(() => {
    const el = list.current;
    const p = path.current;
    if (el === null || p === null) return;
    still.current = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (still.current) {
      p.style.strokeDashoffset = "0";
      nodes.current.forEach((n) => n?.setAttribute("data-lit", "true"));
      cards.current.forEach((c) => c?.setAttribute("data-in", "true"));
      return;
    }
    let last = -1;
    const lit = nodes.current.map(() => false);
    const off = addFrameHook(() => {
      const r = el.getBoundingClientRect();
      const vh = window.innerHeight;
      const q = Math.min(1, Math.max(0, (vh * 0.8 - r.top) / Math.max(1, r.height)));
      if (Math.abs(q - last) > 0.001) {
        last = q;
        p.style.strokeDashoffset = (1 - q).toFixed(4);
      }
      const n = nodes.current.length;
      nodes.current.forEach((node, i) => {
        const on = q * n >= i + 0.25;
        if (node && lit[i] !== on) {
          lit[i] = on;
          node.setAttribute("data-lit", on ? "true" : "false");
        }
      });
    });
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) if (e.isIntersecting) (e.target as HTMLElement).setAttribute("data-in", "true");
      },
      { rootMargin: "0px 0px -8% 0px" },
    );
    cards.current.forEach((c) => c && io.observe(c));
    return () => {
      off();
      io.disconnect();
    };
  }, [items]);

  return (
    <ol ref={list} className="ac-time-list ac-chrono">
      <svg ref={svg} className="ac-chrono-spline" aria-hidden="true" preserveAspectRatio="none" focusable="false">
        <path ref={path} pathLength={1} strokeDasharray={1} strokeDashoffset={1} />
      </svg>
      {items.map((x, i) => (
        <li
          key={x.key}
          ref={(el) => {
            cards.current[i] = el;
          }}
          className="ac-time-card ac-card ac-chrono-card"
          data-side={i % 2 === 0 ? "a" : "b"}
          data-brand={x.brand}
        >
          <span
            ref={(el) => {
              nodes.current[i] = el;
            }}
            className="ac-chrono-node"
            aria-hidden="true"
            style={{ background: x.color, color: x.color }}
          />
          <div className="ac-time-top">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={asset(x.icon)} alt="" width={44} height={44} />
            <div>
              <p className="ac-eyebrow">
                {x.now ? labels.now : labels.shipped} · {x.brand}
              </p>
              <h3>
                <span className="ac-ltr">{x.version}</span>
                {x.date ? (
                  <small className="ac-ltr">
                    {" · "}
                    {x.date}
                  </small>
                ) : null}
              </h3>
            </div>
          </div>
          <p className="ac-time-title" lang={x.english ? "en" : undefined}>
            {x.title}
          </p>
          <p className="ac-small ac-time-summary" lang={x.english ? "en" : undefined}>
            {x.summary}
          </p>
          <Link className="ac-link" href={x.href}>
            {labels.open} <span className="ac-flip">→</span>
          </Link>
        </li>
      ))}
    </ol>
  );
}
