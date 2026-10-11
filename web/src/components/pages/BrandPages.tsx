import Link from "next/link";
import { Formation } from "@/engine/store";
import { pathOf } from "@/lib/site";
import { langData } from "@/lib/wiki";
import type { ControlToken, Lang, Requirement } from "@/lib/wiki-types";
import { BrandStage } from "../BrandStage";
import { CopyButton } from "../CopyButton";
import { RealmAnchor } from "../RealmAnchor";
import { ThemePlayer } from "../ThemePlayer";

const PINK: readonly [number, number, number] = [1, 0.58, 0.74];
const ROSE: readonly [number, number, number] = [1, 0.42, 0.55];
const GOLD: readonly [number, number, number] = [1, 0.72, 0.3];
const ASH: readonly [number, number, number] = [0.7, 0.55, 0.45];
const VIOLET: readonly [number, number, number] = [0.65, 0.55, 1];
const SPRING: readonly [number, number, number] = [0.7, 1, 0.72];
const NIGHT: readonly [number, number, number] = [0.45, 0.55, 1];
/** Halia: the gold of its eagle (owner, 2026-10-11: the accent colour is the bald eagle). */
const EAGLE_GOLD: readonly [number, number, number] = [1, 0.84, 0.5];

function ReleaseCard({
  lang,
  requirements,
  file,
}: {
  lang: Lang;
  requirements: Requirement[];
  file: { url: string; sizeDisplay: string; bytesDisplay: string; sha256: string };
}) {
  const c = langData(lang).chrome;
  return (
    <div className="ac-wrap ac-release">
      <div className="ac-card ac-release-card ac-reveal" id="release">
        <dl className="ac-facts">
          {requirements.map((r) => (
            <div key={r.label}>
              <dt>{r.label}</dt>
              <dd className="ac-ltr">{r.value}</dd>
            </div>
          ))}
          <div>
            <dt>{c.fileSize}</dt>
            <dd className="ac-ltr">
              {file.sizeDisplay} ({file.bytesDisplay} bytes)
            </dd>
          </div>
        </dl>
        <div className="ac-release-side">
          <dl className="ac-facts">
            <div>
              <dt>{c.sha256}</dt>
              <dd>
                <code className="ac-hash">{file.sha256}</code>
                <CopyButton text={file.sha256} label={c.copy} done={c.copied} />
              </dd>
            </div>
          </dl>
          <p className="ac-release-dl">
            <a className="ac-btn" href={file.url} download>
              {c.primaryCta}
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}

export function OukaPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const b = d.brands.ouka;
  const c = d.chrome;
  return (
    <>
      <RealmAnchor className="ac-brand-hero" config={{ formation: Formation.Bloom, x: 0.72, xNarrow: 0.5, scale: 0.34, scaleNarrow: 0.28, tint: PINK }}>
        <div className="ac-wrap ac-brand-grid">
          <div className="ac-brand-copy">
            <p className="ac-eyebrow ac-reveal">{b.eyebrow}</p>
            <h1 className="ac-display ac-brand-name ac-reveal">{b.title}</h1>
            <p className="ac-brand-version ac-reveal">
              <b className="ac-ltr">V{b.release.version}</b>
              <span className="ac-ltr" lang="en">
                {b.release.codename}
              </span>
            </p>
            <p className="ac-brand-line ac-reveal">{b.line}</p>
            <div className="ac-brand-actions ac-reveal">
              <a className="ac-btn" href={b.release.file.url} download>
                {c.primaryCta}
              </a>
              <Link className="ac-link" href={pathOf(lang, "changelog/?model=ouka")}>
                {c.changelog} <span className="ac-flip">{c.arrow}</span>
              </Link>
            </div>
            <div className="ac-reveal">
              <ThemePlayer track={b.player.track} play={b.player.play} pause={b.player.pause} />
            </div>
          </div>
          <BrandStage icon="icons/ouka.png" label={b.title} />
        </div>
      </RealmAnchor>
      <ReleaseCard lang={lang} requirements={b.release.requirements} file={b.release.file} />
    </>
  );
}

