'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import ScrollyVideoController from 'scrolly-video/dist/ScrollyVideo.js';
import { Glass } from '@samasante/liquid-glass';
import { asset } from '@/lib/site';

/*
 * The home: the home-theatre template's app/page.tsx, line for line, with Corvus content. Only the strings, the
 * film's URL and the CTA's href differ from the template, plus three additions it has no place for: a liquid-glass
 * link pill in its nav, and two sections below the hero (the models and the rest of the site) built from the
 * template's own type and CTA on liquid-glass cards, then the thirteen languages.
 */

const heroVideo = asset('cinema/hero/hero.mp4');

export interface HomeLink {
  key: string;
  href: string;
  label: string;
}

export interface HomeCard {
  key: string;
  href: string;
  eyebrow: string;
  title: string;
  body: string;
  icon: string | null;
}

export interface HomeContent {
  wordmark: string;
  homeLabel: string;
  heroLabel: string;
  title: [string, string];
  lede: string;
  cta: string;
  ctaHref: string;
  nav: HomeLink[];
  navLabel: string;
  loader: { top: string; muted: string; eyebrow: string; title: string; bottom: string };
  models: { eyebrow: string; title: string; lede: string; open: string; cards: HomeCard[] };
  explore: { eyebrow: string; title: string; open: string; cards: HomeCard[] };
  languages: { label: string; current: string; links: HomeLink[] };
}

class SmoothScrollyVideo extends ScrollyVideoController {
  private lastPaintedFrame = -1;

  override async decodeVideo() {
    if (
      this.video.readyState < HTMLMediaElement.HAVE_METADATA ||
      !Number.isFinite(this.video.duration)
    ) {
      await new Promise<void>((resolve) => {
        const finish = () => {
          this.video.removeEventListener('loadedmetadata', finish);
          this.video.removeEventListener('error', finish);
          resolve();
        };

        this.video.addEventListener('loadedmetadata', finish, { once: true });
        this.video.addEventListener('error', finish, { once: true });
      });
    }

    await super.decodeVideo();
  }

  override paintCanvasFrame(frameNumber: number) {
    const frameIndex = Math.max(
      0,
      Math.min(this.frames.length - 1, frameNumber),
    );
    const frame = this.frames[frameIndex] as ImageBitmap | undefined;

    if (
      !this.canvas ||
      !this.context ||
      !frame ||
      frameIndex === this.lastPaintedFrame
    ) {
      return;
    }

    if (this.canvas.width !== frame.width || this.canvas.height !== frame.height) {
      this.canvas.width = frame.width;
      this.canvas.height = frame.height;
    }

    this.context.drawImage(frame, 0, 0, frame.width, frame.height);
    this.lastPaintedFrame = frameIndex;
  }
}

