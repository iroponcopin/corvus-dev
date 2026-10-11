import Link from "next/link";
import { Formation } from "@/engine/store";
import { FRESH } from "@/i18n/fresh";
import { asset, pathOf } from "@/lib/site";
import { langData } from "@/lib/wiki";
import type { Lang, Product } from "@/lib/wiki-types";
import { RealmAnchor } from "../RealmAnchor";
import { TrustedHtml } from "../Rich";
import { Stagger } from "../Stagger";
import { BrandRing, type RingItem } from "../store/BrandRing";
import { StoreSim } from "../store/StoreSim";
import { LauncherFiles } from "./DownloadPage";

const BLUE: readonly [number, number, number] = [0.25, 0.55, 1];

/** The Store's order of its products, and the hub ring's order of the six marks. */
const PRODUCTS = ["halia", "ouka", "cherry", "aureum", "astraea", "tsubomi", "noctua", "alpha"] as const;
const RING = ["astraea", "ouka", "cherry", "tsubomi", "noctua", "alpha"] as const;

/**
 * Corvus Store: the hub (the astrolabe with the six marks in orbit, read one by one as the page
 * scrolls), the Store itself running in the page on its 3D deck, then the installers, the mods,
 * the release notes and the guide.
 */
export function LauncherPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const l = d.launcher;
  const t = l.text;
  const f = FRESH[lang];
  const files = d.launcherFiles;
  const version = files.version;
  const series = version.split(".").slice(0, 2).join(".");
  const products = PRODUCTS.map((id) => d.products[id]).filter((p): p is Product => p !== undefined);
  const status = (p: Product): string =>
    p.availability === "soon" ? t.comingSoon : p.availability === "archived" ? t.archived : t.available;
  const hrefs = Object.fromEntries(products.map((p) => [p.id, pathOf(lang, p.href)]));
  const ring: RingItem[] = RING.map((id) => d.products[id])
    .filter((p): p is Product => p !== undefined)
    .map((p) => ({
      id: p.id,
      icon: p.icon,
      name: p.name,
      jp: p.jp,
      badge: p.badge,
      category: p.category,
      tagline: p.tagline,
      about: p.availability === "archived" ? p.about : null,
      status: status(p),
      available: p.availability === "available",
      archived: p.availability === "archived",
      href: pathOf(lang, p.href),
    }));

  return (
    <>
      <RealmAnchor
        id="hub"
        className="ac-hub"
        aria-label={l.hub.title}
        config={{ formation: Formation.Horizon, x: 0.5, y: 0.34, scale: 0.17, scaleNarrow: 0.19, astrolabe: 1, tint: BLUE }}
      >
        <a className="ac-hub-skip ac-btn ac-btn--ghost ac-btn--small" href="#hub-get">
          {l.hub.skip}
        </a>
        <div className="ac-hub-sticky">
          <div className="ac-hub-poster ac-only-fallback" aria-hidden="true">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={asset("logo.png")} alt="" width={160} height={160} />
          </div>
          <div className="ac-hub-hero">
            <h1 className="ac-display" dir="ltr">
              <Stagger text={l.hub.title} lang="en" />
            </h1>
            <p className="ac-lead">{l.hub.tagline}</p>
          </div>
          <p className="ac-hub-scroll ac-small" aria-hidden="true">
            {l.hub.scroll}
          </p>
          <BrandRing hubId="hub" items={ring} title={l.hub.brandsTitle} hint={l.hub.brandsHint} readMore={t.readMore} />
        </div>
      </RealmAnchor>

      <RealmAnchor
        className="ac-section ac-deck-section"
        aria-labelledby="deck-title"
        config={{ formation: Formation.Store, x: 0.5, y: 0.55, scale: 0.3, scaleNarrow: 0.36, tint: BLUE }}
      >
        <div className="ac-wrap ac-deck-head">
          <p className="ac-eyebrow">{f.realms.store.eyebrow}</p>
          <h2 id="deck-title" className="ac-h2">
            {f.realms.store.title}
          </h2>
          <p className="ac-lead">{f.realms.store.lede}</p>
        </div>
        <div className="ac-wide ac-deck">
          <div className="ac-deck-inner">
            <StoreSim
              products={products}
              hrefs={hrefs}
              labels={{
                text: t,
                jar: l.storeStrings,
                perch: l.perch,
                perchToggle: l.perchToggle,
                fresh: f.store,
                track: d.brands.ouka.player.track,
              }}
            />
          </div>
          <div className="ac-deck-floor" aria-hidden="true" />
        </div>
      </RealmAnchor>

      <section id="hub-get" className="ac-wrap ac-section ac-hub-get" aria-labelledby="hub-get-h">
        <p className="ac-eyebrow">
          {d.chrome.launcherVersion} <span className="ac-ltr">{version}</span>
        </p>
        <h2 id="hub-get-h" className="ac-h2">
          Corvus Store <span className="ac-ltr">{series}</span>
        </h2>
        <p className="ac-lead ac-measure">{l.body}</p>
        <h3 className="ac-eyebrow ac-hub-get-sub">{f.store.installers}</h3>
        <LauncherFiles d={d} />
        <p className="ac-small ac-dl-note">{l.nativeNote}</p>
        <p>
          <Link className="ac-link" href={pathOf(lang, "download/")}>
            {l.hub.downloadLabel} <span className="ac-flip">{d.chrome.arrow}</span>
          </Link>
        </p>
      </section>

      <section className="ac-wrap ac-section ac-hub-block" aria-labelledby="hub-products-h">
        <h2 id="hub-products-h" className="ac-h3">
          {l.modsHeading}
        </h2>
        <div className="ac-hub-products">
          {products.map((p) => {
            const facts = [status(p), p.version, p.compat].filter((x) => x !== "").join(" · ");
            const tier = p.badge ? `${p.badge} · ${p.category}` : p.category;
            const linked = p.availability !== "soon";
            return (
              <article key={p.id} id={p.id} className="ac-hub-product ac-card">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={asset(p.icon)} alt="" width={64} height={64} data-dim={p.availability === "archived"} />
                <div>
                  <h3>
                    {p.name}
                    {p.jp ? (
                      <span lang="ja" className="ac-jp">
                        {p.jp}
                      </span>
                    ) : null}
                  </h3>
                  <p className="ac-small">{tier}</p>
                  <p>{p.tagline}</p>
                  <p className="ac-small">{facts}</p>
                  {linked ? (
                    <Link className="ac-link" href={pathOf(lang, p.href)}>
                      {p.name} <span className="ac-flip">{d.chrome.arrow}</span>
                    </Link>
                  ) : null}
                </div>
              </article>
            );
          })}
        </div>
      </section>

      <section className="ac-wrap ac-section ac-hub-block" aria-labelledby="hub-notes-h">
        <h2 id="hub-notes-h" className="ac-h3">
          {l.whatsNew} · {d.chrome.launcherVersion} <span className="ac-ltr">{version}</span>
        </h2>
        <div lang="en" dir="ltr" className="ac-hub-notes">
          {files.notes.map((n, i) => (
            <p key={i}>{n}</p>
          ))}
        </div>
        <p className="ac-small ac-dl-note">
          {l.notesEnglishOnly}{" "}
          <Link className="ac-link" href={`${pathOf(lang, "changelog/")}?model=corvus`}>
            {l.versionHistory} <span className="ac-flip">{d.chrome.arrow}</span>
          </Link>
        </p>
      </section>

      <section className="ac-wrap ac-section ac-hub-block ac-hub-last" aria-labelledby="hub-guide-h">
        <h2 id="hub-guide-h" className="ac-h3">
          {l.guideTitle}
        </h2>
        <p className="ac-lead ac-measure">{l.guideIntro}</p>
        <p className="ac-small ac-dl-note">{l.guideNote}</p>
        <div className="ac-hub-guide">
          {l.guide.map((g) => (
            <details key={g.id} id={g.id} className="ac-hub-guide-item">
              <summary>{g.title}</summary>
              <TrustedHtml className="ac-hub-guide-body" html={g.html} />
            </details>
          ))}
        </div>
      </section>
    </>
  );
}
