import React, { useState } from 'react'
import { Box, Text } from '../ink.js'
import { useKeybinding } from '../keybindings/useKeybinding.js'
import { saveApiKey } from '../utils/auth.js'
import { useTerminalSize } from '../hooks/useTerminalSize.js'
import TextInput from './TextInput.js'

type Props = {
  onDone(): void
  startingMessage?: string
  mode?: 'login' | 'setup-token'
  forceLoginMethod?: 'claudeai' | 'console'
}

type Status =
  | { state: 'input' }
  | { state: 'saving' }
  | { state: 'success' }
  | { state: 'error'; message: string }

export function ConsoleOAuthFlow({
  onDone,
  startingMessage,
}: Props): React.ReactNode {
  const [apiKey, setApiKey] = useState('')
  const [cursorOffset, setCursorOffset] = useState(0)
  const [status, setStatus] = useState<Status>({ state: 'input' })
  const columns = Math.max(24, useTerminalSize().columns - 24)

  useKeybinding(
    'confirm:yes',
    () => {
      onDone()
    },
    {
      context: 'Confirmation',
      isActive: status.state === 'success',
    },
  )

  useKeybinding(
    'confirm:yes',
    () => {
      setStatus({ state: 'input' })
    },
    {
      context: 'Confirmation',
      isActive: status.state === 'error',
    },
  )

  async function submitFriendliApiKey(value: string): Promise<void> {
    setStatus({ state: 'saving' })
    try {
      await saveApiKey(value)
      setApiKey('')
      setCursorOffset(0)
      setStatus({ state: 'success' })
    } catch (error) {
      setStatus({
        state: 'error',
        message: error instanceof Error ? error.message : String(error),
      })
    }
  }

  if (status.state === 'success') {
    return (
      <Box flexDirection="column">
        <Text color="success">FriendliAI login successful.</Text>
        <Text>Press Enter to continue.</Text>
      </Box>
    )
  }

  if (status.state === 'error') {
    return (
      <Box flexDirection="column">
        <Text color="error">{status.message}</Text>
        <Text>Press Enter to try again.</Text>
      </Box>
    )
  }

  return (
    <Box flexDirection="column">
      {startingMessage ? <Text>{startingMessage}</Text> : null}
      <Text>Paste your FriendliAI API key.</Text>
      <Box>
        <Text>FriendliAI API key: </Text>
        <TextInput
          value={apiKey}
          onChange={setApiKey}
          onSubmit={submitFriendliApiKey}
          cursorOffset={cursorOffset}
          onChangeCursorOffset={setCursorOffset}
          columns={columns}
          mask="*"
          focus={status.state === 'input'}
          showCursor={status.state === 'input'}
        />
      </Box>
      {status.state === 'saving' ? <Text>Saving FriendliAI API key...</Text> : null}
    </Box>
  )
}
