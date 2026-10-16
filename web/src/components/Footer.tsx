import Link from "next/link";
import { FooterLanguages } from "./FooterLanguages";
import { FRESH } from "@/i18n/fresh";
import { MODELS } from "@/lib/models";
import { pathOf } from "@/lib/site";
import type { Lang, LangData } from "@/lib/wiki-types";

/**
 * The footer the pre-4.0 portal carried, column for column: Models (the header's six), Get
 * started, Reference, Status (with the Teasers); the thirteen languages; the legal block.
 */
export function Footer({ lang, d }: { lang: Lang; d: LangData }) {
  const c = d.chrome;
  const f = FRESH[lang];
  const cols: { heading: string; links: { label: string; href: string; note?: string }[] }[] = [
    {
      heading: f.nav.models,
      links: MODELS.map(([id, name, href]) => ({
        label: d.products[id]?.name ?? name,
        href: pathOf(lang, href),
        note:
          d.products[id]?.availability === "soon"
            ? d.launcher.text.comingSoon
            : d.products[id]?.availability === "archived"
              ? (id === "astraea" ? f.astraeaEnded.badge : d.launcher.text.archived)
              : undefined,
      })),
    },
    {
      heading: c.footerGetStarted,
      links: [
        { label: c.download, href: pathOf(lang, "download/") },
        { label: c.launcher, href: pathOf(lang, "launcher/") },
        { label: c.skin, href: pathOf(lang, "skin/") },
      ],
    },
    { heading: c.footerReference, links: [{ label: c.recipes, href: pathOf(lang, "recipes/") }] },
    {
      heading: c.footerStatus,
      links: [
        { label: c.changelog, href: pathOf(lang, "changelog/") },
        { label: f.announcement.title, href: pathOf(lang, "announcement/") },
        { label: f.teasers.title, href: pathOf(lang, "teasers/") },
        { label: c.discord, href: pathOf(lang, "discord/") },
      ],
    },
  ];
  return (
    <footer className="ac-footer">
      <div className="ac-wrap">
        <div className="ac-footer-cols">
          {cols.map((col) => (
            <div key={col.heading}>
              <h2>{col.heading}</h2>
              <ul>
                {col.links.map((l) => (
                  <li key={l.href}>
                    <Link href={l.href}>{l.label}</Link>
                    {l.note ? <small className="ac-footer-note"> · {l.note}</small> : null}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <FooterLanguages lang={lang} label={c.language} />
        <div className="ac-footer-legal">
          <p className="ac-footer-title">{c.legalTitle}</p>
          <p>{c.tagline}</p>
          <p>{c.footerNote}</p>
        </div>
      </div>
    </footer>
  );
}
