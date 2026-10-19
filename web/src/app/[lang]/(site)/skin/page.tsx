import type { Metadata } from "next";
import { SkinPage } from "@/components/pages/SkinPage";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  return pageMeta(lang, "skin/", d.skin.title, d.skin.description);
}

export default async function Page({ params }: LangParams) {
  return <SkinPage lang={await langOf(params)} />;
}
