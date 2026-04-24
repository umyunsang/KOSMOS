// [P0 reconstructed · Pass 3 · Unicode symbol/glyph constants]
// CC uses these in spinner frames, indicators, and template literals.
// They MUST be real string primitives (not Proxy stubs) because:
//   template literal `${EFFORT_HIGH} ${level}` triggers Symbol.toPrimitive
//   on the value, and a Proxy that returns itself triggers "Symbol.toPrimitive
//   returned an object" runtime TypeError.

export const BLACK_CIRCLE = '●'
export const BLOCKQUOTE_BAR = '▎'
export const BULLET_OPERATOR = '∙'
export const CHANNEL_ARROW = '→'
export const DIAMOND_FILLED = '◆'
export const DIAMOND_OPEN = '◇'
export const DOWN_ARROW = '↓'
export const FLAG_ICON = '⚑'
export const LIGHTNING_BOLT = '⚡'
export const PAUSE_ICON = '⏸'
export const PLAY_ICON = '▶'
export const REFERENCE_MARK = '※'
export const REFRESH_ARROW = '↻'
export const TEARDROP_ASTERISK = '✻'
export const UP_ARROW = '↑'

// Effort levels — rising filled circles for increasing effort
export const EFFORT_LOW = '○'
export const EFFORT_MEDIUM = '◐'
export const EFFORT_HIGH = '◕'
export const EFFORT_MAX = '●'

// Bridge/remote-control status indicators
export const BRIDGE_READY_INDICATOR = '●'
export const BRIDGE_FAILED_INDICATOR = '×'
export const BRIDGE_SPINNER_FRAMES: readonly string[] = [
  '⠋',
  '⠙',
  '⠹',
  '⠸',
  '⠼',
  '⠴',
  '⠦',
  '⠧',
  '⠇',
  '⠏',
] as const

export default undefined as unknown
