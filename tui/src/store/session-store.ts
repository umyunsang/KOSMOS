// Source: .references/claude-code-sourcemap/restored-src/src/state/store.ts (Claude Code 2.1.88, research-use)
// createStore pattern lifted verbatim; SessionState, Action discriminated union,
// and useSessionStore hook are KOSMOS-original following data-model.md § 3.
import { useSyncExternalStore } from 'react'

// ---------------------------------------------------------------------------
// Generic store primitive (≈35-line pattern from restored-src/src/state/store.ts)
// ---------------------------------------------------------------------------

type Listener = () => void

type Store<T> = {
  getState: () => T
  setState: (updater: (prev: T) => T) => void
  subscribe: (listener: Listener) => () => void
  dispatch: (action: SessionAction) => void
}

function createStore<T>(
  initialState: T,
  reducer: (state: T, action: SessionAction) => T,
): Store<T> {
  let state = initialState
  const listeners = new Set<Listener>()

  return {
    getState: () => state,

    setState: (updater: (prev: T) => T) => {
      const prev = state
      const next = updater(prev)
      if (Object.is(next, prev)) return
      state = next
      for (const listener of listeners) listener()
    },

    dispatch: (action: SessionAction) => {
      const prev = state
      const next = reducer(prev, action)
      if (Object.is(next, prev)) return
      state = next
      for (const listener of listeners) listener()
    },

    subscribe: (listener: Listener) => {
      listeners.add(listener)
      return () => listeners.delete(listener)
    },
  }
}

// ---------------------------------------------------------------------------
// KOSMOS session state — data-model.md § 3
// ---------------------------------------------------------------------------

/** One of the four coordinator phases from Spec 031 */
export type Phase =
  | 'Research'
  | 'Synthesis'
  | 'Implementation'
  | 'Verification'

/** Per-worker status entry (worker_status IPC frame payload) */
export interface WorkerStatus {
  worker_id: string
  role_id: string
  current_primitive: string
  status: 'idle' | 'running' | 'waiting_permission' | 'error'
}

/** Pending permission request that blocks user input */
export interface PermissionRequest {
  request_id: string
  correlation_id: string
  worker_id: string
  primitive_kind: string
  description_ko: string
  description_en: string
  risk_level: 'low' | 'medium' | 'high'
}

/** One assembled message in the conversation */
export interface Message {
  id: string
  role: 'user' | 'assistant'
  /** Accumulated assistant delta strings; empty for user messages */
  chunks: string[]
  done: boolean
  tool_calls: ToolCall[]
  tool_results: ToolResult[]
}

export interface ToolCall {
  call_id: string
  name: string
  arguments: Record<string, unknown>
}

export interface ToolResult {
  call_id: string
  envelope: Record<string, unknown>
}

export interface CrashNotice {
  code: string
  message: string
  details: Record<string, unknown>
}

/** Full ephemeral render-state — data-model.md § 3.1 */
export interface SessionState {
  session_id: string
  messages: Map<string, Message>
  message_order: string[]
  coordinator_phase: Phase | null
  workers: Map<string, WorkerStatus>
  pending_permission: PermissionRequest | null
  crash: CrashNotice | null
}

// ---------------------------------------------------------------------------
// Action discriminated union — data-model.md § 3.2
// ---------------------------------------------------------------------------

export type SessionAction =
  | { type: 'USER_INPUT'; message_id: string; text: string }
  | {
      type: 'ASSISTANT_CHUNK'
      message_id: string
      delta: string
      done: boolean
    }
  | { type: 'TOOL_CALL'; message_id: string; tool_call: ToolCall }
  | { type: 'TOOL_RESULT'; call_id: string; envelope: Record<string, unknown> }
  | { type: 'COORDINATOR_PHASE'; phase: Phase }
  | { type: 'WORKER_STATUS'; status: WorkerStatus }
  | { type: 'PERMISSION_REQUEST'; request: PermissionRequest }
  | { type: 'PERMISSION_RESPONSE' }
  | {
      type: 'SESSION_EVENT'
      event: 'save' | 'load' | 'list' | 'resume' | 'new' | 'exit'
      payload: Record<string, unknown>
    }
  | { type: 'ERROR'; code: string; message: string; details: Record<string, unknown> }
  | { type: 'CRASH'; notice: CrashNotice }

// ---------------------------------------------------------------------------
// Reducer
// ---------------------------------------------------------------------------

function getOrCreateAssistantMessage(
  state: SessionState,
  message_id: string,
): Message {
  return (
    state.messages.get(message_id) ?? {
      id: message_id,
      role: 'assistant',
      chunks: [],
      done: false,
      tool_calls: [],
      tool_results: [],
    }
  )
}

