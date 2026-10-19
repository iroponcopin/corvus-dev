import type { Metadata } from "next";
import { CatalogueModelPage } from "@/components/pages/BrandPages";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const p = langData(lang).products.astraea;
  return pageMeta(lang, "astraea/", p?.name ?? "ASTRAEA", p?.tagline ?? "");
}

export default async function Page({ params }: LangParams) {
  return <CatalogueModelPage lang={await langOf(params)} id="astraea" />;
}
