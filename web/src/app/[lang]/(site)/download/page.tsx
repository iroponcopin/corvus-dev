import type { Metadata } from "next";
import { DownloadPage } from "@/components/pages/DownloadPage";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  return pageMeta(lang, "download/", d.download.title, d.download.description);
}

export default async function Page({ params }: LangParams) {
  return <DownloadPage lang={await langOf(params)} />;
}
