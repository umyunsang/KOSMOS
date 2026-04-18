// KOSMOS-original command registry builder.
// Wires the four session commands into the default registry.
//
// Usage:
//   import { buildDefaultRegistry } from './commands/index.ts'
//   const registry = buildDefaultRegistry()

import { createRegistry, registerCommand, type CommandRegistry } from './dispatcher'
import saveCommand from './save'
import sessionsCommand from './sessions'
import resumeCommand from './resume'
import newCommand from './new'

/**
 * Build and return the default KOSMOS command registry containing:
 *   /save      — save current session
 *   /sessions  — list sessions
 *   /resume    — resume session by id  (alias: /continue)
 *   /new       — start a new session
 */
export function buildDefaultRegistry(): CommandRegistry {
  const registry = createRegistry()
  registerCommand(registry, saveCommand)
  registerCommand(registry, sessionsCommand)
  registerCommand(registry, resumeCommand)
  registerCommand(registry, newCommand)
  return registry
}

export { createRegistry, registerCommand } from './dispatcher'
export type { CommandDefinition, CommandHandlerArgs, CommandResult, SendFrame } from './types'
