// KOSMOS-original session command: /sessions
// Emits session_event IPC frame with event="list".
// Backend streams back session metadata in a matching session_event list payload.

import type { CommandDefinition, CommandHandlerArgs, CommandResult } from './types'
import en from '../i18n/en'

function handle({ sendFrame }: CommandHandlerArgs): CommandResult {
  const now = new Date().toISOString()
  sendFrame({
    kind: 'session_event',
    session_id: '',
    correlation_id: null,
    ts: now,
    event: 'list',
    payload: {},
  })
  return { acknowledgement: en.cmdSessionsAck }
}

const sessionsCommand: CommandDefinition = {
  name: 'sessions',
  description: 'List saved sessions',
  handle,
}

export default sessionsCommand
