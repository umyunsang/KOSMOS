#!/usr/bin/env bun
/**
 * ink-rehearsal.tsx — Spec 1978 T080 in-process TUI rehearsal harness.
 *
 * Replaces the Python `pty.fork`-based `scripts/pty-scenario.py` (which hits
 * an `OSError [Errno 5] EIO` against Bun's stdin raw-mode transition — see
 * `docs/spec-1978/rehearsal-2026-04-27.md` § S3).
 *
 * Strategy: ink-testing-library mounts the actual Ink components in-process
 * with a mocked stdin/stdout. We:
 *   1. Spawn the real Python backend (`uv run kosmos --ipc stdio`) via the
 *      production `createBridge()` IPC bridge.
 *   2. Mount a minimal `<RehearsalHarness />` Ink component using
 *      `ink-testing-library`'s `render()`.
 *   3. Simulate the citizen's keystrokes via `stdin.write()`.
 *   4. The component echoes typed chars locally, sends a `ChatRequestFrame`
 *      on Enter, and renders inbound `assistant_chunk` / `tool_call` /
 *      `error` frames.
 *   5. Capture the final frame buffer and print it as readable JSON.
 *
 * Usage:
 *   bun run scripts/ink-rehearsal.tsx greeting
 *   bun run scripts/ink-rehearsal.tsx lookup-emergency-room
 *
 * Env: KOSMOS_FRIENDLI_TOKEN must be exported (or in `.env` sourced before
 * invocation). Without it the backend will return an error frame; the
 * rehearsal still completes with a structured failure summary.
 */

import { render } from 'ink-testing-library'
import { Box, Text, useInput } from 'ink'
import * as React from 'react'
import { useEffect, useState } from 'react'
import { createBridge, type IPCBridge } from '../src/ipc/bridge.js'
import type { IPCFrame } from '../src/ipc/codec.js'

// ---------------------------------------------------------------------------
// Scenario catalogue
// ---------------------------------------------------------------------------

type Scenario = {
  name: string
  description: string
  prompt: string  // text typed into the prompt before Enter
  timeoutMs: number
  expectedKinds: ReadonlyArray<string>
}

const SCENARIOS: Record<string, Scenario> = {
  greeting: {
    name: 'greeting',
    description: 'US1 — citizen says hello (FR-001 / SC-001)',
    prompt: '안녕하세요',
    timeoutMs: 60_000,
    expectedKinds: ['assistant_chunk'],
  },
  'lookup-emergency-room': {
    name: 'lookup-emergency-room',
    description: 'US1 — emergency room lookup chain (SC-001)',
    prompt: '강남구 응급실 알려줘',
    timeoutMs: 90_000,
    expectedKinds: ['assistant_chunk'],
  },
}

// ---------------------------------------------------------------------------
// Harness Ink component
// ---------------------------------------------------------------------------

type Props = {
  bridge: IPCBridge
  prompt: string
  onComplete: (summary: RehearsalSummary) => void
  timeoutMs: number
}

type RehearsalSummary = {
  scenario: string
  success: boolean
  prompt: string
  framesReceived: number
  assistantText: string
  kinds: Record<string, number>
  firstFrameMs: number | null
  lastFrameMs: number | null
  error?: string
}

