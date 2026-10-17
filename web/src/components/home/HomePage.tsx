import Link from "next/link";
import { FRESH, fill } from "@/i18n/fresh";
import { asset, pathOf, recipeIcon } from "@/lib/site";
import { langData, wiki } from "@/lib/wiki";
import type { Lang, Release } from "@/lib/wiki-types";
import { BRAND_COLOR, BRAND_ICON } from "@/lib/brands";
import { NaturalCinemaStage } from "../cinema/NaturalCinemaStage";
import { AltitudeStream, type StreamRelease } from "./AltitudeStream";
import { CopyButton } from "../CopyButton";
import { FeedTelemetry } from "../discord/FeedTelemetry";
import { CodexPreview, type FeaturedRecipe } from "./CodexPreview";
import { ShowroomPreview } from "./ShowroomPreview";
import { StorePreview } from "./StorePreview";


/**
 * The codex realm's three recipes: an OUKA ammunition, the OUKA alloy ingot, the crucible's fusion. ASTRAEA's
 * recipes stay in the sheet as history, but ASTRAEA's service has ended (2026-10-16), so it is not featured here.
 */
const FEATURED = ["ouka:ammo_energy", "ouka:ouka_alloy_ingot", "cherry:astral_catalyst"] as const;

/**
 * The home page: Act I (the natural cinema stage), the brands, then the five realms the particles travel
 * through as the page scrolls (codex, showroom, store, time, nexus) and the explore grid.
 */
