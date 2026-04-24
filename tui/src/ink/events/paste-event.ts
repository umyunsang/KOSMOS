// [P0 reconstructed · Pass 3 · Ink paste event]
// Reference: Ink v7 `usePaste` hook + VT100 bracketed paste mode
//            (ECMA-48 escape sequences `\x1b[200~` … `\x1b[201~`).
// Sibling pattern: `./keyboard-event.ts`, `./click-event.ts` — all extend
// TerminalEvent with specific event properties.
//
// Bracketed paste (enabled via `\x1b[?2004h`) wraps pasted text in markers
// so terminals can distinguish paste from direct keyboard input. The parser
// upstream of Ink (`parse-keypress.ts`) extracts the raw pasted text; this
// event delivers it as a single string to React handlers, bubbling through
// the focus tree like browser PasteEvents.

import { TerminalEvent } from './terminal-event.js'

/**
 * Paste event dispatched when bracketed-paste markers wrap incoming bytes.
 *
 * `data` is the raw pasted text with newlines, escape sequences, and other
 * special characters preserved exactly as pasted (matches Ink v7 usePaste
 * semantics — no splitting into per-key events).
 */
export class PasteEvent extends TerminalEvent {
  readonly data: string

  constructor(data: string) {
    super('paste', { bubbles: true, cancelable: true })
    this.data = data
  }
}

/** Bracketed-paste enable/disable escape sequences (ECMA-48). */
export const BRACKETED_PASTE_ENABLE = '\x1b[?2004h'
export const BRACKETED_PASTE_DISABLE = '\x1b[?2004l'

/** The start/end markers that frame pasted content in the input stream. */
export const BRACKETED_PASTE_START = '\x1b[200~'
export const BRACKETED_PASTE_END = '\x1b[201~'
