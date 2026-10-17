"use client";

import Link from "next/link";
import { useState } from "react";
import { chime } from "@/engine/audio";
import { asset } from "@/lib/site";

export interface RingItem {
  id: string;
  icon: string;
  name: string;
  jp: string | null;
  badge: string | null;
  category: string;
  tagline: string;
  /** Shown for an archived brand: why it is archived. */
  about: string | null;
  status: string;
  available: boolean;
  archived: boolean;
  href: string;
}

/**
 * The brands of the Store's hub: one mark per model, and a details card for the mark that is
 * hovered, focused or pressed (the first one by default). Each mark is a button, so the whole
 * list works with a keyboard and without scripts' pointer tricks.
 */
export function BrandRing({
  items,
  title,
  hint,
  readMore,
}: {
  items: RingItem[];
  title: string;
  hint: string;
  readMore: string;
}) {
  const [hover, setHover] = useState<number | null>(null);
  const [tapped, setTapped] = useState<number | null>(null);
  const shown = hover ?? tapped ?? 0;
  const item = items[shown] ?? items[0]!;

  return (
    <div className="ac-hub-ring">
      <div className="ac-hub-ring-head">
        <h2 className="ac-h2">{title}</h2>
        <p className="ac-lead">{hint}</p>
      </div>
      <ul className="ac-hub-marks">
        {items.map((m, i) => (
          <li key={m.id}>
            <button
              type="button"
              className="ac-hub-mark"
              aria-pressed={shown === i}
              aria-label={m.name}
              title={m.name}
              data-dim={m.archived}
              onPointerEnter={(e) => {
                if (e.pointerType !== "touch") setHover(i);
              }}
              onPointerLeave={() => setHover(null)}
              onFocus={() => setHover(i)}
              onBlur={() => setHover(null)}
              onClick={() => {
                setTapped(i);
                chime("tick");
              }}
            >
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset(m.icon)} alt="" width={44} height={44} />
            </button>
          </li>
        ))}
      </ul>
      <article className="ac-hub-card ac-card" aria-live="polite" aria-label={item.name} data-brand={item.id}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img className="ac-hub-card-icon" src={asset(item.icon)} alt="" width={64} height={64} data-dim={item.archived} />
        <div className="ac-hub-card-copy">
          <div className="ac-hub-card-name">
            <h3>{item.name}</h3>
            {item.jp ? <span lang="ja">{item.jp}</span> : null}
            {item.badge ? <span className="ac-hub-badge">{item.badge}</span> : null}
          </div>
          <p className="ac-hub-card-cat">{item.category}</p>
          <p className="ac-hub-card-tag">{item.tagline}</p>
          {item.archived && item.about ? <p className="ac-small">{item.about}</p> : null}
        </div>
        <div className="ac-hub-card-side">
          <span className="ac-hub-status" data-on={item.available}>
            {item.status}
          </span>
          <Link className="ac-link" href={item.href}>
            {item.name} <span className="ac-flip">{readMore}</span>
          </Link>
        </div>
      </article>
    </div>
  );
}
