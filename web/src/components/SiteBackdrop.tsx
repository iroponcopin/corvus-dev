"use client";

import { usePathname } from "next/navigation";
import { asset, isHomePath } from "@/lib/site";

/** Pages whose still is the cloud sunrise (Halia's world, and the Store). Every other page is the forest. */
const SUNRISE_PAGES = ["halia/", "launcher/", "download/"];

/**
 * The backdrop of every page but the home page (which has its own cinema): one still of our own footage, fixed
 * behind the page, very dark and desaturated, with a slow drift of mist. The veil keeps text at AA contrast.
 */
export function SiteBackdrop() {
  const pathname = usePathname() ?? "/";
  if (isHomePath(pathname)) return null;
  const rest = pathname.replace(/^\/(?:[a-z]{2}(?:-br)?\/)?/, "");
  const sunrise = SUNRISE_PAGES.some((p) => rest.startsWith(p));
  const src = sunrise ? asset("cinema/act1/bg/f080.webp") : asset("cinema/act2/bg/f150.webp");
  return (
    <div className="ac-backdrop" aria-hidden="true">
      <div className="ac-backdrop-img" style={{ backgroundImage: `url("${src}")` }} />
      <div className="ac-backdrop-mist" />
      <div className="ac-backdrop-veil" />
    </div>
  );
}