function sessionReducer(
  state: SessionState,
  action: SessionAction,
): SessionState {
  switch (action.type) {
    case 'USER_INPUT': {
      const msg: Message = {
        id: action.message_id,
        role: 'user',
        chunks: [action.text],
        done: true,
        tool_calls: [],
        tool_results: [],
      }
      const messages = new Map(state.messages)
      messages.set(msg.id, msg)
      return {
        ...state,
        messages,
        message_order: [...state.message_order, msg.id],
      }
    }

    case 'ASSISTANT_CHUNK': {
      const existing = getOrCreateAssistantMessage(state, action.message_id)
      if (existing.done) return state // discard post-done chunks
      const updated: Message = {
        ...existing,
        chunks: [...existing.chunks, action.delta],
        done: action.done,
      }
      const messages = new Map(state.messages)
      messages.set(action.message_id, updated)
      const message_order = state.messages.has(action.message_id)
        ? state.message_order
        : [...state.message_order, action.message_id]
      return { ...state, messages, message_order }
    }

    case 'TOOL_CALL': {
      const existing = getOrCreateAssistantMessage(state, action.message_id)
      const updated: Message = {
        ...existing,
        tool_calls: [...existing.tool_calls, action.tool_call],
      }
      const messages = new Map(state.messages)
      messages.set(action.message_id, updated)
      return { ...state, messages }
    }

    case 'TOOL_RESULT': {
      // Attach result to the message that owns the matching call_id
      const messages = new Map(state.messages)
      for (const [id, msg] of messages) {
        if (msg.tool_calls.some(tc => tc.call_id === action.call_id)) {
          messages.set(id, {
            ...msg,
            tool_results: [
              ...msg.tool_results,
              { call_id: action.call_id, envelope: action.envelope },
            ],
          })
          break
        }
      }
      return { ...state, messages }
    }

    case 'COORDINATOR_PHASE':
      return { ...state, coordinator_phase: action.phase }

    case 'WORKER_STATUS': {
      const workers = new Map(state.workers)
      workers.set(action.status.worker_id, action.status)
      return { ...state, workers }
    }

    case 'PERMISSION_REQUEST':
      return { ...state, pending_permission: action.request }

    case 'PERMISSION_RESPONSE':
      return { ...state, pending_permission: null }

    case 'SESSION_EVENT': {
      if (action.event === 'new') {
        return {
          ...initialSessionState(state.session_id),
        }
      }
      if (action.event === 'load') {
        // FR-052: replay persisted messages directly with done:true so
        // MessageList does not animate them as streaming content.
        const rawMessages = action.payload['messages']
        if (!Array.isArray(rawMessages)) {
          console.warn('[session-store] SESSION_EVENT load: payload.messages is not an array — ignoring')
          return state
        }
        const messages = new Map<string, Message>()
        const message_order: string[] = []
        for (const raw of rawMessages) {
          if (
            raw === null ||
            typeof raw !== 'object' ||
            typeof (raw as Record<string, unknown>)['id'] !== 'string'
          ) {
            console.warn('[session-store] SESSION_EVENT load: skipping entry missing required id field', raw)
            continue
          }
          const entry = raw as Record<string, unknown>
          const msg: Message = {
            id: entry['id'] as string,
            role: (entry['role'] === 'user' || entry['role'] === 'assistant') ? entry['role'] : 'assistant',
            chunks: Array.isArray(entry['chunks'])
              ? (entry['chunks'] as unknown[]).map(String)
              : [],
            done: true, // always mark done — no streaming animation (FR-052)
            tool_calls: Array.isArray(entry['tool_calls'])
              ? (entry['tool_calls'] as ToolCall[])
              : [],
            tool_results: Array.isArray(entry['tool_results'])
              ? (entry['tool_results'] as ToolResult[])
              : [],
          }
          messages.set(msg.id, msg)
          message_order.push(msg.id)
        }
        const session_id =
          typeof action.payload['session_id'] === 'string'
            ? action.payload['session_id']
            : state.session_id
        return {
          ...state,
          session_id,
          messages,
          message_order,
        }
      }
      // Other session events (save, list, resume, exit) are handled
      // as side-effects by the IPC bridge; reducer leaves state intact.
      return state
    }

    case 'ERROR': {
      const errId = `error-${Date.now()}-${Math.random().toString(36).slice(2)}`
      const errMsg: Message = {
        id: errId,
        role: 'assistant',
        chunks: [`[ERROR ${action.code}] ${action.message}`],
        done: true,
        tool_calls: [],
        tool_results: [],
      }
      const messages = new Map(state.messages)
      messages.set(errId, errMsg)
      return {
        ...state,
        messages,
        message_order: [...state.message_order, errId],
      }
    }

    case 'CRASH':
      return { ...state, crash: action.notice }

    default:
      return state
  }
}

// ---------------------------------------------------------------------------
// Store singleton + exported hook — data-model.md § 3.3
// ---------------------------------------------------------------------------

function initialSessionState(session_id: string): SessionState {
  return {
    session_id,
    messages: new Map(),
    message_order: [],
    coordinator_phase: null,
    workers: new Map(),
    pending_permission: null,
    crash: null,
  }
}

/** Module-level singleton.  Reset via SESSION_EVENT new. */
const sessionStore = createStore<SessionState>(
  initialSessionState(''),
  sessionReducer,
)

/**
 * Subscribe to a slice of SessionState via useSyncExternalStore.
 * Only components whose selector result changes (Object.is) re-render.
 *
 * @example
 *   const phase = useSessionStore(s => s.coordinator_phase)
 *   const msgs  = useSessionStore(s => s.message_order)
 */
export function useSessionStore<T>(selector: (state: SessionState) => T): T {
  return useSyncExternalStore(
    sessionStore.subscribe,
    () => selector(sessionStore.getState()),
    () => selector(sessionStore.getState()),
  )
}

/** Dispatch an action to the session store */
export function dispatchSessionAction(action: SessionAction): void {
  sessionStore.dispatch(action)
}

/** Direct snapshot access for non-React code (IPC bridge, tests) */
export function getSessionSnapshot(): SessionState {
  return sessionStore.getState()
}

export { sessionStore }
