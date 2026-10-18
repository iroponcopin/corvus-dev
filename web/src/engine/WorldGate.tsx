"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { isHomePath } from "@/lib/site";
import { Experience } from "./Experience";

/** The pages whose scenes draw into the shared 3D stage: the Sparxie skin. The recipe Tome has its own canvas. */
const STAGE_PAGES = ["skin/"];

/**
 * Mounts the shared 3D stage only where a page has a 3D scene (the Skin). Everywhere else, and on the
 * home page (whose cinema draws its own footage), the stage is absent, exactly as on a device without WebGL 2, and
 * the posters show.
 */
export function WorldGate({ dir }: { dir: "ltr" | "rtl" }) {
  const pathname = usePathname() ?? "/";
  const rest = pathname.replace(/^\/(?:[a-z]{2}(?:-br)?\/)?/, "");
  const stage = !isHomePath(pathname) && STAGE_PAGES.some((p) => rest.startsWith(p));

  useEffect(() => {
    if (!stage) document.documentElement.dataset.webgl = "off";
  }, [stage]);

  if (!stage) return null;
  return <Experience dir={dir} />;
}
