"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";
import { isHomePath } from "@/lib/site";
import { Experience } from "./Experience";

/**
 * Mounts the shared 3D stage (the realms' scenes) on every page except the home page, whose cinema draws its own
 * footage. On the home page the stage is absent, exactly as on a device without WebGL 2.
 */
export function WorldGate({ dir }: { dir: "ltr" | "rtl" }) {
  const pathname = usePathname();
  const home = pathname !== null && isHomePath(pathname);

  useEffect(() => {
    if (home) document.documentElement.dataset.webgl = "off";
  }, [home]);

  if (home) return null;
  return <Experience dir={dir} />;
}
