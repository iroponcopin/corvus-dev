import { FRESH } from "@/i18n/fresh";
import { langData, wiki } from "@/lib/wiki";
import type { Lang } from "@/lib/wiki-types";
import { BrandStage } from "../BrandStage";
import { CommandBrowser } from "../discord/CommandBrowser";
import { MissionControl } from "../home/MissionControl";
import { HOME_V2 } from "@/i18n/home";
import { TrustedHtml } from "../Rich";


export function DiscordPage({ lang }: { lang: Lang }) {
  const d = langData(lang);
  const w = wiki();
  const k = d.discord;
  const f = FRESH[lang];
  const st = k.status;
  const steps: [string, string][] = [
    [k.s1_h, k.s1_p],
    [k.s2_h, k.s2_p],
    [k.s3_h, k.s3_p],
    [k.s4_h, k.s4_p],
  ];
  return (
    <>
      <section className="ac-brand-hero">
        <div className="ac-wrap ac-brand-grid">
          <div className="ac-brand-copy">
            <p className="ac-eyebrow ac-reveal">{k.eyebrow}</p>
            <h1 className="ac-h1 ac-reveal">{k.title}</h1>
            <p className="ac-lead ac-reveal" style={{ maxWidth: "40ch" }}>
              {k.lede}
            </p>
            <div className="ac-brand-actions ac-reveal">
              {w.discord.invite ? (
                <a className="ac-btn ac-btn--discord" href={w.discord.invite} target="_blank" rel="noopener noreferrer">
                  {k.invite}
                </a>
              ) : null}
            </div>
            <p className="ac-small ac-reveal">{k.invite_note}</p>
          </div>
          <BrandStage icon="icons/store.png" label="" />
        </div>
      </section>

      <section className="ac-wrap ac-dc-section" aria-labelledby="dc-status">
        <h2 id="dc-status" className="ac-h3">
          {st.statusTitle}
        </h2>
        <dl className="ac-status-grid">
          <div className="ac-card ac-reveal">
            <dt>{st.statusInvite}</dt>
            <dd>{st.published}</dd>
          </div>
          <div className="ac-card ac-reveal">
            <dt>{st.statusPermissions}</dt>
            <dd className="ac-ltr">{w.discord.permissions}</dd>
          </div>
          <div className="ac-card ac-reveal">
            <dt>{st.statusLatest}</dt>
            <dd className="ac-ltr" lang="en">
              {w.discord.latest.title} · {w.discord.latest.date}
            </dd>
          </div>
          <div className="ac-card ac-reveal">
            <dt>{st.statusFeed}</dt>
            <dd className="ac-ltr">
              {w.discord.feed.date} · {w.discord.feed.count}
            </dd>
          </div>
        </dl>
        <p className="ac-small">{st.statusNote}</p>
        <MissionControl
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
      </section>

      <section className="ac-wrap ac-dc-section" aria-labelledby="dc-setup">
        <h2 id="dc-setup" className="ac-h2">
          {k.setup_title}
        </h2>
        <ol className="ac-steps">
          {steps.map(([h, p], i) => (
            <li key={h} className="ac-card ac-reveal">
              <span className="ac-step-n" aria-hidden="true">
                {i + 1}
              </span>
              <h3>{h}</h3>
              <TrustedHtml html={p} className="ac-small ac-dc-html" as="p" />
              {i === 3 ? (
                <span className="ac-kinds ac-ltr">
                  {w.discord.routeKinds.map((kind) => (
                    <code key={kind}>{kind}</code>
                  ))}
                </span>
              ) : null}
            </li>
          ))}
        </ol>
      </section>

      <section className="ac-wrap ac-dc-section" aria-labelledby="dc-posts">
        <h2 id="dc-posts" className="ac-h3">
          {k.posts_title}
        </h2>
        <p className="ac-small">{k.posts_p}</p>
        <ul className="ac-posts">
          <li className="ac-card ac-reveal">{k.post_update}</li>
          <li className="ac-card ac-reveal">{k.post_upcoming}</li>
          <li className="ac-card ac-reveal">{k.post_intake}</li>
        </ul>
      </section>

      <section className="ac-wrap ac-dc-section" aria-labelledby="dc-cmds">
        <h2 id="dc-cmds" className="ac-h2">
          {k.cmds_title}
        </h2>
        <CommandBrowser
          groups={k.groups}
          labels={{
            thCmd: k.th_cmd,
            thWhat: k.th_what,
            thWho: k.th_who,
            whoAll: k.who_all,
            whoAdmin: k.who_admin,
            copy: d.chrome.copy,
            copied: d.chrome.copied,
            filter: f.nexus.filter,
          }}
        />
        <p className="ac-small">{k.rate_note}</p>
      </section>

      <section className="ac-wrap ac-dc-section" aria-labelledby="dc-lang">
        <h2 id="dc-lang" className="ac-h3">
          {k.lang_title}
        </h2>
        <p>{k.lang_p}</p>
        <ul className="ac-dc-langs">
          {w.discord.languages.map((code) => (
            <li key={code} className="ac-card">
              <span lang={code}>{w.discord.languageNames[code] ?? code}</span>
              <code>{code}</code>
            </li>
          ))}
        </ul>
        <p className="ac-small">{k.lang_note}</p>
      </section>

      <section className="ac-wrap ac-dc-section ac-dc-last" aria-labelledby="dc-priv">
        <h2 id="dc-priv" className="ac-h3">
          {k.privacy_title}
        </h2>
        <p>{k.privacy_p}</p>
      </section>
    </>
  );
}
