// KOSMOS-original session command: /new
// Emits session_event IPC frame with event="new".
// The session store's SESSION_EVENT "new" arm clears state (data-model.md § 3.2).

import type { CommandDefinition, CommandHandlerArgs, CommandResult } from './types'
import en from '../i18n/en'

function handle({ sendFrame }: CommandHandlerArgs): CommandResult {
  const now = new Date().toISOString()
  sendFrame({
    kind: 'session_event',
    session_id: '',
    correlation_id: null,
    ts: now,
    event: 'new',
    payload: {},
  })
  // Store is cleared via the SESSION_EVENT "new" reducer in session-store.ts
  return { acknowledgement: en.cmdNewAck }
}

const newCommand: CommandDefinition = {
  name: 'new',
  description: 'Start a new session (clears current conversation)',
  handle,
}

export default newCommand
