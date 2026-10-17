import { FRESH } from "@/i18n/fresh";
import Link from "next/link";
import { asset, pathOf } from "@/lib/site";
import { langData, wiki } from "@/lib/wiki";
import type { Lang, LangData } from "@/lib/wiki-types";
import { FileCard, type FileCardLabels } from "../FileCard";
import { AstraeaEnded } from "./AstraeaEnded";


export function fileLabels(d: LangData): FileCardLabels {
  return { fileSize: d.chrome.fileSize, sha256: d.chrome.sha256, copy: d.chrome.copy, copied: d.chrome.copied };
}

/** The four Corvus Store files (macOS, Windows, Linux, jar), shared with the Store page. */
export function LauncherFiles({ d }: { d: LangData }) {
  const f = d.launcherFiles;
  const labels = fileLabels(d);
  return (
    <div className="ac-grid-2">
      {f.native.map((n) => (
        <FileCard
          key={n.platform}
          tag={`${n.label} · .${n.ext}`}
          file={n}
          note={n.platform === "macos" ? d.launcher.macNote : undefined}
          cta={`${d.launcher.cta} (${n.label})`}
          labels={labels}
        />
      ))}
      <FileCard
        tag={`${d.chrome.launcherVersion} ${f.version} · .jar`}
        file={f.jar}
        note={d.launcher.jarNote}
        cta={d.launcher.cta}
        labels={labels}
      />
    </div>
  );
}

