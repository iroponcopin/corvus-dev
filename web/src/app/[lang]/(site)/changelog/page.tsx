import type { Metadata } from "next";
import { ChangelogPage } from "@/components/pages/ChangelogPage";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  // The old pages titled this one with the navigation label (es "Historial", fr "Mises à jour").
  return pageMeta(lang, "changelog/", d.chrome.changelog, d.changelog.description);
}

export default async function Page({ params }: LangParams) {
  return <ChangelogPage lang={await langOf(params)} />;
}