function ScrollyHero({ onReady }: { onReady: () => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const readyRef = useRef(false);

  const markReady = useCallback(() => {
    if (readyRef.current) return;
    readyRef.current = true;
    onReady();
  }, [onReady]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let controller: SmoothScrollyVideo | null = null;
    let destroyed = false;
    readyRef.current = false;

    const revealWhenVisible = () => {
      if (destroyed || !controller) return;

      const { video, canvas, frames } = controller;

      if (canvas && frames.length > 0) {
        const duration = video.duration;
        if (Number.isFinite(duration) && duration > 0) {
          controller.frameRate = frames.length / duration;
          controller.updateScrollPercentage(true);
          controller.paintCanvasFrame(
            Math.floor(controller.currentTime * controller.frameRate),
          );
        }

        window.requestAnimationFrame(markReady);
        return;
      }

      if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
        window.requestAnimationFrame(markReady);
      } else {
        video.addEventListener('loadeddata', markReady, { once: true });
        video.addEventListener('canplay', markReady, { once: true });
      }
    };

    controller = new SmoothScrollyVideo({
      src: heroVideo,
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

    return () => {
      destroyed = true;
      controller?.destroy();
    };
  }, [markReady]);

  return (
    <div className="hero-track">
      <div ref={containerRef} data-scrolly-container />
    </div>
  );
}

/** A liquid-glass card: the template's Syne heading, its 14px body and its text CTA, on the glass material. */
function GlassCard({ card, open }: { card: HomeCard; open: string }) {
  return (
    <Glass className="glass-card">
      <a className="glass-card__link" href={card.href}>
        <span className="glass-card__eyebrow">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          {card.icon ? <img src={card.icon} alt="" width={18} height={18} /> : null}
          <span>{card.eyebrow}</span>
        </span>
        <span className="glass-card__title">{card.title}</span>
        <span className="glass-card__body">{card.body}</span>
        <span className="text-cta glass-card__cta">
          {open} <span aria-hidden="true">→</span>
        </span>
      </a>
    </Glass>
  );
}

export default function Home({ content: c }: { content: HomeContent }) {
  const [siteReady, setSiteReady] = useState(false);
  const [videoReady, setVideoReady] = useState(false);
  const isReady = siteReady && videoReady;

  // Never let the hero strand the page on its loading screen. The film is
  // fetched over the network, so "ready" depends on the visitor's connection
  // and may simply never arrive — and without this the site never shows itself
  // at all. Same guard the other templates in this set use.
  useEffect(() => {
    const film = window.setTimeout(() => setVideoReady(true), 6000);
    const reveal = window.setTimeout(() => setSiteReady(true), 9000);
    return () => {
      window.clearTimeout(film);
      window.clearTimeout(reveal);
    };
  }, []);
  const handleVideoReady = useCallback(() => setVideoReady(true), []);

  // Past the hero, the fixed wordmark sits on a glass pill, so it never runs over the sections' text.
  const [pastHero, setPastHero] = useState(false);
  useEffect(() => {
    const hero = document.getElementById('top');
    if (!hero) return;
    const update = () => setPastHero(hero.getBoundingClientRect().bottom < window.innerHeight * 0.5);
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    const markSiteReady = () => {
      const fontsReady = document.fonts?.ready ?? Promise.resolve();

      void fontsReady.then(() => {
        window.requestAnimationFrame(() => {
          if (!cancelled) setSiteReady(true);
        });
      });
    };

    if (document.readyState === 'complete') {
      markSiteReady();
    } else {
      window.addEventListener('load', markSiteReady, { once: true });
    }

    return () => {
      cancelled = true;
      window.removeEventListener('load', markSiteReady);
    };
  }, []);

  return (
    <>
      <main className={`site-shell${isReady ? ' is-ready' : ''}`} aria-busy={!isReady}>
      <header className={`site-nav${pastHero ? ' is-past' : ''}`}>
        {pastHero ? (
          <Glass className="site-nav__mark">
            <a className="wordmark" href="#top" aria-label={c.homeLabel}>
              {c.wordmark}
            </a>
          </Glass>
        ) : (
          <a className="wordmark" href="#top" aria-label={c.homeLabel}>
            {c.wordmark}
          </a>
        )}
        <Glass className="site-nav__glass">
          <nav aria-label={c.navLabel} className="site-nav__links">
            {c.nav.map((l) => (
              <a key={l.key} href={l.href}>
                {l.label}
              </a>
            ))}
          </nav>
        </Glass>
      </header>

      <section className="hero-scroll" id="top" aria-label={c.heroLabel}>
        <ScrollyHero onReady={handleVideoReady} />

        <div className="hero-stage">
          <div className="hero-shade" aria-hidden="true" />

          <div className="hero-content">
            <h1>{c.title[0]}<br />{c.title[1]}</h1>
            <p>{c.lede}</p>
            <a className="text-cta" href={c.ctaHref}>
              {c.cta} <span aria-hidden="true">→</span>
            </a>
          </div>
        </div>
      </section>

      <section className="home-band" id="models" aria-labelledby="home-models-h">
        <p className="home-band__eyebrow">{c.models.eyebrow}</p>
        <h2 id="home-models-h" className="home-band__title">{c.models.title}</h2>
        <p className="home-band__lede">{c.models.lede}</p>
        <div className="home-band__grid">
          {c.models.cards.map((card) => (
            <GlassCard key={card.key} card={card} open={c.models.open} />
          ))}
        </div>
      </section>

      <section className="home-band" id="explore" aria-labelledby="home-explore-h">
        <p className="home-band__eyebrow">{c.explore.eyebrow}</p>
        <h2 id="home-explore-h" className="home-band__title">{c.explore.title}</h2>
        <div className="home-band__grid home-band__grid--three">
          {c.explore.cards.map((card) => (
            <GlassCard key={card.key} card={card} open={c.explore.open} />
          ))}
        </div>
      </section>

      <footer className="home-foot">
        <span>{c.wordmark}</span>
        <nav aria-label={c.languages.label} className="home-foot__langs">
          {c.languages.links.map((l) => (
            <a key={l.key} href={l.href} hrefLang={l.key} aria-current={l.key === c.languages.current ? 'page' : undefined}>
              {l.label}
            </a>
          ))}
        </nav>
      </footer>
      </main>

      <div
        className={`loading-screen${isReady ? ' is-complete' : ''}`}
        role="status"
        aria-live="polite"
        aria-label={c.loader.bottom}
        aria-hidden={isReady}
      >
        <div className="loading-screen__top">
          <span>{c.loader.top}</span>
          <span className="loading-screen__muted">{c.loader.muted}</span>
        </div>

        <div className="loading-screen__center">
          <span className="loading-screen__eyebrow">{c.loader.eyebrow}</span>
          <span className="loading-screen__title">{c.loader.title}</span>
        </div>

        <div className="loading-screen__bottom">
          <span className="loading-screen__muted">{c.loader.bottom}</span>
          <span className="loading-screen__indicator" aria-hidden="true" />
        </div>
      </div>
    </>
  );
}
