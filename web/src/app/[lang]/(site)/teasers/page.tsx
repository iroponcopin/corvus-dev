import type { Metadata } from "next";
import { TeasersPage } from "@/components/pages/TeasersPage";
import { FRESH } from "@/i18n/fresh";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const t = FRESH[lang].teasers;
  return pageMeta(lang, "teasers/", t.title, t.description);
}

export default async function Page({ params }: LangParams) {
  return <TeasersPage lang={await langOf(params)} />;
}
