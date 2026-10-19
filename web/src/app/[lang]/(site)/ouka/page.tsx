import type { Metadata } from "next";
import { OukaPage } from "@/components/pages/BrandPages";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  return pageMeta(lang, "ouka/", d.brands.ouka.title, d.brands.ouka.description);
}

export default async function Page({ params }: LangParams) {
  return <OukaPage lang={await langOf(params)} />;
}
