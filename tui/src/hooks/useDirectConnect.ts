// SPDX-License-Identifier: Apache-2.0
//
// KOSMOS-1633 P1+P2 / KOSMOS-1978 T011 — useDirectConnect stubbed.
//
// Original CC module: `tui/src/hooks/useDirectConnect.ts` (CC 2.1.88) drives
// Anthropic's "direct connect" remote-session mode where the TUI proxies
// messages to a hosted Anthropic agent via WebSocket. KOSMOS citizen TUI is
// strictly local — there is no remote agent to connect to. The hook is
// preserved as a no-op so screens/REPL.tsx continues to compile without a
// branching guard at every call site.

import type { ToolUseConfirm } from '../components/permissions/PermissionRequest.js'
import type { Tool } from '../Tool.js'
import type { Message as MessageType } from '../types/message.js'

export type DirectConnectConfig = {
  url?: string
  hasInitialPrompt?: boolean
}

type UseDirectConnectResult = {
  isRemoteMode: boolean
  sendMessage: (content: unknown) => Promise<boolean>
  cancelRequest: () => void
  disconnect: () => void
}

type UseDirectConnectProps = {
  config: DirectConnectConfig | undefined
  setMessages: React.Dispatch<React.SetStateAction<MessageType[]>>
  setIsLoading: (loading: boolean) => void
  setToolUseConfirmQueue: React.Dispatch<React.SetStateAction<ToolUseConfirm[]>>
  tools: Tool[]
}

export function useDirectConnect(_props: UseDirectConnectProps): UseDirectConnectResult {
  return {
    isRemoteMode: false,
    sendMessage: async () => false,
    cancelRequest: () => undefined,
    disconnect: () => undefined,
  }
}
