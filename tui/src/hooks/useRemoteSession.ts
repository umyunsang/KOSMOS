// SPDX-License-Identifier: Apache-2.0
//
// KOSMOS-1633 P1+P2 / KOSMOS-1978 T011 — useRemoteSession stubbed.
//
// Original CC module: `tui/src/hooks/useRemoteSession.ts` (CC 2.1.88) drives
// the Anthropic CCR (Claude Code Remote) WebSocket session. KOSMOS citizen
// TUI is local-only — there is no Anthropic-hosted session to attach to.
// Stub returns `isRemoteMode: false` so REPL.tsx skips the entire remote
// branch and behaves as a local interactive session.

import type { ToolUseConfirm } from '../components/permissions/PermissionRequest.js'
import type { SpinnerMode } from '../components/Spinner/types.js'
import type { Tool } from '../Tool.js'
import type { Message as MessageType } from '../types/message.js'

export type RemoteSessionConfig = {
  hasInitialPrompt?: boolean
  url?: string
  sessionId?: string
}

type UseRemoteSessionProps = {
  config: RemoteSessionConfig | undefined
  setMessages: React.Dispatch<React.SetStateAction<MessageType[]>>
  setIsLoading: (loading: boolean) => void
  onInit?: (slashCommands: string[]) => void
  setToolUseConfirmQueue: React.Dispatch<React.SetStateAction<ToolUseConfirm[]>>
  tools: Tool[]
  setStreamingToolUses?: React.Dispatch<React.SetStateAction<unknown[]>>
  setStreamMode?: React.Dispatch<React.SetStateAction<SpinnerMode>>
  setInProgressToolUseIDs?: (f: (prev: Set<string>) => Set<string>) => void
}

type UseRemoteSessionResult = {
  isRemoteMode: boolean
  sendMessage: (content: unknown, opts?: { uuid?: string }) => Promise<boolean>
  cancelRequest: () => void
  disconnect: () => void
}

export function useRemoteSession(_props: UseRemoteSessionProps): UseRemoteSessionResult {
  return {
    isRemoteMode: false,
    sendMessage: async () => false,
    cancelRequest: () => undefined,
    disconnect: () => undefined,
  }
}
