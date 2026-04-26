// SPDX-License-Identifier: Apache-2.0
//
// KOSMOS-1633 P1+P2 / KOSMOS-1978 T011 — useSSHSession stubbed.
//
// Original CC module: `tui/src/hooks/useSSHSession.ts` (CC 2.1.88) drives
// `claude ssh` sessions where the TUI front-ends an SSH child process
// running the agent on a remote host. KOSMOS citizen TUI is local-only and
// does not ship the `ssh` subcommand. Stub returns `isRemoteMode: false` so
// REPL.tsx skips the SSH branch.

import type { ToolUseConfirm } from '../components/permissions/PermissionRequest.js'
import type { Tool } from '../Tool.js'
import type { Message as MessageType } from '../types/message.js'

type UseSSHSessionResult = {
  isRemoteMode: boolean
  sendMessage: (content: unknown) => Promise<boolean>
  cancelRequest: () => void
  disconnect: () => void
}

type UseSSHSessionProps = {
  session: unknown
  setMessages: React.Dispatch<React.SetStateAction<MessageType[]>>
  setIsLoading: (loading: boolean) => void
  setToolUseConfirmQueue: React.Dispatch<React.SetStateAction<ToolUseConfirm[]>>
  tools: Tool[]
}

export function useSSHSession(_props: UseSSHSessionProps): UseSSHSessionResult {
  return {
    isRemoteMode: false,
    sendMessage: async () => false,
    cancelRequest: () => undefined,
    disconnect: () => undefined,
  }
}
