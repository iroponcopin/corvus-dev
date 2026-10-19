import type { ReactNode } from "react";


/**
 * The root layout only carries the stylesheet: <html lang dir> belongs to the language
 * segment (app/[lang]/layout.tsx), which is what keeps one WebGL context alive across every
 * navigation within a language. The 404 page renders its own document.
 */
export default function RootLayout({ children }: { children: ReactNode }) {
  return children;
}