export function HomePage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const w = wiki();
  const f = FRESH[lang];
  const h = d.home;
  const p = d.products;
  const t = d.launcher.text;
  const status = (id: string): string =>
    p[id]?.availability === "soon" ? t.comingSoon : p[id]?.availability === "archived" ? t.archived : t.available;

  // The marks the hero carries, in its order. ASTRAEA is not one of them since its service ended (2026-10-16); its
  // page is still in the Models menu, last.
  const cards = [
    { id: "halia", name: "Halia", jp: null, line: p.halia?.tagline ?? "", href: pathOf(lang, "halia/"), icon: "icons/halia.png", status: status("halia") },
    { id: "ouka", name: "OUKA", jp: null, line: p.ouka?.lede ?? "", href: pathOf(lang, "ouka/"), icon: "icons/ouka.png", status: status("ouka") },
    { id: "cherry", name: "Cherry", jp: null, line: p.cherry?.lede ?? "", href: pathOf(lang, "cherry/"), icon: "icons/cherry.png", status: status("cherry") },
    { id: "tsubomi", name: "Tsubomi", jp: p.tsubomi?.jp ?? null, line: p.tsubomi?.tagline ?? "", href: pathOf(lang, "tsubomi/"), icon: "icons/tsubomi.png", status: status("tsubomi") },
    { id: "noctua", name: p.noctua?.name ?? "Noctua", jp: p.noctua?.jp ?? null, line: p.noctua?.tagline ?? "", href: pathOf(lang, "noctua/"), icon: "icons/noctua.png", status: status("noctua"), soon: p.noctua?.availability !== "available" },
    { id: "store", name: h.ctaStore, jp: null, line: h.storeTagline, href: pathOf(lang, "launcher/"), icon: "icons/store.png", status: `${d.chrome.launcherVersion} ${d.launcherFiles.version}` },
  ];

  // Codex: real recipes, prepared exactly as the codex prepares them.
  const R = w.recipes;
  const rl = d.recipes.labels;
  const itemName = (id: string): string => d.recipes.names[id] ?? R.items[id]?.en ?? id;
  const stationName = (id: string): string => {
    if (id === "tsubomi") return rl.tsubomiName;
    const st = R.stations.find((s) => s.id === id);
    return st?.item ? itemName(st.item) : id;
  };
  const featured: FeaturedRecipe[] = FEATURED.flatMap((id) => {
    const rec = R.recipes.find((r) => r.result === id);
    const it = R.items[id];
    if (rec === undefined || it === undefined) return [];
    const ingredients = rec.grid
      ? rec.grid.flatMap((cell, slot) =>
          cell === 0 ? [] : [{ slot, icon: recipeIcon(R.items[cell]?.icon ?? null), kind: R.items[cell]?.kind ?? ("none" as const) }],
        )
      : (rec.fusion ?? []).flatMap((x) =>
          Array.from({ length: Math.min(x.n, 3) }, () => ({ slot: -1, icon: recipeIcon(R.items[x.id]?.icon ?? null), kind: R.items[x.id]?.kind ?? ("none" as const) })),
        );
    return [{ key: rec.key, name: itemName(id), station: fill(rl.madeIn, stationName(rec.station)), result: { icon: recipeIcon(it.icon), kind: it.kind }, ingredients }];
  });
  // The skin showroom holds ASTRAEA's blade only while ASTRAEA is offered; it is not, so the showroom is bladeless.
  const blade = null;

  // Time: the latest release of each brand, newest first, then what comes next.
  const c = d.changelog;
  const latest = c.brands
    .map((b) => ({ brand: b, release: b.releases[0] }))
    .filter((x): x is { brand: (typeof c.brands)[number]; release: Release } => x.release !== undefined)
    .sort((a, b) => (b.release.date ?? "9999").localeCompare(a.release.date ?? "9999"));

  // Nexus: a taste of the command list.
  const k = d.discord;
  const commands = k.groups.flatMap((g) => g.subcommands.filter((s) => !s.admin).map((s) => ({ cmd: `/${g.name} ${s.name}`, gloss: s.gloss }))).slice(0, 5);

  // The altitude stream: the latest releases of every model but Alpha (archived), newest first.
  const altitude: StreamRelease[] = c.brands
    .filter((b) => b.id !== "alpha")
    .flatMap((b) => b.releases.map((r) => ({ r, b })))
    .sort((x, y) => (y.r.date ?? "").localeCompare(x.r.date ?? ""))
    .slice(0, 10)
    .map(({ r, b }) => ({
      key: r.id,
      href: `${pathOf(lang, "changelog/")}?model=${b.id}`,
      icon: BRAND_ICON[b.id] ?? "icons/store.png",
      brand: b.name,
      version: r.version,
      date: r.date,
      title: r.title,
      color: BRAND_COLOR[b.id] ?? "#2997ff",
    }));

  const explore = [
    { href: "launcher/", title: d.launcher.title, body: d.launcher.description },
    { href: "announcement/", title: f.announcement.title, body: f.announcement.description },
    { href: "changelog/", title: c.title, body: c.description },
    { href: "recipes/", title: d.recipes.navTitle, body: d.recipes.description },
    { href: "skin/", title: d.skin.title, body: h.skinTile },
    { href: "discord/", title: k.title, body: k.description },
  ];

  return (
    <>
      <NaturalCinemaStage
        title="HALIA"
        title2="CORVUS"
        title3="AURORA CORVUS"
        tagline={f.cinema.tagline}
        tagline2={f.cinema.tagline2}
        tagline3={f.cinema.tagline3}
        credit={f.cinema.credit}
        hint={f.heroScroll}
      />

      <AltitudeStream
        title={f.altitude.title}
        lede={f.altitude.lede}
        openLabel={f.chrono.open}
        backdrop="cinema/act3/bg/f196.webp"
        releases={altitude}
      />

      <section className="ac-wrap ac-brands" aria-labelledby="ac-brands-title">
        <h2 id="ac-brands-title" className="ac-eyebrow">
          {h.brandsTitle}
        </h2>
        <ul className="ac-brand-cards">
          {cards.map((x, i) => (
            <li key={x.id}>
              <Link href={x.href} className="ac-brand-card ac-card" data-mark={i} data-soon={x.soon ? "true" : undefined}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={asset(x.icon)} alt="" width={52} height={52} />
                <span>
                  <b>
                    {x.name}
                    {x.jp ? (
                      <i lang="ja" className="ac-jp">
                        {x.jp}
                      </i>
                    ) : null}
                  </b>
                  <span>{x.line}</span>
                  <em>{x.status}</em>
                </span>
              </Link>
            </li>
          ))}
        </ul>
      </section>

      <section
        className="ac-realm"
        aria-labelledby="realm-codex-h"
      >
        <div className="ac-wrap ac-realm-grid">
          <div className="ac-realm-copy">
            <p className="ac-eyebrow ac-reveal">{f.realms.codex.eyebrow}</p>
            <h2 id="realm-codex-h" className="ac-h2 ac-reveal">
              {f.realms.codex.title}
            </h2>
            <p className="ac-lead ac-reveal">{f.realms.codex.lede}</p>
            <p className="ac-reveal">
              <Link className="ac-btn" href={pathOf(lang, "recipes/")}>
                {f.realms.codex.cta}
              </Link>
            </p>
          </div>
          <CodexPreview
            recipes={featured}
            labels={{ synthesise: f.synth.synthesise, featured: f.synth.featured, result: f.synth.result, fusing: f.synth.fusing, drag: rl.preview.drag, title: rl.preview.title }}
          />
        </div>
      </section>

      <section
        className="ac-realm ac-realm--flip"
        aria-labelledby="realm-showroom-h"
      >
        <div className="ac-wrap ac-realm-grid">
          <div className="ac-realm-copy">
            <p className="ac-eyebrow ac-reveal">{f.realms.showroom.eyebrow}</p>
            <h2 id="realm-showroom-h" className="ac-h2 ac-reveal">
              {f.realms.showroom.title}
            </h2>
            <p className="ac-lead ac-reveal">{f.realms.showroom.lede}</p>
            <p className="ac-reveal">
              <Link className="ac-btn" href={pathOf(lang, "skin/")}>
                {f.realms.showroom.cta}
              </Link>
            </p>
          </div>
          <ShowroomPreview
            bladeIcon={blade}
            skinFile={w.skinPublic?.file ?? null}
            labels={{
              idle: f.skin.idle,
              walk: d.skin.labels.walk,
              combat: f.skin.combat,
              motion: f.skin.motion,
              drag: d.skin.labels.drag,
              sealed: f.skin.sealedModel,
              noWebgl: d.skin.labels.noWebgl,
              portrait: f.skinPreview.title,
            }}
          />
        </div>
      </section>

      <section
        className="ac-realm"
        aria-labelledby="realm-store-h"
      >
        <div className="ac-wrap ac-realm-grid">
          <div className="ac-realm-copy">
            <p className="ac-eyebrow ac-reveal">{f.realms.store.eyebrow}</p>
            <h2 id="realm-store-h" className="ac-h2 ac-reveal">
              {f.realms.store.title}
            </h2>
            <p className="ac-lead ac-reveal">{f.realms.store.lede}</p>
            <p className="ac-reveal ac-realm-actions">
              <Link className="ac-btn" href={pathOf(lang, "launcher/")}>
                {f.realms.store.cta}
              </Link>
              <Link className="ac-link" href={pathOf(lang, "launcher/#hub-get")}>
                {f.store.installers} <span className="ac-flip">{d.chrome.arrow}</span>
              </Link>
            </p>
          </div>
          {p.ouka ? (
            <StorePreview
              product={p.ouka}
              text={t}
              jar={d.launcher.storeStrings}
              speed={f.store.speed}
              timeLeft={f.store.timeLeft}
              nowPlaying={f.store.nowPlaying}
              track={d.brands.ouka.player.track}
            />
          ) : null}
        </div>
      </section>

      <section
        id="realm-chrono"
        className="ac-realm ac-realm--time"
        aria-labelledby="realm-chrono-h"
      >
        <div className="ac-wrap ac-time-head">
          <p className="ac-eyebrow ac-reveal">{f.realms.chronology.eyebrow}</p>
          <h2 id="realm-chrono-h" className="ac-h2 ac-reveal">
            {f.realms.chronology.title}
          </h2>
          <p className="ac-lead ac-reveal">{f.realms.chronology.lede}</p>
          <p className="ac-small ac-reveal">{f.chrono.hint}</p>
        </div>
        <ol className="ac-wrap ac-time-list">
          {latest.map(({ brand, release }, i) => (
            <li key={release.id} className="ac-time-card ac-card ac-reveal" data-side={i % 2 === 0 ? "a" : "b"} data-brand={brand.id}>
              <span className="ac-time-dot" aria-hidden="true" style={{ background: BRAND_COLOR[brand.id] ?? "#2997ff" }} />
              <div className="ac-time-top">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={asset(BRAND_ICON[brand.id] ?? "icons/store.png")} alt="" width={44} height={44} data-dim={brand.id === "alpha"} />
                <div>
                  <p className="ac-eyebrow">
                    {i === 0 ? f.chrono.now : f.chrono.shipped} · {brand.name}
                  </p>
                  <h3>
                    <span className="ac-ltr">{release.version}</span>
                    {release.date ? (
                      <small className="ac-ltr">
                        {" · "}
                        {release.date}
                      </small>
                    ) : null}
                  </h3>
                </div>
              </div>
              <p className="ac-time-title" lang={brand.id === "corvus" ? "en" : undefined}>
                {release.title}
              </p>
              <p className="ac-small ac-time-summary" lang={brand.id === "corvus" ? "en" : undefined}>
                {release.summary}
              </p>
              <Link className="ac-link" href={`${pathOf(lang, "changelog/")}?model=${brand.id}`}>
                {f.chrono.open} <span className="ac-flip">{d.chrome.arrow}</span>
              </Link>
            </li>
          ))}
        </ol>
        <div className="ac-wrap ac-time-foot ac-reveal">
          <Link className="ac-btn" href={pathOf(lang, "changelog/")}>
            {f.realms.chronology.cta}
          </Link>
          <Link className="ac-btn ac-btn--ghost" href={pathOf(lang, "announcement/")}>
            {f.realms.chronology.ctaNext}
          </Link>
        </div>
      </section>

      <section
        className="ac-realm ac-realm--flip"
        aria-labelledby="realm-nexus-h"
      >
        <div className="ac-wrap ac-realm-grid">
          <div className="ac-realm-copy">
            <p className="ac-eyebrow ac-reveal">{f.realms.nexus.eyebrow}</p>
            <h2 id="realm-nexus-h" className="ac-h2 ac-reveal">
              {f.realms.nexus.title}
            </h2>
            <p className="ac-lead ac-reveal">{f.realms.nexus.lede}</p>
            <p className="ac-reveal ac-realm-actions">
              <Link className="ac-btn" href={pathOf(lang, "discord/")}>
                {f.realms.nexus.cta}
              </Link>
              {w.discord.invite ? (
                <>
                  <a className="ac-btn ac-btn--ghost" href={w.discord.invite} target="_blank" rel="noopener noreferrer">
                    {k.invite}
                  </a>
                  <CopyButton text={w.discord.invite} label={f.nexus.copyInvite} done={d.chrome.copied} />
                </>
              ) : null}
            </p>
          </div>
          <div className="ac-preview ac-nexus-preview">
            <FeedTelemetry
              lazy
              labels={{
                feeds: f.nexus.feeds,
                ping: f.nexus.ping,
                pinging: f.nexus.pinging,
                latency: f.nexus.latency,
                measured: f.nexus.measured,
                unreachable: f.nexus.unreachable,
              }}
            />
            <div className="ac-term ac-card ac-term--cmds" role="group" aria-label={f.nexus.commands}>
              <div className="ac-term-bar" aria-hidden="true">
                <i />
                <i />
                <i />
                <span>corvus@nexus — {f.nexus.terminal}</span>
              </div>
              <ul className="ac-term-body ac-term-cmds">
                {commands.map((x) => (
                  <li key={x.cmd}>
                    <code className="ac-ltr">
                      <span className="ac-term-prompt">$</span> {x.cmd}
                    </code>
                    <span className="ac-small">{x.gloss}</span>
                    <CopyButton text={x.cmd} label={d.chrome.copy} done={d.chrome.copied} />
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      <section className="ac-section ac-explore" aria-labelledby="ac-explore-h">
        <div className="ac-wrap">
          <h2 id="ac-explore-h" className="ac-h2">
            {h.explore}
          </h2>
          <div className="ac-tiles">
            {explore.map((x) => (
              <Link key={x.href} className="ac-tile ac-card ac-reveal" href={pathOf(lang, x.href)}>
                <h3>{x.title}</h3>
                <p>{x.body}</p>
                <span className="ac-link" aria-hidden="true">
                  <span className="ac-flip">{d.chrome.arrow}</span>
                </span>
              </Link>
            ))}
          </div>
        </div>
      </section>
    </>
  );
}
