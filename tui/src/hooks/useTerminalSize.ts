import { useContext } from 'react'
import {
  type TerminalSize,
  TerminalSizeContext,
} from 'src/ink/components/TerminalSizeContext.js'

/** Fallback dimensions used in test environments where Ink App context is absent. */
const FALLBACK_SIZE: TerminalSize = { columns: 80, rows: 24 }

export function useTerminalSize(): TerminalSize {
  const size = useContext(TerminalSizeContext)

  // Return a sensible fallback rather than throwing when the Ink App context
  // is not present (e.g., ink-testing-library mounts components without the
  // full Ink App wrapper that normally provides TerminalSizeContext).
  if (!size) {
    return FALLBACK_SIZE
  }

  return size
}
