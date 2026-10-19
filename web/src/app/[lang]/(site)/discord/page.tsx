import type { Metadata } from "next";
import { DiscordPage } from "@/components/pages/DiscordPage";
import { pageMeta } from "@/lib/meta";
import { type LangParams, langOf } from "@/lib/route";
import { langData } from "@/lib/wiki";

export async function generateMetadata({ params }: LangParams): Promise<Metadata> {
  const lang = await langOf(params);
  const d = langData(lang);
  return pageMeta(lang, "discord/", d.discord.title, d.discord.description);
}

export default async function Page({ params }: LangParams) {
  return <DiscordPage lang={await langOf(params)} />;
}
