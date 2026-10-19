import type { Metadata } from "next";
import "./globals.css";
import "./corvus.css";
import Home, { type HomeCard, type HomeContent } from "@/components/home/TemplateHome";
import { FRESH } from "@/i18n/fresh";
import { SHELL } from "@/i18n/shell";
import { THEATRE } from "@/i18n/theatre";
import { BRAND_ICON } from "@/lib/brands";
import { pageMeta } from "@/lib/meta";
import { inModelOrder } from "@/lib/models";
import { asset, BASE_PATH, isLang, LANGUAGES, pathOf } from "@/lib/site";
import { langData, lineupFor } from "@/lib/wiki";
import type { Lang } from "@/lib/wiki-types";

type Params = { params: Promise<{ lang: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { lang } = await params;
  return pageMeta(lang as Lang, "", null, lineupFor(lang as Lang));
}

/** The four models the home presents, in the owner's order. */
const HOME_MODELS = ["halia", "ouka", "cherry", "tsubomi"] as const;

/**
 * The home: the home-theatre template's page (components/home/TemplateHome.tsx) with its own stylesheet, verbatim
 * (./globals.css), and Corvus content: the film, the Corvus wordmark and copy, the Corvus Store download, 13 languages.
 * The template's links are plain anchors, so every link here is a full URL with the base path.
 */
export default async function Page({ params }: Params) {
  const { lang } = await params;
  if (!isLang(lang)) return null;
  const d = langData(lang);
  const f = FRESH[lang];
  const th = THEATRE[lang];
  const c = d.chrome;
  const p = d.products;
  const t = d.launcher.text;
  const href = (section: string): string => `${BASE_PATH}${pathOf(lang, section)}`;
  const status = (id: string): string =>
    p[id]?.availability === "soon" ? t.comingSoon : p[id]?.availability === "archived" ? t.archived : t.available;
  const line: Record<(typeof HOME_MODELS)[number], string> = {
    halia: p.halia?.headline ?? "",
    ouka: d.brands.ouka.line,
    cherry: d.brands.cherry.line,
    tsubomi: p.tsubomi?.headline ?? "",
  };
  const models: HomeCard[] = inModelOrder([...HOME_MODELS]).map((id) => ({
    key: id,
    href: href(`${id}/`),
    eyebrow: `${p[id]?.version ? `V${p[id]?.version} — ` : ""}${status(id)}`,
    title: p[id]?.name ?? id,
    body: line[id],
    icon: asset(BRAND_ICON[id] ?? `icons/${id}.png`),
  }));
  const explore: HomeCard[] = [
    { key: "launcher", href: href("launcher/"), eyebrow: `${c.launcherVersion} ${d.launcherFiles.version}`, title: d.launcher.title, body: d.launcher.description, icon: asset("icons/store.png") },
    { key: "recipes", href: href("recipes/"), eyebrow: c.recipes, title: d.recipes.navTitle, body: d.recipes.description, icon: null },
    { key: "changelog", href: href("changelog/"), eyebrow: c.changelog, title: d.changelog.title, body: d.changelog.description, icon: null },
    { key: "announcement", href: href("announcement/"), eyebrow: f.announcement.title, title: f.announcement.title, body: f.announcement.description, icon: null },
    { key: "skin", href: href("skin/"), eyebrow: c.skin, title: d.skin.title, body: d.home.skinTile, icon: null },
    { key: "discord", href: href("discord/"), eyebrow: c.discord, title: d.discord.title, body: d.discord.description, icon: null },
  ];
  const content: HomeContent = {
    wordmark: "CORVUS",
    homeLabel: c.home,
    heroLabel: th.label,
    title: th.title,
    lede: th.lede,
    cta: th.cta,
    ctaHref: href("download/"),
    navLabel: c.primary,
    nav: [
      { key: "models", href: "#models", label: f.nav.models },
      { key: "recipes", href: href("recipes/"), label: c.recipes },
      { key: "changelog", href: href("changelog/"), label: c.changelog },
      { key: "download", href: href("download/"), label: c.download },
    ],
    loader: SHELL[lang].loader,
    models: { eyebrow: "CORVUS / 02", title: d.home.brandsTitle, lede: th.endLede, open: th.open, cards: models },
    explore: { eyebrow: "CORVUS / 03", title: d.home.explore, open: th.open, cards: explore },
    languages: {
      label: c.language,
      current: lang,
      links: LANGUAGES.map((l) => ({ key: l.code, href: `${BASE_PATH}${pathOf(l.code, "")}`, label: l.name })),
    },
  };
  return <Home content={content} />;
}
