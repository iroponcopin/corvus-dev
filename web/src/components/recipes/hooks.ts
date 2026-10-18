import { useSyncExternalStore } from "react";

/**
 * Media queries for the Recipe Tome, read through useSyncExternalStore so the server render and the first client
 * render agree (the server snapshot is passed in) and a later change re-renders without a hydration error.
 */
export function useMediaQuery(query: string, serverSnapshot: boolean): boolean {
  return useSyncExternalStore(
    (onChange) => {
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    () => window.matchMedia(query).matches,
    () => serverSnapshot,
  );
}

/** The side-by-side book and the 3D stage start at 1024 px (the owner's split). */
export function useWide(): boolean {
  return useMediaQuery("(min-width: 1024px)", true);
}

/** Reduced motion: no turntable, no riffle, no ritual, no page curl (the state changes at once). */
export function useReducedMotion(): boolean {
  return useMediaQuery("(prefers-reduced-motion: reduce)", false);
}
