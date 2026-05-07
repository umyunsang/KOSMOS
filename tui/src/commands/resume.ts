// KOSMOS-original session command: /resume [session-id]
// Emits session_event IPC frame with event="resume" and payload={id: sessionId}.

import type { CommandDefinition, CommandHandlerArgs, CommandResult } from './types'
import { i18n } from '../i18n'

function handle({ args, sendFrame }: CommandHandlerArgs): CommandResult {
  const sessionId = args.trim()
  if (!sessionId) {
    return {
      acknowledgement: i18n.cmdResumeMissingId,
    }
  }

  const now = new Date().toISOString()
  sendFrame({
    kind: 'session_event',
    session_id: '',
    correlation_id: crypto.randomUUID(),
    ts: now,
    role: 'tui',
    event: 'resume',
    payload: { id: sessionId },
  })
  return { acknowledgement: i18n.cmdResumeAck(sessionId) }
}

const resumeCommand: CommandDefinition = {
  name: 'resume',
  description: 'Resume a previous session by ID',
  aliases: ['continue'],
  argumentHint: '[session-id]',
  handle,
}

export default resumeCommand
