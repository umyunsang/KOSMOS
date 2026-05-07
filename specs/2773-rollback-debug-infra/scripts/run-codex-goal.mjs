#!/usr/bin/env node

import { spawn } from 'node:child_process'
import fs from 'node:fs'
import path from 'node:path'
import readline from 'node:readline'

const repoRoot = path.resolve('/Users/um-yunsang/UMMAYA')
const promptPath = process.argv[2] ?? path.join(repoRoot, 'specs/2773-rollback-debug-infra/codex-goal-final-packaging.md')
const logPath = process.argv[3] ?? path.join(
  repoRoot,
  'specs/2773-rollback-debug-infra/captures/codex-goal-final-packaging.jsonl',
)
const ummayaReferenceSkillPath = path.join(repoRoot, '.agents/skills/ummaya-reference-first/SKILL.md')

const fullPrompt = fs.readFileSync(promptPath, 'utf8')
const objective = [
  'Make UMMAYA packaging-ready as the client-side reference implementation for Korea national AX infrastructure.',
  'Preserve the thesis: Claude Code original harness plus two swaps only: FriendliAI/K-EXAONE and Korean public-service tools.',
  'Verify and repair the whole harness abstraction across query engine, tool system, permission pipeline, TUI, IPC, reasoning, observability, docs, and packaging gates.',
  'Treat non-exception abnormal UI/UX, interaction, backend, reasoning, tool-call, visualization, painting, and debug-inspection flows as failures that must be debugged.',
  'Use the UMMAYA LLMOps rendering-flow infrastructure: join LLM chunks, IPC frames, tool dispatch, permission events, render commits, PTY/frame artifacts, expanded logs, and scenario audits by trace/correlation ids.',
  'Use the ummaya-reference-first skill for research material discovery before implementation decisions.',
  'Use reference-first research, CC restored source parity, official adapter/API evidence, direct curl for live public APIs, and real-use TUI/PTY verification.',
  'No hallucinated behavior, hardcoded routing, static fallbacks, symptom-only fixes, or unverified success claims.',
  `Full goal prompt and acceptance criteria are in ${promptPath}.`,
].join(' ')
fs.mkdirSync(path.dirname(logPath), { recursive: true })
const log = fs.createWriteStream(logPath, { flags: 'a' })

const proc = spawn('codex', ['app-server', '--enable', 'goals', '--listen', 'stdio://'], {
  cwd: repoRoot,
  env: process.env,
  stdio: ['pipe', 'pipe', 'inherit'],
})

let nextId = 1
let threadId = null
let turnCompleted = false

function emit(message) {
  log.write(`${JSON.stringify({ direction: 'client', message })}\n`)
  proc.stdin.write(`${JSON.stringify(message)}\n`)
}

function request(method, params = {}) {
  const id = nextId++
  emit({ method, id, params })
  return id
}

function notify(method, params = {}) {
  emit({ method, params })
}

function fail(message) {
  console.error(message)
  try {
    proc.kill('SIGTERM')
  } finally {
    process.exitCode = 1
  }
}

const initializeId = request('initialize', {
  clientInfo: {
    name: 'ummaya_goal_runner',
    title: 'UMMAYA Goal Runner',
    version: '0.1.0',
  },
  capabilities: {
    experimentalApi: true,
  },
})
notify('initialized', {})

const rl = readline.createInterface({ input: proc.stdout })

rl.on('line', (line) => {
  if (!line.trim()) return

  let msg
  try {
    msg = JSON.parse(line)
  } catch (error) {
    log.write(`${JSON.stringify({ direction: 'server-parse-error', line, error: String(error) })}\n`)
    return
  }

  log.write(`${JSON.stringify({ direction: 'server', message: msg })}\n`)

  if (msg.id === initializeId) {
    request('thread/start', {
      model: 'gpt-5.5',
      cwd: repoRoot,
      approvalPolicy: 'never',
      sandbox: 'danger-full-access',
      personality: 'pragmatic',
      serviceName: 'ummaya_goal_runner',
      persistExtendedHistory: true,
    })
    return
  }

  if (msg.result?.thread?.id && !threadId) {
    threadId = msg.result.thread.id
    request('thread/name/set', {
      threadId,
      name: 'UMMAYA final packaging readiness loop',
    })
    request('thread/goal/set', {
      threadId,
      objective,
      status: 'active',
      tokenBudget: null,
    })
    request('thread/goal/get', { threadId })
    request('turn/start', {
      threadId,
      model: 'gpt-5.5',
      effort: 'xhigh',
      cwd: repoRoot,
      approvalPolicy: 'never',
      sandboxPolicy: { type: 'dangerFullAccess' },
      personality: 'pragmatic',
      input: [
        {
          type: 'text',
          text: `$ummaya-reference-first\n\n${fullPrompt}\n\nExecute this active goal now. Continue the RALF loop until the acceptance criteria pass or a blocker is proven with exact evidence.`,
        },
        {
          type: 'skill',
          name: 'ummaya-reference-first',
          path: ummayaReferenceSkillPath,
        },
      ],
    })
    return
  }

  if (msg.method === 'turn/completed') {
    turnCompleted = true
    const status = msg.params?.turn?.status ?? 'unknown'
    console.log(`Codex goal turn completed with status=${status}`)
    proc.kill('SIGTERM')
  }

  if (msg.error) {
    fail(`Codex app-server error: ${JSON.stringify(msg.error)}`)
  }
})

proc.on('exit', (code, signal) => {
  log.write(`${JSON.stringify({ direction: 'process', code, signal, turnCompleted })}\n`)
  log.end()
  if (!turnCompleted && code !== 0) {
    process.exitCode = code ?? 1
  }
})

proc.on('error', (error) => {
  fail(`Failed to start codex app-server: ${String(error)}`)
})