export function CherryPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const b = d.brands.cherry;
  const c = d.chrome;
  return (
    <>
      <RealmAnchor className="ac-brand-hero" config={{ formation: Formation.Horizon, x: 0.72, xNarrow: 0.5, scale: 0.3, scaleNarrow: 0.26, tint: ROSE }}>
        <div className="ac-wrap ac-brand-grid">
          <div className="ac-brand-copy">
            <p className="ac-eyebrow ac-reveal">{b.eyebrow}</p>
            <h1 className="ac-display ac-brand-name ac-reveal">{b.title}</h1>
            <p className="ac-brand-version ac-reveal">
              <b className="ac-ltr">V{b.release.version}</b>
              <span className="ac-ltr" lang="en">
                {b.release.codename}
              </span>
            </p>
            <p className="ac-brand-line ac-reveal">{b.line}</p>
            <div className="ac-brand-actions ac-reveal">
              <a className="ac-btn" href={b.release.file.url} download>
                {c.primaryCta}
              </a>
              <Link className="ac-link" href={pathOf(lang, "changelog/?model=cherry")}>
                {c.changelog} <span className="ac-flip">{c.arrow}</span>
              </Link>
              <Link className="ac-link" href={pathOf(lang, "cherry-controls/")}>
                {b.controlsLabel} <span className="ac-flip">{c.arrow}</span>
              </Link>
            </div>
          </div>
          <BrandStage icon="icons/cherry.png" label={b.title} />
        </div>
      </RealmAnchor>
      <ReleaseCard lang={lang} requirements={b.release.requirements} file={b.release.file} />
    </>
  );
}

export function AureumPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const a = d.brands.aureum;
  const c = d.chrome;
  return (
    <>
      <RealmAnchor className="ac-brand-hero" config={{ formation: Formation.Aurum, x: 0.72, xNarrow: 0.5, scale: 0.32, scaleNarrow: 0.26, tint: GOLD }}>
        <div className="ac-wrap ac-brand-grid">
          <div className="ac-brand-copy">
            <p className="ac-eyebrow ac-reveal">
              {c.version} <span className="ac-ltr">{a.version}</span>
            </p>
            <h1 className="ac-display ac-brand-name ac-gold ac-reveal">{a.title}</h1>
            <p className="ac-lead ac-reveal" style={{ maxWidth: "36ch" }}>
              {a.tagline}
            </p>
            <div className="ac-brand-actions ac-reveal">
              <a className="ac-btn" href={a.download.url} download>
                {a.download.label}
              </a>
              <Link className="ac-link" href={pathOf(lang, "download/")}>
                {a.detailsLabel}
              </Link>
            </div>
          </div>
          <BrandStage icon="icons/aureum.png" label={a.title} />
        </div>
      </RealmAnchor>
      <div className="ac-wrap ac-aureum">
        <h2 className="ac-h3 ac-reveal">{a.statsHeading}</h2>
        <div className="ac-stats">
          {a.stats.map((s, i) => (
            <div key={s.label} className="ac-stat ac-card ac-reveal" style={{ ["--ac-i" as string]: i }}>
              <b className="ac-ltr">{s.value}</b>
              <span>{s.label}</span>
            </div>
          ))}
        </div>
        <div className="ac-sections">
          {a.sections.map((s) => (
            <section key={s.heading} className="ac-card ac-section-card ac-reveal">
              <h2 className="ac-h3">{s.heading}</h2>
              {s.paragraphs.map((p) => (
                <p key={p.slice(0, 32)}>{p}</p>
              ))}
              {s.requirements ? (
                <>
                  <h2 className="ac-h3 ac-req-head">{s.requirements.heading}</h2>
                  <ul className="ac-ltr ac-req">
                    {s.requirements.items.map((r) => (
                      <li key={r}>{r}</li>
                    ))}
                  </ul>
                </>
              ) : null}
            </section>
          ))}
        </div>
        <p className="ac-small ac-aureum-note ac-reveal">
          {a.closingLine} · {c.version} <span className="ac-ltr">{a.version}</span> · {c.sha256}{" "}
          <code className="ac-hash">{a.sha256}</code>
        </p>
        <p className="ac-aureum-log">
          <Link className="ac-link" href={pathOf(lang, "changelog/?model=aureum")}>
            {c.changelog} <span className="ac-flip">{c.arrow}</span>
          </Link>
        </p>
      </div>
    </>
  );
}

