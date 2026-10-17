"use client";

import { useEffect, useRef, useState } from "react";
import { chime } from "@/engine/audio";
import { engine } from "@/engine/store";
import { Stage3D } from "@/engine/View";
import { type SynthIngredient, Synthesizer, type SynthItem } from "@/realms/Synthesizer";
import { Icon } from "../Icon";

export interface FeaturedRecipe {
  key: string;
  name: string;
  station: string;
  result: SynthItem;
  ingredients: SynthIngredient[];
}

/**
 * The codex realm on the home page: three real recipes (a blade, the ingot it is forged from,
 * and the crucible's fusion) synthesised on demand. Drag or use the arrow keys to turn the result.
 */
export function CodexPreview({
  recipes,
  labels,
}: {
  recipes: FeaturedRecipe[];
  labels: { synthesise: string; featured: string; result: string; fusing: string; drag: string; title: string };
}) {
  const [index, setIndex] = useState(0);
  const [playKey, setPlayKey] = useState(0);
  const [fusing, setFusing] = useState(false);
  const turn = useRef(0);
  const drag = useRef<{ x: number; id: number } | null>(null);
  // The ingredients fly for as long as the synthesiser takes to fuse them (its fuseAt).
  useEffect(() => {
    if (playKey === 0 || engine.reducedMotion) return;
    setFusing(true);
    const id = window.setTimeout(() => setFusing(false), 1150);
    return () => window.clearTimeout(id);
  }, [playKey]);

  const r = recipes[index] ?? recipes[0];
  if (r === undefined) return null;

  const play = (i: number): void => {
    setIndex(i);
    setPlayKey((k) => k + 1);
    chime("tick");
  };

  return (
    <div className="ac-preview ac-codex-preview">
      <div
        className="ac-preview-stage"
        tabIndex={0}
        role="group"
        aria-label={`${labels.title}: ${r.name}. ${labels.drag}`}
        onPointerDown={(e) => {
          drag.current = { x: e.clientX, id: e.pointerId };
          e.currentTarget.setPointerCapture(e.pointerId);
        }}
        onPointerMove={(e) => {
          if (drag.current === null || drag.current.id !== e.pointerId) return;
          turn.current += (e.clientX - drag.current.x) * 0.012;
          drag.current.x = e.clientX;
        }}
        onPointerUp={() => {
          drag.current = null;
        }}
        onPointerCancel={() => {
          drag.current = null;
        }}
        onKeyDown={(e) => {
          if (e.key === "ArrowLeft") turn.current -= 0.3;
          else if (e.key === "ArrowRight") turn.current += 0.3;
        }}
      >
        <Stage3D
          className="ac-preview-canvas"
          fov={30}
          position={[0, 0.18, 4.4]}
          fallback={
            r.result.icon ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={r.result.icon} alt="" width={128} height={128} className="ac-pixel" />
            ) : null
          }
        >
          <Synthesizer result={r.result} ingredients={r.ingredients} playKey={playKey * 7 + index} spinning turn={turn} />
        </Stage3D>
        <p className="ac-preview-caption" aria-live="polite">
          <small>{fusing ? labels.fusing : labels.result}</small>
          <b>{r.name}</b>
          <span className="ac-small">{r.station}</span>
        </p>
      </div>
      <div className="ac-preview-controls">
        <span className="ac-small">{labels.featured}</span>
        <div className="ac-chips" role="group" aria-label={labels.featured}>
          {recipes.map((x, i) => (
            <button key={x.key} type="button" className="ac-chip" aria-pressed={i === index} onClick={() => play(i)}>
              {x.result.icon ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={x.result.icon} alt="" width={18} height={18} className="ac-pixel" />
              ) : null}
              {x.name}
            </button>
          ))}
        </div>
        <button type="button" className="ac-btn ac-btn--ghost ac-btn--small" onClick={() => play(index)}>
          <Icon name="sparkle" size={14} />
          {labels.synthesise}
        </button>
      </div>
    </div>
  );
}
