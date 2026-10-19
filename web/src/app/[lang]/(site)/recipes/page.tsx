import type { Metadata } from "next";
import { RecipesPage } from "@/components/pages/RecipesPage";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  return pageMeta(lang, "recipes/", d.recipes.navTitle, d.recipes.description);
}

export default async function Page({ params }: LangParams) {
  return <RecipesPage lang={await langOf(params)} />;
}