/** The models whose page is built from the store catalogue and the manifest alone. */
export type CatalogueModel = "astraea" | "tsubomi" | "noctua" | "halia";

const CATALOGUE_STAGE: Record<CatalogueModel, { formation: number; tint: readonly [number, number, number] }> = {
  astraea: { formation: Formation.Horizon, tint: VIOLET },
  tsubomi: { formation: Formation.Bloom, tint: SPRING },
  halia: { formation: Formation.Horizon, tint: EAGLE_GOLD },
  noctua: { formation: Formation.Nexus, tint: NIGHT },
};

/** ASTRAEA, Tsubomi and Noctua: the same hero, stage and release card as OUKA and Cherry. */
export function CatalogueModelPage({ lang, id }: { lang: Lang; id: CatalogueModel }) {
  const d = langData(lang);
  const p = d.products[id];
  if (!p) throw new Error(`${id}: not in the store catalogue`);
  const dl = d.download[id];
  const c = d.chrome;
  const stage = CATALOGUE_STAGE[id];
  const hasLog = d.changelog.brands.some((b) => b.id === id);
  return (
    <>
      <RealmAnchor className="ac-brand-hero" config={{ formation: stage.formation, x: 0.72, xNarrow: 0.5, scale: 0.32, scaleNarrow: 0.26, tint: stage.tint }}>
        <div className="ac-wrap ac-brand-grid">
          <div className="ac-brand-copy">
            <p className="ac-eyebrow ac-reveal">{p.badge ?? p.category}</p>
            <h1 className="ac-display ac-brand-name ac-reveal">{p.name}</h1>
            <p className="ac-brand-version ac-reveal">
              <b className="ac-ltr">V{dl?.version ?? p.version}</b>
              {p.jp ? <span lang="ja">{p.jp}</span> : null}
            </p>
            <p className="ac-brand-line ac-reveal">{p.headline}</p>
            {p.tagline !== p.headline ? (
              <p className="ac-lead ac-reveal" style={{ maxWidth: "36ch" }}>
                {p.tagline}
              </p>
            ) : null}
            <div className="ac-brand-actions ac-reveal">
              {dl ? (
                <a className="ac-btn" href={dl.file.url} download>
                  {c.primaryCta}
                </a>
              ) : null}
              {hasLog ? (
                <Link className="ac-link" href={pathOf(lang, `changelog/?model=${id}`)}>
                  {c.changelog} <span className="ac-flip">{c.arrow}</span>
                </Link>
              ) : null}
            </div>
          </div>
          <BrandStage icon={`icons/${id}.png`} label={p.name} />
        </div>
      </RealmAnchor>
      {dl ? <ReleaseCard lang={lang} requirements={dl.requirements} file={dl.file} /> : null}
    </>
  );
}

