import Link from "next/link";
import type { ReactNode } from "react";
import { pathOf } from "@/lib/site";
import { langData } from "@/lib/wiki";
import type { ControlToken, Lang, Requirement } from "@/lib/wiki-types";
import { BrandStage } from "../BrandStage";
import { CopyButton } from "../CopyButton";
import { ThemePlayer } from "../ThemePlayer";
import { AstraeaEnded } from "./AstraeaEnded";

/** The models that share the model-page design: each sets its accent pair on `.ac-model-page[data-model]`. */
export type ModelId = "ouka" | "cherry" | "aureum" | "astraea" | "tsubomi" | "noctua" | "halia";

/**
 * A model page's frame: the page-wide ambient light in the model's own accents (one fixed-size layer, clipped so it
 * never widens the page), then the page. Accents come from globals.css (`--accent-<model>`), so no colour is set here.
 */
function ModelPage({ id, children }: { id: ModelId; children: ReactNode }) {
  return (
    <div className="ac-model-page" data-model={id}>
      <div className="ac-model-ambient" aria-hidden="true" />
      {children}
    </div>
  );
}

/** A call to action as a text link with an arrow, in the template's style. `primary` is the download. */
function CtaDownload({ href, label, arrow, primary = false }: { href: string; label: string; arrow: string; primary?: boolean }) {
  return (
    <a className={`ac-model-cta${primary ? " ac-model-cta--primary" : ""}`} href={href} download>
      {label} <span className="ac-flip">{arrow}</span>
    </a>
  );
}

function CtaLink({ href, label, arrow }: { href: string; label: string; arrow: string }) {
  return (
    <Link className="ac-model-cta" href={href}>
      {label} <span className="ac-flip">{arrow}</span>
    </Link>
  );
}

/**
 * The hero every model page shares: eyebrow, Syne name in the model's accent gradient, the version pill from the
 * manifest, the line and lead, the text CTAs, and the model's own icon art beside them.
 */
function ModelHero({
  eyebrow,
  title,
  version,
  detail,
  line,
  lead,
  actions,
  footer,
  icon,
  dim = false,
}: {
  eyebrow?: string;
  title: string;
  version?: string;
  detail?: ReactNode;
  line?: string;
  lead?: string;
  actions: ReactNode;
  footer?: ReactNode;
  icon: string;
  dim?: boolean;
}) {
  return (
    <section className="ac-model-hero">
      <div className="ac-wrap ac-model-grid">
        <div className="ac-model-copy">
          {eyebrow ? <p className="ac-eyebrow ac-reveal">{eyebrow}</p> : null}
          <h1 className="ac-display ac-model-name ac-reveal">{title}</h1>
          {version ? (
            <p className="ac-model-version ac-reveal">
              <span className="ac-model-pill ac-ltr">V{version}</span>
              {detail}
            </p>
          ) : null}
          {line ? <p className="ac-model-line ac-reveal">{line}</p> : null}
          {lead ? <p className="ac-lead ac-model-lead ac-reveal">{lead}</p> : null}
          <div className="ac-model-actions ac-reveal">{actions}</div>
          {footer ? <div className="ac-reveal">{footer}</div> : null}
        </div>
        <BrandStage icon={icon} label={title} dim={dim} />
      </div>
    </section>
  );
}

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
    <div className="ac-wrap ac-model-release">
      <div className="ac-card ac-model-release-card ac-reveal" id="release">
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
        <div className="ac-model-release-side">
          <dl className="ac-facts">
            <div>
              <dt>{c.sha256}</dt>
              <dd>
                <code className="ac-hash">{file.sha256}</code>
                <CopyButton text={file.sha256} label={c.copy} done={c.copied} />
              </dd>
            </div>
          </dl>
          <p className="ac-model-release-dl">
            <CtaDownload href={file.url} label={c.primaryCta} arrow={c.arrow} primary />
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
    <ModelPage id="ouka">
      <ModelHero
        eyebrow={b.eyebrow}
        title={b.title}
        version={b.release.version}
        detail={<span className="ac-model-codename ac-ltr" lang="en">{b.release.codename}</span>}
        line={b.line}
        icon="icons/ouka.png"
        actions={
          <>
            <CtaDownload href={b.release.file.url} label={c.primaryCta} arrow={c.arrow} primary />
            <CtaLink href={pathOf(lang, "changelog/?model=ouka")} label={c.changelog} arrow={c.arrow} />
          </>
        }
        footer={<ThemePlayer track={b.player.track} play={b.player.play} pause={b.player.pause} />}
      />
      <ReleaseCard lang={lang} requirements={b.release.requirements} file={b.release.file} />
    </ModelPage>
  );
}