export function DownloadPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const w = wiki();
  const dl = d.download;
  const labels = fileLabels(d);
  const mc = w.versions.mc;
  return (
    <section>
      <div className="ac-wrap ac-page-head">
        <p className="ac-eyebrow">
          {d.chrome.launcher} <span className="ac-ltr">{d.launcherFiles.version}</span>
        </p>
        <h1 className="ac-h1">{dl.heading}</h1>
        <p className="ac-lead">{dl.body}</p>
      </div>

      <section className="ac-wrap ac-dl-section" aria-labelledby="dl-store">
        <h2 id="dl-store" className="ac-h3">
          {dl.nativeHeading}
        </h2>
        <p className="ac-small ac-dl-note">{dl.nativeNote}</p>
        <LauncherFiles d={d} />
        <p className="ac-dl-more">
          <Link className="ac-link" href={pathOf(lang, "changelog/")}>
            {dl.changelogLink}
          </Link>
        </p>
      </section>

      {dl.halia ? (
        <section className="ac-wrap ac-dl-section" aria-labelledby="dl-halia">
          <h2 id="dl-halia" className="ac-h3">
            Halia {d.products.halia?.jp ?? ""}
          </h2>
          <p className="ac-small ac-dl-note">{d.products.halia?.tagline}</p>
          <div className="ac-grid-2">
            <FileCard tag={`${d.chrome.version} ${dl.halia.version}`} file={dl.halia.file} cta={d.chrome.primaryCta} labels={labels} />
            <div className="ac-card ac-file-aside">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset("icons/halia.png")} alt="" width={64} height={64} />
              <p className="ac-small ac-ltr">Minecraft {mc} · Fabric</p>
            </div>
          </div>
        </section>
      ) : null}

      {d.products.astraea?.availability === "archived" ? (
        <section className="ac-wrap ac-dl-section" aria-labelledby="astraea-ended-h">
          <AstraeaEnded lang={lang} />
        </section>
      ) : dl.astraea ? (
        <section className="ac-wrap ac-dl-section" aria-labelledby="dl-astraea">
          <h2 id="dl-astraea" className="ac-h3">
            ASTRAEA
          </h2>
          <p className="ac-small ac-dl-note">{d.products.astraea?.tagline}</p>
          <div className="ac-grid-2">
            <FileCard tag={`${d.chrome.version} ${dl.astraea.version}`} file={dl.astraea.file} cta={d.chrome.primaryCta} labels={labels} />
            <div className="ac-card ac-file-aside">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset("icons/astraea.png")} alt="" width={64} height={64} />
              <p className="ac-small ac-ltr">Minecraft {mc} · Fabric</p>
            </div>
          </div>
        </section>
      ) : null}

      {dl.tsubomi ? (
        <section className="ac-wrap ac-dl-section" aria-labelledby="dl-tsubomi">
          <h2 id="dl-tsubomi" className="ac-h3">
            Tsubomi {d.products.tsubomi?.jp ?? ""}
          </h2>
          <p className="ac-small ac-dl-note">{d.products.tsubomi?.tagline}</p>
          <div className="ac-grid-2">
            <FileCard tag={`${d.chrome.version} ${dl.tsubomi.version}`} file={dl.tsubomi.file} cta={d.chrome.primaryCta} labels={labels} />
            <div className="ac-card ac-file-aside">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset("icons/tsubomi.png")} alt="" width={64} height={64} />
              <p className="ac-small ac-ltr">Minecraft {mc} · Fabric</p>
            </div>
          </div>
        </section>
      ) : null}

      <section className="ac-wrap ac-dl-section" aria-labelledby="dl-aureum">
        <h2 id="dl-aureum" className="ac-h3">
          {dl.aureum.heading}
        </h2>
        <p className="ac-small ac-dl-note">{dl.aureum.body}</p>
        <div className="ac-grid-2">
          <FileCard tag={`${d.chrome.version} ${dl.aureum.version}`} file={dl.aureum.file} cta={dl.aureum.cta} labels={labels} />
          <div className="ac-card ac-file-aside">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={asset("icons/aureum.png")} alt="" width={64} height={64} />
            <p className="ac-small">{dl.aureum.note}</p>
            <Link className="ac-link" href={pathOf(lang, "aureum/")}>
              Aureum <span className="ac-flip">{d.chrome.arrow}</span>
            </Link>
          </div>
        </div>
      </section>

      {dl.agent ? (
        <section className="ac-wrap ac-dl-section" aria-labelledby="dl-agent">
          <h2 id="dl-agent" className="ac-h3">
            {FRESH[lang].agent.title}
          </h2>
          <p className="ac-small ac-dl-note">{FRESH[lang].agent.body}</p>
          <div className="ac-grid-2">
            <FileCard tag={`${d.chrome.version} ${dl.agent.version}`} file={dl.agent.file} cta={d.chrome.primaryCta} labels={labels} />
            <div className="ac-card ac-file-aside">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={asset("icons/store.png")} alt="" width={64} height={64} />
              <p className="ac-small">{FRESH[lang].agent.note}</p>
            </div>
          </div>
        </section>
      ) : null}

      <section className="ac-wrap ac-dl-section" aria-labelledby="dl-discord">
        <h2 id="dl-discord" className="ac-h3">
          {dl.discord.heading}
        </h2>
        <p className="ac-small ac-dl-note">{dl.discord.body}</p>
        <p className="ac-dl-actions">
          {w.discord.invite ? (
            <a className="ac-btn" href={w.discord.invite} target="_blank" rel="noopener">
              {dl.discord.cta}
            </a>
          ) : null}
          <Link className="ac-link" href={pathOf(lang, "discord/")}>
            {d.chrome.discord} <span className="ac-flip">{d.chrome.arrow}</span>
          </Link>
        </p>
      </section>

      <section className="ac-wrap ac-dl-section ac-dl-last" aria-labelledby="dl-alpha">
        <h2 id="dl-alpha" className="ac-h3">
          Alpha
        </h2>
        <p className="ac-small">
          {dl.alphaNote}{" "}
          <Link className="ac-link" href={pathOf(lang, "alpha/")}>
            <span className="ac-ltr">{dl.alphaVersion}</span> <span className="ac-flip">{d.chrome.arrow}</span>
          </Link>
        </p>
      </section>
    </section>
  );
}
