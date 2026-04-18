// Source: .references/claude-code-sourcemap/restored-src/src/commands.ts (Claude Code 2.1.88, research-use)
// Lifted structural pattern: command registry map, findCommand, dispatchCommand.
// All KOSMOS-domain logic (IPC frames, session events, help renderer) is original.

import type { CommandDefinition, CommandHandlerArgs, CommandResult, SendFrame } from './types'

// ---------------------------------------------------------------------------
// CommandRegistry
// ---------------------------------------------------------------------------

/** Map from canonical command name → definition */
export type CommandRegistry = Map<string, CommandDefinition>

/**
 * Create a new (empty) command registry.
 * Use registerCommand() to populate it.
 */
export function createRegistry(): CommandRegistry {
  return new Map()
}

/**
 * Register a command into the registry.
 * Both the canonical name and any aliases are indexed.
 *
 * Throws if a name/alias is already registered to prevent silent shadowing.
 */
export function registerCommand(
  registry: CommandRegistry,
  def: CommandDefinition,
): void {
  if (registry.has(def.name)) {
    throw new Error(`Command already registered: "${def.name}"`)
  }
  registry.set(def.name, def)

  for (const alias of def.aliases ?? []) {
    if (registry.has(alias)) {
      throw new Error(`Command alias already registered: "${alias}" (for command "${def.name}")`)
    }
    registry.set(alias, def)
  }
}

// ---------------------------------------------------------------------------
// Input parsing
// ---------------------------------------------------------------------------

/**
 * Returns true if raw input is a slash command (starts with "/").
 * Leading whitespace is significant — "  /save" is NOT a command.
 */
export function isSlashCommand(input: string): boolean {
  return input.startsWith('/')
}

/**
 * Parse a raw slash-command string into { name, args }.
 *
 * Examples:
 *   "/save"                 → { name: "save", args: "" }
 *   "/resume abc123"        → { name: "resume", args: "abc123" }
 *   '/resume "my session"'  → { name: "resume", args: '"my session"' }
 *   "/new  extra stuff"     → { name: "new", args: "extra stuff" }
 */
export function parseSlashCommand(input: string): { name: string; args: string } {
  if (!input.startsWith('/')) {
    return { name: '', args: input.trim() }
  }
  const withoutSlash = input.slice(1)
  const spaceIdx = withoutSlash.indexOf(' ')
  if (spaceIdx === -1) {
    return { name: withoutSlash.trim().toLowerCase(), args: '' }
  }
  const name = withoutSlash.slice(0, spaceIdx).trim().toLowerCase()
  const args = withoutSlash.slice(spaceIdx + 1).trim()
  return { name, args }
}

// ---------------------------------------------------------------------------
// Dispatcher
// ---------------------------------------------------------------------------

export interface DispatchResult extends CommandResult {
  /** Name that was dispatched (empty string if input was not a slash command) */
  commandName: string
}

/**
 * Central command dispatcher.
 *
 * @param input   Raw user input string
 * @param registry  The command registry to look up against
 * @param sendFrame IPC send callback injected by Team A at T050 wiring
 *
 * @returns DispatchResult — always resolves (never throws to the caller).
 *   If the command is unknown, renderHelp:true is set and acknowledgement
 *   contains an error notice keyed via the i18n bundle.
 */
export async function dispatchCommand(
  input: string,
  registry: CommandRegistry,
  sendFrame: SendFrame,
): Promise<DispatchResult> {
  // Empty / blank input — no-op
  if (!input.trim()) {
    return {
      commandName: '',
      acknowledgement: '',
    }
  }

  // Not a slash command — caller should emit user_input frame instead
  if (!isSlashCommand(input)) {
    return {
      commandName: '',
      acknowledgement: '',
    }
  }

  const { name, args } = parseSlashCommand(input)

  // Empty command name ("/  ") — show help
  if (!name) {
    return {
      commandName: '',
      acknowledgement: '',
      renderHelp: true,
    }
  }

  const def = registry.get(name)

  // Unknown command — return help render signal
  if (!def) {
    return {
      commandName: name,
      acknowledgement: `Unknown command: /${name}`,
      renderHelp: true,
    }
  }

  const handlerArgs: CommandHandlerArgs = { args, sendFrame }

  try {
    const result = await def.handle(handlerArgs)
    return { commandName: name, ...result }
  } catch (err: unknown) {
    const message = err instanceof Error ? err.message : String(err)
    return {
      commandName: name,
      acknowledgement: `/${name} failed: ${message}`,
    }
  }
}

// ---------------------------------------------------------------------------
// Registry introspection helpers (used by HelpView)
// ---------------------------------------------------------------------------

/**
 * Returns the unique set of command definitions (deduplicated by canonical name
 * so aliases don't produce double entries).
 */
export function listCommands(registry: CommandRegistry): CommandDefinition[] {
  const seen = new Set<CommandDefinition>()
  const result: CommandDefinition[] = []
  for (const def of registry.values()) {
    if (!seen.has(def)) {
      seen.add(def)
      result.push(def)
    }
  }
  return result.sort((a, b) => a.name.localeCompare(b.name))
}
