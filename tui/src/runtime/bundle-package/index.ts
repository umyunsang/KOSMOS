const KNOWN_FEATURES = [
  'ABLATION_BASELINE',
  'AGENT_MEMORY_SNAPSHOT',
  'AGENT_TRIGGERS',
  'AGENT_TRIGGERS_REMOTE',
  'ALLOW_TEST_VERSIONS',
  'ANTI_DISTILLATION_CC',
  'AUTO_THEME',
  'AWAY_SUMMARY',
  'BASH_CLASSIFIER',
  'BG_SESSIONS',
  'BREAK_CACHE_COMMAND',
  'BRIDGE_MODE',
  'BUDDY',
  'BUILDING_CLAUDE_APPS',
  'BUILTIN_EXPLORE_PLAN_AGENTS',
  'BYOC_ENVIRONMENT_RUNNER',
  'CACHED_MICROCOMPACT',
  'CCR_AUTO_CONNECT',
  'CCR_MIRROR',
  'CCR_REMOTE_SETUP',
  'CHICAGO_MCP',
  'COMMIT_ATTRIBUTION',
  'COMPACTION_REMINDERS',
  'CONNECTOR_TEXT',
  'CONTEXT_COLLAPSE',
  'COORDINATOR_MODE',
  'COWORKER_TYPE_TELEMETRY',
  'DAEMON',
  'DIRECT_CONNECT',
  'DOWNLOAD_USER_SETTINGS',
  'DUMP_SYSTEM_PROMPT',
  'ENHANCED_TELEMETRY_BETA',
  'EXPERIMENTAL_SKILL_SEARCH',
  'EXTRACT_MEMORIES',
  'FILE_PERSISTENCE',
  'FORK_SUBAGENT',
  'HARD_FAIL',
  'HISTORY_PICKER',
  'HISTORY_SNIP',
  'HOOK_PROMPTS',
  'IS_LIBC_GLIBC',
  'IS_LIBC_MUSL',
  'KAIROS',
  'KAIROS_BRIEF',
  'KAIROS_CHANNELS',
  'KAIROS_DREAM',
  'KAIROS_GITHUB_WEBHOOKS',
  'KAIROS_PUSH_NOTIFICATION',
  'LODESTONE',
  'MCP_RICH_OUTPUT',
  'MCP_SKILLS',
  'MEMORY_SHAPE_TELEMETRY',
  'MESSAGE_ACTIONS',
  'MONITOR_TOOL',
  'NATIVE_CLIENT_ATTESTATION',
  'NATIVE_CLIPBOARD_IMAGE',
  'NEW_INIT',
  'OVERFLOW_TEST_TOOL',
  'PERFETTO_TRACING',
  'POWERSHELL_AUTO_MODE',
  'PROACTIVE',
  'PROMPT_CACHE_BREAK_DETECTION',
  'QUICK_SEARCH',
  'REACTIVE_COMPACT',
  'REVIEW_ARTIFACT',
  'RUN_SKILL_GENERATOR',
  'SELF_HOSTED_RUNNER',
  'SHOT_STATS',
  'SKILL_IMPROVEMENT',
  'SKIP_DETECTION_WHEN_AUTOUPDATES_DISABLED',
  'SLOW_OPERATION_LOGGING',
  'SSH_REMOTE',
  'STREAMLINED_OUTPUT',
  'TEAMMEM',
  'TEMPLATES',
  'TERMINAL_PANEL',
  'TOKEN_BUDGET',
  'TORCH',
  'TRANSCRIPT_CLASSIFIER',
  'TREE_SITTER_BASH',
  'TREE_SITTER_BASH_SHADOW',
  'UDS_INBOX',
  'ULTRAPLAN',
  'ULTRATHINK',
  'UNATTENDED_RETRY',
  'UPLOAD_USER_SETTINGS',
  'VERIFICATION_AGENT',
  'VOICE_MODE',
  'WEB_BROWSER_TOOL',
  'WORKFLOW_SCRIPTS',
] as const

type KnownFeature = (typeof KNOWN_FEATURES)[number]
type FeatureName = KnownFeature | (string & {})

const KNOWN_FEATURE_SET = new Set<string>(KNOWN_FEATURES)
const TRUE_VALUES = new Set(['1', 'true', 'yes', 'on', 'enabled'])
const FALSE_VALUES = new Set(['0', 'false', 'no', 'off', 'disabled'])

function normalizeFeatureName(name: string): string {
  return name.trim().replace(/[^A-Za-z0-9]+/g, '_').toUpperCase()
}

function readBool(value: string | undefined): boolean | undefined {
  if (value === undefined) return undefined
  const normalized = value.trim().toLowerCase()
  if (TRUE_VALUES.has(normalized)) return true
  if (FALSE_VALUES.has(normalized)) return false
  return undefined
}

function parseFeatureList(value: string | undefined): Set<string> {
  const result = new Set<string>()
  if (!value) return result

  for (const raw of value.split(/[,\s]+/)) {
    const normalized = normalizeFeatureName(raw)
    if (normalized) result.add(normalized)
  }

  return result
}

const LIST_ENABLED_FEATURES = new Set([
  ...parseFeatureList(process.env.UMMAYA_FEATURES),
  ...parseFeatureList(process.env.CLAUDE_CODE_FEATURES),
])

export function feature(name: FeatureName): boolean {
  const normalized = normalizeFeatureName(name)

  const explicit =
    readBool(process.env[`UMMAYA_FEATURE_${normalized}`]) ??
    readBool(process.env[`CLAUDE_CODE_FEATURE_${normalized}`])

  if (explicit !== undefined) return explicit
  if (LIST_ENABLED_FEATURES.has(normalized)) return true

  return false
}

export function isKnownFeature(name: string): boolean {
  return KNOWN_FEATURE_SET.has(normalizeFeatureName(name))
}

export function listKnownFeatures(): readonly KnownFeature[] {
  return KNOWN_FEATURES
}