export function AlphaPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const a = d.alpha;
  return (
    <>
      <RealmAnchor className="ac-brand-hero" config={{ formation: Formation.Ember, x: 0.72, xNarrow: 0.5, scale: 0.36, scaleNarrow: 0.3, tint: ASH }}>
        <div className="ac-wrap ac-brand-grid">
          <div className="ac-brand-copy">
            <p className="ac-eyebrow ac-ltr ac-reveal">{a.version}</p>
            <h1 className="ac-display ac-brand-name ac-reveal">{a.title}</h1>
            <p className="ac-lead ac-reveal" style={{ maxWidth: "36ch" }}>
              {a.lede}
            </p>
            <div className="ac-brand-actions ac-reveal">
              <Link className="ac-btn" href={pathOf(lang, "changelog/?model=alpha")}>
                {a.ctaRetirement}
              </Link>
              <Link className="ac-btn ac-btn--ghost" href={pathOf(lang, "changelog/")}>
                {a.ctaChangelog}
              </Link>
            </div>
          </div>
          <BrandStage icon="icons/alpha.png" label={a.title} dim />
        </div>
      </RealmAnchor>
      <div className="ac-wrap ac-sections ac-alpha">
        {a.sections.map((s) => (
          <section key={s.heading} className="ac-card ac-section-card ac-reveal">
            <h2 className="ac-h3">{s.heading}</h2>
            <p>{s.body}</p>
          </section>
        ))}
      </div>
    </>
  );
}

/** Cherry Controls' inline grammar: key caps, English names, the release, menu paths. */
function Tokens({ tokens }: { tokens: ControlToken[] }) {
  return (
    <>
      {tokens.map((t, i) => {
        if (typeof t === "string") return <span key={i}>{t}</span>;
        switch (t.t) {
          case "key":
            return (
              <kbd key={i} className="ac-key" dir={t.dir}>
                {t.label}
              </kbd>
            );
          case "en":
          case "release":
            return (
              <span key={i} lang="en" dir="ltr">
                {t.v}
              </span>
            );
          case "nobreak":
            return (
              <span key={i} className="ac-nb">
                {t.v}
              </span>
            );
          case "path":
            return (
              <span key={i} className="ac-path">
                {t.steps.map((s, j) => (
                  <span key={j}>
                    {j > 0 ? t.sep : null}
                    <span className="ac-path-step">{s}</span>
                  </span>
                ))}
              </span>
            );
        }
        return null;
      })}
    </>
  );
}

export function ControlsPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const k = d.brands.controls;
  return (
    <RealmAnchor className="ac-controls" config={{ formation: Formation.Store, x: 0.5, y: 0.62, scale: 0.42, tint: ROSE }}>
      <div className="ac-wrap ac-page-head">
        <p className="ac-eyebrow">
          <Link href={pathOf(lang, "cherry/")} lang="en" dir="ltr">
            Cherry
          </Link>
        </p>
        <h1 className="ac-h1">{k.heading}</h1>
        <p className="ac-lead ac-cc-note">
          <Tokens tokens={k.note} />
        </p>
        <p className="ac-small ac-cc-note">
          <Tokens tokens={k.layout} />
        </p>
      </div>
      <div className="ac-wrap ac-cc-grid">
        {k.cards.map((card) => (
          <section key={card.id} className="ac-card ac-cc-card ac-reveal" aria-labelledby={card.anchor}>
            <h2 className="ac-h3" id={card.anchor}>
              <Tokens tokens={card.title} />
            </h2>
            <ul className="ac-cc-list">
              {card.facts.map((f, i) => (
                <li key={i}>
                  <Tokens tokens={f} />
                </li>
              ))}
            </ul>
            <table className="ac-cc-keys">
              <tbody>
                {card.keys.map((row, i) => (
                  <tr key={i}>
                    <th scope="row">
                      <Tokens tokens={row.action} />
                    </th>
                    <td>
                      <Tokens tokens={row.how} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {card.lists.map((list, i) => (
              <div key={i}>
                <h3 className="ac-cc-h3">
                  <Tokens tokens={list.title} />
                </h3>
                <ul className="ac-cc-list">
                  {list.items.map((it, j) => (
                    <li key={j}>
                      <Tokens tokens={it} />
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </section>
        ))}
      </div>
    </RealmAnchor>
  );
}
