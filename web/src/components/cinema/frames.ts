import { asset } from "@/lib/site";
import { ACT2_COUNT, ACT3_COUNT, BG_COUNT, CROW3_COUNT, CROW_COUNT, EAGLE_COUNT } from "./timeline";

const pad3 = (n: number): string => String(n).padStart(3, "0");

/** The Act I background file for index 0..112 (f001..f113), full size or the phone size. */
export function bgFrameUrl(index: number, small: boolean): string {
  return asset(`cinema/act1/${small ? "bg-sm" : "bg"}/f${pad3(index + 1)}.webp`);
}

/** The Act I eagle file for index 0..59 (h001..h060). */
export function eagleFrameUrl(index: number): string {
  return asset(`cinema/act1/eagle/h${pad3(index + 1)}.webp`);
}

/** The Act II background file for index 0..181 (f001..f182). */
export function act2FrameUrl(index: number, small: boolean): string {
  return asset(`cinema/act2/${small ? "bg-sm" : "bg"}/f${pad3(index + 1)}.webp`);
}

/** The Act II crow file for index 0..104 (c001..c105). */
export function crowFrameUrl(index: number): string {
  return asset(`cinema/act2/crow/c${pad3(index + 1)}.webp`);
}

/** The Act III headland file for index 0..195 (f001..f196). */
export function act3FrameUrl(index: number, small: boolean): string {
  return asset(`cinema/act3/${small ? "bg-sm" : "bg"}/f${pad3(index + 1)}.webp`);
}

/** The Act III close crow file for index 0..47 (k001..k048). */
export function crow3FrameUrl(index: number): string {
  return asset(`cinema/act3/crow/k${pad3(index + 1)}.webp`);
}

/** Load order: the first frame, then the rest in footage order. */
export function inOrder(count: number): number[] {
  return Array.from({ length: count }, (_, i) => i);
}

export const BG_ORDER = inOrder(BG_COUNT);
export const ACT2_ORDER = inOrder(ACT2_COUNT);
export const EAGLE_ORDER = inOrder(EAGLE_COUNT);
export const CROW_ORDER = inOrder(CROW_COUNT);
export const ACT3_ORDER = inOrder(ACT3_COUNT);
export const CROW3_ORDER = inOrder(CROW3_COUNT);
