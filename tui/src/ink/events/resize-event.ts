// [P0 reconstructed · Pass 3 v2 · agent-verified · Ink resize event]
// Reference: Node `process.stdout.on('resize', …)` + ink/ink.tsx L226
// (`options.stdout.on('resize', handleResize)`) + sibling KeyboardEvent pattern.
//
// When the TTY emits SIGWINCH, stdout fires 'resize'. Ink intercepts and
// re-measures the root container, then dispatches this event so React
// subtrees can react to viewport changes (reflow logs, truncate text, etc).
//
// Callers MUST supply previous dimensions explicitly — the agent-reported
// v1 default (`previousColumns = columns`) made deltas always zero.

import { TerminalEvent } from './terminal-event.js'

/**
 * Resize event dispatched when the terminal viewport changes dimensions.
 * `columns`/`rows` are the new post-resize values (from
 * `process.stdout.columns` / `rows`); `previousColumns`/`previousRows` are
 * the last-known values; `deltaColumns`/`deltaRows` are signed deltas for
 * layout logic.
 */
export class ResizeEvent extends TerminalEvent {
  readonly columns: number
  readonly rows: number
  readonly previousColumns: number
  readonly previousRows: number
  readonly deltaColumns: number
  readonly deltaRows: number

  constructor(
    columns: number,
    rows: number,
    previousColumns: number,
    previousRows: number,
  ) {
    super('resize', { bubbles: true, cancelable: false })
    this.columns = columns
    this.rows = rows
    this.previousColumns = previousColumns
    this.previousRows = previousRows
    this.deltaColumns = columns - previousColumns
    this.deltaRows = rows - previousRows
  }
}