export function CherryPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const b = d.brands.cherry;
  const c = d.chrome;
  return (
    <ModelPage id="cherry">
      <ModelHero
        eyebrow={b.eyebrow}
        title={b.title}
        version={b.release.version}
        detail={<span className="ac-model-codename ac-ltr" lang="en">{b.release.codename}</span>}
        line={b.line}
        icon="icons/cherry.png"
        actions={
          <>
            <CtaDownload href={b.release.file.url} label={c.primaryCta} arrow={c.arrow} primary />
            <CtaLink href={pathOf(lang, "changelog/?model=cherry")} label={c.changelog} arrow={c.arrow} />
            <CtaLink href={pathOf(lang, "cherry-controls/")} label={b.controlsLabel} arrow={c.arrow} />
          </>
        }
      />
      <ReleaseCard lang={lang} requirements={b.release.requirements} file={b.release.file} />
    </ModelPage>
  );
}

export function AureumPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const a = d.brands.aureum;
  const c = d.chrome;
  return (
    <ModelPage id="aureum">
      <ModelHero
        title={a.title}
        version={a.version}
        lead={a.tagline}
        icon="icons/aureum.png"
        actions={
          <>
            <CtaDownload href={a.download.url} label={a.download.label} arrow={c.arrow} primary />
            <CtaLink href={pathOf(lang, "download/")} label={a.detailsLabel} arrow={c.arrow} />
          </>
        }
      />
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
        <p className="ac-aureum-log ac-reveal">
          <CtaLink href={pathOf(lang, "changelog/?model=aureum")} label={c.changelog} arrow={c.arrow} />
        </p>
      </div>
    </ModelPage>
  );
}

/** The models whose page is built from the store catalogue and the manifest alone. */
export type CatalogueModel = "astraea" | "tsubomi" | "noctua" | "halia";

/**
 * ASTRAEA, Tsubomi, Noctua and Halia: the same hero, stage and release card as OUKA and Cherry. An archived model keeps
 * its page as a notice: greyed art, no download.
 */
export function CatalogueModelPage({ lang, id }: { lang: Lang; id: CatalogueModel }) {
  const d = langData(lang);
  const p = d.products[id];
  if (!p) throw new Error(`${id}: not in the store catalogue`);
  const c = d.chrome;
  const archived = p.availability === "archived";
  const dl = archived ? undefined : d.download[id];
  const hasLog = d.changelog.brands.some((b) => b.id === id);
  return (
    <ModelPage id={id}>
      {id === "astraea" && archived ? (
        <div className="ac-wrap ac-ended-top">
          <AstraeaEnded lang={lang} />
        </div>
      ) : null}
      <ModelHero
        eyebrow={p.badge ?? p.category}
        title={p.name}
        version={dl?.version ?? p.version}
        detail={p.jp ? <span className="ac-model-codename" lang="ja">{p.jp}</span> : undefined}
        line={p.headline}
        lead={p.tagline !== p.headline ? p.tagline : undefined}
        icon={`icons/${id}.png`}
        dim={archived}
        actions={
          <>
            {dl ? <CtaDownload href={dl.file.url} label={c.primaryCta} arrow={c.arrow} primary /> : null}
            {hasLog ? <CtaLink href={pathOf(lang, `changelog/?model=${id}`)} label={c.changelog} arrow={c.arrow} /> : null}
          </>
        }
      />
      {dl ? <ReleaseCard lang={lang} requirements={dl.requirements} file={dl.file} /> : null}
    </ModelPage>
  );
}

export function AlphaPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const a = d.alpha;
  return (
    <>
      <section className="ac-brand-hero">
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
      </section>
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
    <section className="ac-controls">
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
    </section>
  );
}
