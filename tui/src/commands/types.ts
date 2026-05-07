// KOSMOS-original command type definitions.
// These are NOT lifted from .references/ — they are purpose-built for KOSMOS.

import type { PluginOpFrame, SessionEventFrame } from '../ipc/frames.generated'

// ---------------------------------------------------------------------------
// SendFrame callback type — dependency-injected, never imported directly
// ---------------------------------------------------------------------------

/**
 * Callback injected into the dispatcher at construction time.
 * Team A wires this to the actual IPC bridge at T050.
 *
 * TODO(T050): Wire dispatcher into tui/src/entrypoints/tui.tsx — slash-prefixed
 * input intercepted before user_input frame emission. The dispatcher's
 * sendFrame prop should be wired to bridge.sendFrame there.
 */
export type SendFrame = (frame: SessionEventFrame) => void

/**
 * Plugin-op frame send callback (Spec 032 IPC arm 20). Separate from
 * `SendFrame` so existing session-event commands (save/sessions/resume/new)
 * keep their narrow typing — only the new plugin commands receive this
 * second callback.
 */
export type SendPluginOp = (frame: PluginOpFrame) => void

// ---------------------------------------------------------------------------
// CommandHandlerArgs
// ---------------------------------------------------------------------------

/** Arguments passed to every command handler */
export interface CommandHandlerArgs {
  /** Remainder text after the command name (trimmed), e.g. "abc123" for "/resume abc123" */
  args: string
  /** Injected IPC send callback — DO NOT import bridge directly */
  sendFrame: SendFrame
  /**
   * Optional plugin-op send callback. Present when the dispatcher was
   * constructed with the plugin command set; only `/plugin install`,
   * `/plugin list`, `/plugin uninstall` use it.
   */
  sendPluginOp?: SendPluginOp
}

// ---------------------------------------------------------------------------
// CommandResult
// ---------------------------------------------------------------------------

/**
 * Value returned from a command handler.
 *
 * - `acknowledgement`: i18n-keyed string shown to the user in the conversation
 *   as a transient notice (not stored in session).
 * - `renderHelp`: when true, the UI should render <HelpView /> with an optional
 *   error banner (for unknown command paths).
 */
export interface CommandResult {
  acknowledgement: string
  renderHelp?: boolean
}

// ---------------------------------------------------------------------------
// CommandDefinition
// ---------------------------------------------------------------------------

/**
 * A registered slash command.  The name MUST match what follows the "/" in
 * the user's input, e.g. name: "save" matches "/save".
 */
export interface CommandDefinition {
  /** Slash command name without the leading "/" */
  name: string
  /** Short human-readable description shown in help */
  description: string
  /** Optional aliases (e.g. ["continue"] for "resume") */
  aliases?: string[]
  /** Argument hint shown in help, e.g. "[session-id]" */
  argumentHint?: string
  /** Handler implementation */
  handle: (args: CommandHandlerArgs) => CommandResult | Promise<CommandResult>
}
