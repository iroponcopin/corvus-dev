import type { Metadata } from "next";
import { AlphaPage } from "@/components/pages/BrandPages";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  return pageMeta(lang, "alpha/", d.alpha.title, d.alpha.description);
}

export default async function Page({ params }: LangParams) {
  return <AlphaPage lang={await langOf(params)} />;
}
