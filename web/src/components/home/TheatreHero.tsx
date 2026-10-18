"use client";

import Link from "next/link";
import { type CSSProperties, useCallback, useEffect, useRef, useState } from "react";
import type ScrollyVideoController from "scrolly-video/dist/ScrollyVideo.js";

/** One chapter of the theatre: a model in MODEL_ORDER (or the closing Store block when `cta`). */
export interface TheatreChapter {
  key: string;
  eyebrow: string;
  title: string[];
  lede: string;
  href: string;
  link: string;
  accent: string;
  icon: string | null;
}

export interface TheatreProps {
  label: string;
  /** The film, desktop and phone (all-intra mp4s composited from the three cinema acts). */
  src: string;
  srcSmall: string;
  chapters: TheatreChapter[];
}

/** Scroll, in viewport heights, given to each chapter; the template gives its single copy block 215vh. */
const CHAPTER_VH = 110;

/**
 * The template's ScrollyVideo subclass, unchanged in behaviour: wait for the metadata before decoding, and paint a
 * frame only when it changes (sizing the canvas to the frame).
 */
async function makeController(): Promise<typeof ScrollyVideoController> {
  const mod = await import("scrolly-video/dist/ScrollyVideo.js");
  const Base = mod.default;
  class SmoothScrollyVideo extends Base {
    private lastPaintedFrame = -1;

    override async decodeVideo(): Promise<void> {
      if (this.video.readyState < HTMLMediaElement.HAVE_METADATA || !Number.isFinite(this.video.duration)) {
        await new Promise<void>((resolve) => {
          const finish = (): void => {
            this.video.removeEventListener("loadedmetadata", finish);
            this.video.removeEventListener("error", finish);
            resolve();
          };
          this.video.addEventListener("loadedmetadata", finish, { once: true });
          this.video.addEventListener("error", finish, { once: true });
        });
      }
      await super.decodeVideo();
    }

    override paintCanvasFrame(frameNumber: number): void {
      const frameIndex = Math.max(0, Math.min(this.frames.length - 1, frameNumber));
      const frame = this.frames[frameIndex] as ImageBitmap | undefined;
      if (!this.canvas || !this.context || !frame || frameIndex === this.lastPaintedFrame) return;
      if (this.canvas.width !== frame.width || this.canvas.height !== frame.height) {
        this.canvas.width = frame.width;
        this.canvas.height = frame.height;
      }
      this.context.drawImage(frame, 0, 0, frame.width, frame.height);
      this.lastPaintedFrame = frameIndex;
    }
  }
  return SmoothScrollyVideo;
}

/** Tells the loading screen the film's first frame is up (it also lifts on its own guards). */
function announceReady(): void {
  document.documentElement.dataset.hero = "ready";
  window.dispatchEvent(new Event("corvus:hero-ready"));
}

/**
 * The home theatre: the template's full-screen scroll-scrubbed film (ScrollyVideo, sticky, cover), its radial shade,
 * and its copy block bottom-left, here one block per chapter (Corvus, then each model in MODEL_ORDER, then the Store)
 * that takes the stage as the film scrolls past.
 */
export function TheatreHero({ label, src, srcSmall, chapters }: TheatreProps) {
  const sectionRef = useRef<HTMLElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const readyRef = useRef(false);
  const [active, setActive] = useState(0);

  const markReady = useCallback(() => {
    if (readyRef.current) return;
    readyRef.current = true;
    announceReady();
  }, []);

  // The film: the template's controller and its reveal, with the same options.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let destroyed = false;
    let controller: InstanceType<typeof ScrollyVideoController> | null = null;
    readyRef.current = false;
    const guard = window.setTimeout(markReady, 6000);

    const revealWhenVisible = (): void => {
      if (destroyed || !controller) return;
      const { video, canvas, frames } = controller;
      if (canvas && frames.length > 0) {
        const duration = video.duration;
        if (Number.isFinite(duration) && duration > 0) {
          controller.frameRate = frames.length / duration;
          controller.updateScrollPercentage(true);
          controller.paintCanvasFrame(Math.floor(controller.currentTime * controller.frameRate));
        }
        window.requestAnimationFrame(markReady);
        return;
      }
      if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) window.requestAnimationFrame(markReady);
      else {
        video.addEventListener("loadeddata", markReady, { once: true });
        video.addEventListener("canplay", markReady, { once: true });
      }
    };

    void makeController().then((Ctor) => {
      if (destroyed) return;
      const small = window.matchMedia("(max-width: 800px)").matches;
      controller = new Ctor({
        src: small ? srcSmall : src,
        scrollyVideoContainer: container,
        sticky: true,
        full: true,
        cover: true,
        trackScroll: true,
        lockScroll: false,
        transitionSpeed: 64,
        frameThreshold: 1 / 60,
        useWebCodecs: true,
        onReady: revealWhenVisible,
      });
    });

    return () => {
      destroyed = true;
      window.clearTimeout(guard);
      controller?.destroy();
    };
  }, [src, srcSmall, markReady]);

  // The chapter on stage follows the section's scroll progress.
  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;
    let raf = 0;
    const update = (): void => {
      raf = 0;
      const r = section.getBoundingClientRect();
      const span = r.height - window.innerHeight;
      const p = span > 0 ? Math.min(1, Math.max(0, -r.top / span)) : 0;
      setActive(Math.min(chapters.length - 1, Math.floor(p * chapters.length)));
    };
    const onScroll = (): void => {
      if (raf === 0) raf = window.requestAnimationFrame(update);
    };
    update();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
      if (raf !== 0) window.cancelAnimationFrame(raf);
    };
  }, [chapters.length]);

  return (
    <section
      ref={sectionRef}
      className="th-scroll"
      aria-label={label}
      data-theatre=""
      style={{ "--th-h": `${chapters.length * CHAPTER_VH}vh` } as CSSProperties}
    >
      <div className="th-track">
        <div ref={containerRef} data-scrolly-container="" />
      </div>
      <div className="th-stage">
        <div className="th-shade" aria-hidden="true" />
        {chapters.map((c, i) => {
          const Heading = i === 0 ? "h1" : "h2";
          return (
            <div
              key={c.key}
              className={`th-content${i === active ? " is-active" : ""}`}
              aria-hidden={i !== active}
              style={{ "--th-accent": c.accent } as CSSProperties}
            >
              <p className="th-eyebrow">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                {c.icon ? <img src={c.icon} alt="" width={18} height={18} /> : null}
                <span>{c.eyebrow}</span>
              </p>
              <Heading className="th-title">
                {c.title.map((line, k) => (
                  <span key={k}>
                    {line}
                    {k < c.title.length - 1 ? <br /> : null}
                  </span>
                ))}
              </Heading>
              <p className="th-lede">{c.lede}</p>
              <Link className="text-cta" href={c.href} tabIndex={i === active ? 0 : -1}>
                {c.link} <span aria-hidden="true" className="ac-flip">→</span>
              </Link>
            </div>
          );
        })}
        <ol className="th-progress" aria-hidden="true">
          {chapters.map((c, i) => (
            <li key={c.key} className={i === active ? "is-active" : ""} />
          ))}
        </ol>
      </div>
    </section>
  );
}