function RehearsalHarness({ bridge, prompt, onComplete, timeoutMs }: Props): React.ReactElement {
  const [typed, setTyped] = useState('')
  const [submitted, setSubmitted] = useState(false)
  const [transcript, setTranscript] = useState<string[]>([])
  const [framesSeen, setFramesSeen] = useState(0)

  // Capture keystrokes — when the test stdin pushes chars, accumulate; on
  // Enter (\r) we lock the input and emit the ChatRequestFrame.
  useInput((input, key) => {
    if (submitted) return
    if (key.return) {
      setSubmitted(true)
      return
    }
    setTyped((prev) => prev + input)
  })

  // After Enter is pressed, dispatch the ChatRequestFrame and start the
  // frame collector. Closes when terminal assistant_chunk{done=true} or
  // error frame arrives, or on timeout.
  useEffect(() => {
    if (!submitted) return

    const start = Date.now()
    const summary: RehearsalSummary = {
      scenario: prompt,
      success: false,
      prompt: typed,
      framesReceived: 0,
      assistantText: '',
      kinds: {},
      firstFrameMs: null,
      lastFrameMs: null,
    }

    const correlationId = crypto.randomUUID()
    const sent = bridge.send({
      kind: 'chat_request',
      version: '1.0',
      session_id: '',
      correlation_id: correlationId,
      role: 'tui',
      frame_seq: 0,
      transaction_id: null,
      trailer: null,
      ts: new Date().toISOString(),
      messages: [{ role: 'user', content: typed }],
      tools: [],
      system: null,
      max_tokens: 8192,
      temperature: 1.0,
      top_p: 0.95,
    } as unknown as IPCFrame)

    if (!sent) {
      summary.error = 'bridge.send returned false (backend already exited)'
      onComplete(summary)
      return
    }

    let stopped = false
    const watchdog = setTimeout(() => {
      stopped = true
      summary.error = `timeout after ${timeoutMs}ms`
      onComplete(summary)
    }, timeoutMs)

    void (async () => {
      try {
        for await (const frame of bridge.frames()) {
          if (stopped) break
          if (summary.firstFrameMs === null) {
            summary.firstFrameMs = Date.now() - start
          }
          summary.lastFrameMs = Date.now() - start
          summary.framesReceived++
          summary.kinds[frame.kind] = (summary.kinds[frame.kind] ?? 0) + 1
          setFramesSeen((n) => n + 1)

          if (frame.kind === 'assistant_chunk') {
            const delta = (frame as { delta?: string }).delta ?? ''
            summary.assistantText += delta
            setTranscript((prev) => {
              const updated = [...prev]
              if (updated.length === 0) updated.push('')
              updated[updated.length - 1] += delta
              return updated
            })
            const done = (frame as { done?: boolean }).done ?? false
            if (done) {
              stopped = true
              clearTimeout(watchdog)
              summary.success = true
              onComplete(summary)
              return
            }
          } else if (frame.kind === 'error') {
            stopped = true
            clearTimeout(watchdog)
            summary.error = (frame as { message?: string }).message ?? 'error frame'
            onComplete(summary)
            return
          } else if (frame.kind === 'session_event') {
            const evt = (frame as { event?: string }).event
            if (evt === 'exit') {
              stopped = true
              clearTimeout(watchdog)
              if (!summary.success) summary.error = 'backend exited before terminal chunk'
              onComplete(summary)
              return
            }
          }
        }
      } catch (err) {
        clearTimeout(watchdog)
        summary.error = `frame iterator threw: ${String(err)}`
        onComplete(summary)
      }
    })()

    return () => {
      clearTimeout(watchdog)
      stopped = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [submitted])

  return (
    <Box flexDirection="column">
      <Box>
        <Text color="cyan">{'> '}</Text>
        <Text>{typed}</Text>
        {!submitted && <Text color="gray">{' [▌]'}</Text>}
      </Box>
      {submitted && (
        <Box flexDirection="column" marginTop={1}>
          <Text color="magenta">[response · {framesSeen} frame(s)]</Text>
          {transcript.map((line, i) => (
            <Text key={i}>{line}</Text>
          ))}
        </Box>
      )}
    </Box>
  )
}

// ---------------------------------------------------------------------------
// CLI driver
// ---------------------------------------------------------------------------

async function main(): Promise<void> {
  const scenarioName = process.argv[2]
  if (!scenarioName || !SCENARIOS[scenarioName]) {
    const available = Object.keys(SCENARIOS).join(', ')
    process.stderr.write(`usage: bun run scripts/ink-rehearsal.tsx <scenario>\nscenarios: ${available}\n`)
    process.exit(2)
  }

  const scenario = SCENARIOS[scenarioName]
  process.stderr.write(`[ink-rehearsal] scenario=${scenario.name} prompt=${JSON.stringify(scenario.prompt)}\n`)

  // Spawn the real Python backend (cmd defaults to `uv run kosmos --ipc stdio`).
  const bridge = createBridge({})

  let summary: RehearsalSummary | null = null
  await new Promise<void>((resolve) => {
    const onComplete = (s: RehearsalSummary): void => {
      summary = s
      resolve()
    }

    const instance = render(
      <RehearsalHarness
        bridge={bridge}
        prompt={scenario.prompt}
        onComplete={onComplete}
        timeoutMs={scenario.timeoutMs}
      />,
    )

    // Push the prompt characters then Enter via the mocked stdin.
    // ink-testing-library's stdin.write triggers `useInput` for each chunk.
    setTimeout(() => {
      instance.stdin.write(scenario.prompt)
      // Small delay so React processes the keystroke batch before Enter.
      setTimeout(() => {
        instance.stdin.write('\r')
      }, 50)
    }, 100)
  })

  await bridge.close()

  if (!summary) {
    process.stderr.write('[ink-rehearsal] error: no summary captured\n')
    process.exit(1)
  }

  // Print structured result to stdout.
  process.stdout.write(JSON.stringify(summary, null, 2) + '\n')
  process.exit(summary.success ? 0 : 1)
}

void main().catch((err) => {
  process.stderr.write(`[ink-rehearsal] fatal: ${String(err)}\n`)
  process.exit(1)
})
