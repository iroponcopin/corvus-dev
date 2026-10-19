import type { Metadata } from "next";
import { LauncherPage } from "@/components/pages/LauncherPage";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  return pageMeta(lang, "launcher/", d.launcher.title, d.launcher.description);
}

export default async function Page({ params }: LangParams) {
  return <LauncherPage lang={await langOf(params)} />;
}
