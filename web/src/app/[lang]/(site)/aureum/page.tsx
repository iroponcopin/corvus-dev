import type { Metadata } from "next";
import { AureumPage } from "@/components/pages/BrandPages";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  return pageMeta(lang, "aureum/", d.brands.aureum.title, d.brands.aureum.description);
}

export default async function Page({ params }: LangParams) {
  return <AureumPage lang={await langOf(params)} />;
}
