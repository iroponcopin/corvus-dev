import "../../globals.css";
import { notFound } from "next/navigation";
import type { ReactNode } from "react";
import { DebugHud } from "@/components/DebugHud";
import { Footer } from "@/components/Footer";
import { Dock, type ModelLink, type UpdateLink } from "@/components/Dock";
import { Palette } from "@/components/palette/Palette";
import { LoadingScreen } from "@/components/shell/LoadingScreen";
import { Reveal } from "@/components/Reveal";
import { SiteBackdrop } from "@/components/SiteBackdrop";
import { SmoothScroll } from "@/components/SmoothScroll";
import { WorldGate } from "@/engine/WorldGate";
import { FRESH } from "@/i18n/fresh";
import { SHELL } from "@/i18n/shell";
import { MODELS } from "@/lib/models";
import { isLang, pathOf } from "@/lib/site";
import { langData } from "@/lib/wiki";

export default async function SiteLayout({ children, params }: { children: ReactNode; params: Promise<{ lang: string }> }) {
  const { lang } = await params;
  if (!isLang(lang)) notFound();
  const d = langData(lang);
  const f = FRESH[lang];
  const c = d.chrome;
  const t = d.launcher.text;
  // The Models menu, in the owner's order; a line the Store lists as "soon" says so (today, Noctua), and an ended
  // one says it has ended (ASTRAEA, 2026-10-16: its page stays, its menu line stays, last).
  const models: ModelLink[] = MODELS.map(([key, name, href]) => {
    const availability = d.products[key]?.availability;
    const soon = availability === "soon";
    const ended = availability === "archived";
    const status = soon ? t.comingSoon : ended ? (key === "astraea" ? f.astraeaEnded.badge : t.archived) : t.available;
    return { key, label: d.products[key]?.name ?? name, href: pathOf(lang, href), status, soon };
  });
  const updates: UpdateLink[] = [
    { key: "changelog", label: c.changelog, desc: f.nav.updatesDesc.changelog, href: pathOf(lang, "changelog/"), icon: "library" },
    { key: "announcement", label: f.announcement.title, desc: f.nav.updatesDesc.announcement, href: pathOf(lang, "announcement/"), icon: "play" },
    { key: "teasers", label: f.teasers.title, desc: f.nav.updatesDesc.teasers, href: pathOf(lang, "teasers/"), icon: "play" },
    { key: "skin", label: c.skin, desc: f.nav.updatesDesc.skin, href: pathOf(lang, "skin/"), icon: "user" },
  ];
  return (
    <>
        <a className="ac-skip" href="#main">
          {c.skipLink}
        </a>
        <SiteBackdrop />
        <WorldGate dir={d.dir} />
        <SmoothScroll />
        <Reveal />
        <LoadingScreen labels={SHELL[lang].loader} />
        <Dock
          lang={lang}
          models={models}
          updates={updates}
          labels={{
            siteTitle: c.siteTitle,
            home: c.home,
            launcher: c.launcher,
            models: f.nav.models,
            updates: f.nav.updates,
            recipes: c.recipes,
            discord: c.discord,
            download: c.download,
            search: SHELL[lang].palette.open,
            menu: c.menu,
            close: c.close,
            language: c.language,
            primary: c.primary,
            sound: f.sound,
            soundOn: f.soundOn,
            soundOff: f.soundOff,
          }}
        />
        <div className="ac-page">
          <main id="main">{children}</main>
          <Footer lang={lang} d={d} />
        </div>
        <Palette
          lang={lang}
          labels={SHELL[lang].palette}
          modelLabels={Object.fromEntries(models.map((m) => [m.key, m.label]))}
        />
        <DebugHud labels={{ fps: f.debug.fps, drawCalls: f.debug.drawCalls }} />
    </>
  );
}
