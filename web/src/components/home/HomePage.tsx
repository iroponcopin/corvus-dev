import Link from "next/link";
import { FRESH, fill } from "@/i18n/fresh";
import { pathOf, recipeIcon } from "@/lib/site";
import { langData, recipeModelList, wiki } from "@/lib/wiki";
import type { Lang, Release } from "@/lib/wiki-types";
import { BRAND_COLOR, BRAND_ICON } from "@/lib/brands";
import { NaturalCinemaStage } from "../cinema/NaturalCinemaStage";
import { BentoReleases, type BentoItem } from "./BentoReleases";
import { Lineup, type LineupItem } from "./Lineup";
import { Chronology, type ChronoItem } from "./Chronology";
import { CopyButton } from "../CopyButton";
import { MissionControl } from "./MissionControl";
import { CodexPreview, type FeaturedRecipe } from "./CodexPreview";
import { ShowroomPreview } from "./ShowroomPreview";
import { StorePreview } from "./StorePreview";
import { HOME_V2 } from "@/i18n/home";
import { ENDED_MODELS, inModelOrder, MODEL_ORDER } from "@/lib/models";


/**
 * The codex realm's three recipes: an OUKA ammunition, the OUKA alloy ingot, the crucible's fusion. ASTRAEA's
 * recipes left the sheet with its end of service (2026-10-17), so it is not featured here.
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

  // Time: the latest release of each live model (never ASTRAEA or Alpha), newest first.
  const CHRONO_IDS: readonly string[] = [...MODEL_ORDER.filter((id) => !ENDED_MODELS.includes(id) && id !== "noctua"), "corvus"];
  const c = d.changelog;
  const latest: { brand: (typeof c.brands)[number]; release: Release }[] = c.brands
    .filter((b): b is (typeof c.brands)[number] => CHRONO_IDS.includes(b.id))
    .map((b) => ({ brand: b, release: b.releases[0] }))
    .filter((x): x is { brand: (typeof c.brands)[number]; release: Release } => x.release !== undefined)
    .sort((a, b) => (b.release.date ?? "9999").localeCompare(a.release.date ?? "9999"));
  const chrono: ChronoItem[] = latest.map(({ brand, release }, i) => ({
    key: release.id,
    brand: brand.name,
    icon: BRAND_ICON[brand.id] ?? "icons/store.png",
    color: BRAND_COLOR[brand.id] ?? "#2997ff",
    version: release.version,
    date: release.date,
    title: release.title,
    summary: release.summary,
    href: `${pathOf(lang, "changelog/")}?model=${brand.id}`,
    english: brand.id === "corvus",
    now: i === 0,
  }));

  // Nexus: a taste of the command list.
  const k = d.discord;
  const commands = k.groups.flatMap((g) => g.subcommands.filter((s) => !s.admin).map((s) => ({ cmd: `/${g.name} ${s.name}`, gloss: s.gloss }))).slice(0, 5);

  // The Bento grid: the latest release of each live model (never ASTRAEA or Alpha), by id. Store and Agent read
  // the Store's own entries and the manifest. The pill is the build-time version until the feed answers.
  const BENTO: { key: string; manifest: string; changelog: string | null; size: BentoItem["size"]; href: string }[] = [
    { key: "halia", manifest: "halia", changelog: "halia", size: "xl", href: "halia/" },
    { key: "ouka", manifest: "ouka", changelog: "ouka", size: "l", href: "ouka/" },
    { key: "cherry", manifest: "cherry", changelog: "cherry", size: "m", href: "cherry/" },
    { key: "tsubomi", manifest: "tsubomi", changelog: "tsubomi", size: "m", href: "tsubomi/" },
    { key: "noctua", manifest: "noctua", changelog: null, size: "m", href: "noctua/" },
    { key: "aureum", manifest: "aureum", changelog: "aureum", size: "m", href: "aureum/" },
    { key: "store", manifest: "launcher", changelog: "corvus", size: "l", href: "launcher/" },
    { key: "agent", manifest: "agent", changelog: null, size: "m", href: "launcher/" },
  ];
  // MODEL_ORDER decides the order; Store and Agent (not models) keep their place after every model.
  const byOrder = <T extends { key: string }>(xs: T[]): T[] =>
    inModelOrder(xs.map((x) => x.key)).map((k) => xs.find((x) => x.key === k) as T);
  const bento: BentoItem[] = byOrder(BENTO).map((x) => {
    const brand = x.changelog === null ? undefined : c.brands.find((b) => b.id === x.changelog);
    const rel = brand?.releases[0];
    const prod = p[x.key];
    const name = x.key === "store" ? h.ctaStore : x.key === "agent" ? "Corvus Agent" : prod?.name ?? brand?.name ?? x.key;
    const color = BRAND_COLOR[x.changelog ?? x.key] ?? "#2997ff";
    const entry = rel
      ? { version: rel.version, date: rel.date, title: rel.title, summary: rel.summary, paragraphs: rel.paragraphs ?? [], highlights: rel.highlights, warnings: rel.warnings }
      : { version: prod?.version ?? "", date: null, title: prod?.tagline ?? h.storeTagline, summary: prod?.headline ?? "", paragraphs: [], highlights: [], warnings: [] };
    return {
      key: x.key,
      manifest: x.manifest,
      name,
      icon: BRAND_ICON[x.changelog ?? x.key] ?? (x.key === "store" || x.key === "agent" ? "icons/store.png" : `icons/${x.key}.png`),
      color,
      size: x.size,
      version: rel?.version ?? prod?.version ?? "",
      entry,
      href: pathOf(lang, x.href),
      changelogHref: `${pathOf(lang, "changelog/")}?model=${x.changelog ?? x.key}`,
    };
  });

  // The Lineup: the live models in the Store's order, with corvus Store 5.x last. ASTRAEA and Alpha are not in it.
  const lineup: LineupItem[] = byOrder([
    { key: "halia", name: "Halia", line: p.halia?.tagline ?? "", status: status("halia"), icon: "icons/halia.png", accent: BRAND_COLOR.halia ?? "#2997ff", href: pathOf(lang, "halia/"), demo: "blade" },
    { key: "ouka", name: "OUKA", line: p.ouka?.lede ?? "", status: status("ouka"), icon: "icons/ouka.png", accent: BRAND_COLOR.ouka ?? "#2997ff", href: pathOf(lang, "ouka/"), demo: "power" },
    { key: "cherry", name: "Cherry", line: p.cherry?.lede ?? "", status: status("cherry"), icon: "icons/cherry.png", accent: BRAND_COLOR.cherry ?? "#2997ff", href: pathOf(lang, "cherry/"), demo: null },
    { key: "tsubomi", name: "Tsubomi", line: p.tsubomi?.tagline ?? "", status: status("tsubomi"), icon: "icons/tsubomi.png", accent: BRAND_COLOR.tsubomi ?? "#2997ff", href: pathOf(lang, "tsubomi/"), demo: null },
    { key: "noctua", name: p.noctua?.name ?? "Noctua", line: p.noctua?.tagline ?? "", status: status("noctua"), icon: "icons/noctua.png", accent: BRAND_COLOR.noctua ?? "#2997ff", href: pathOf(lang, "noctua/"), demo: null },
    { key: "aureum", name: "Aureum", line: p.aureum?.tagline ?? "", status: status("aureum"), icon: "icons/aureum.png", accent: BRAND_COLOR.aureum ?? "#2997ff", href: pathOf(lang, "aureum/"), demo: null },
    { key: "store", name: h.ctaStore, line: h.storeTagline, status: `${d.chrome.launcherVersion} ${d.launcherFiles.version}`, icon: "icons/store.png", accent: "#2997ff", href: pathOf(lang, "launcher/"), demo: null },
  ]);

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
        title3="Corvus"
        tagline={f.cinema.tagline}
        tagline2={f.cinema.tagline2}
        closing={HOME_V2[lang].closing}
        credit={f.cinema.credit}
        hint={f.heroScroll}
      />

      <section className="ac-section ac-bento-section" aria-labelledby="ac-bento-h">
        <div className="ac-wrap">
          <h2 id="ac-bento-h" className="ac-h2">
            {HOME_V2[lang].bento.title}
          </h2>
          <p className="ac-lead">{HOME_V2[lang].bento.lede}</p>
          <BentoReleases
            items={bento}
            labels={{ title: HOME_V2[lang].bento.title, lede: HOME_V2[lang].bento.lede, open: HOME_V2[lang].bento.open, close: HOME_V2[lang].bento.close, modal: HOME_V2[lang].bento.modal, pill: HOME_V2[lang].bento.pill }}
          />
        </div>
      </section>

      <Lineup items={lineup} labels={{ title: HOME_V2[lang].lineup.title, lede: HOME_V2[lang].lineup.lede, scrub: HOME_V2[lang].lineup.scrub, open: HOME_V2[lang].lineup.open, power: HOME_V2[lang].lineup.power, blade: HOME_V2[lang].lineup.blade }} />

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
            <p className="ac-lead ac-reveal">{f.realms.codex.lede.replace("{models}", recipeModelList(lang))}</p>
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
        <div className="ac-wrap">
          <Chronology items={chrono} labels={{ now: f.chrono.now, shipped: f.chrono.shipped, open: f.chrono.open }} />
        </div>
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
            <MissionControl
              lazy
              labels={{
                feeds: f.nexus.feeds,
                ping: f.nexus.ping,
                pinging: f.nexus.pinging,
                latency: f.nexus.latency,
                measured: f.nexus.measured,
                unreachable: f.nexus.unreachable,
                inspect: HOME_V2[lang].telemetry.inspect,
                payload: HOME_V2[lang].telemetry.payload,
                bytes: HOME_V2[lang].telemetry.bytes,
                modified: HOME_V2[lang].telemetry.modified,
                truncated: HOME_V2[lang].telemetry.truncated,
                drawer: HOME_V2[lang].telemetry.drawer,
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
