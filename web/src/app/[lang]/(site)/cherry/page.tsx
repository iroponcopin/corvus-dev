import type { Metadata } from "next";
import { CherryPage } from "@/components/pages/BrandPages";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  return pageMeta(lang, "cherry/", d.brands.cherry.title, d.brands.cherry.description);
}

export default async function Page({ params }: LangParams) {
  return <CherryPage lang={await langOf(params)} />;
}
