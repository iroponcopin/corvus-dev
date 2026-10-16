import { asset } from "@/lib/site";
import { BG_COUNT, EAGLE_COUNT } from "./timeline";

const pad3 = (n: number): string => String(n).padStart(3, "0");

/** The background frame file for index 0..112 (f001..f113), full size or the phone size. */
export function bgFrameUrl(index: number, small: boolean): string {
  return asset(`cinema/act1/${small ? "bg-sm" : "bg"}/f${pad3(index + 1)}.webp`);
}

/** The eagle frame file for index 0..59 (h001..h060). */
export function eagleFrameUrl(index: number): string {
  return asset(`cinema/act1/eagle/h${pad3(index + 1)}.webp`);
}

/** Load order: the first frame, then the rest in footage order. */
export function inOrder(count: number): number[] {
  return Array.from({ length: count }, (_, i) => i);
}

export const BG_ORDER = inOrder(BG_COUNT);
export const EAGLE_ORDER = inOrder(EAGLE_COUNT);
