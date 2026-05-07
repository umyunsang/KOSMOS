// KOSMOS-original session command: /save
// Emits session_event IPC frame with event="save".

import type { CommandDefinition, CommandHandlerArgs, CommandResult } from './types'
import { i18n } from '../i18n'

function handle({ sendFrame }: CommandHandlerArgs): CommandResult {
  const now = new Date().toISOString()
  sendFrame({
    kind: 'session_event',
    // session_id and ts are placeholders — Team A fills these in at the bridge
    // layer (T050) when wiring the dispatcher to the IPC bridge.
    session_id: '',
    correlation_id: crypto.randomUUID(),
    ts: now,
    role: 'tui',
    event: 'save',
    payload: {},
  })
  return { acknowledgement: i18n.cmdSaveAck }
}

const saveCommand: CommandDefinition = {
  name: 'save',
  description: 'Save the current session',
  handle,
}

export default saveCommand
