/** The window event that opens the Cmd/Ctrl+K palette; the Dock's search button dispatches it too. */
export const PALETTE_OPEN_EVENT = "corvus:palette-open";

export function openPalette(): void {
  window.dispatchEvent(new Event(PALETTE_OPEN_EVENT));
}
