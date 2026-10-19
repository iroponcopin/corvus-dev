import type { Metadata } from "next";
import { AnnouncementPage } from "@/components/pages/AnnouncementPage";
import { FRESH } from "@/i18n/fresh";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const t = FRESH[lang].announcement;
  return pageMeta(lang, "announcement/", t.title, t.description);
}

export default async function Page({ params }: LangParams) {
  return <AnnouncementPage lang={await langOf(params)} />;
}
