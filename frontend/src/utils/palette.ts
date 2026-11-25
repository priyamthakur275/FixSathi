/** The command palette (Ctrl K / Cmd K) listens for this event, so any button can open it. */
export const OPEN_PALETTE = 'fixsaathi:palette'
export const openPalette = () => window.dispatchEvent(new Event(OPEN_PALETTE))
export const isMac = () => typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)
