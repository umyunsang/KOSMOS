// SPDX-License-Identifier: Apache-2.0
// UMMAYA-original — Epic #2637 cascade · stub-noop replacement.
// SWAP/anti-anthropic-1p(2637): ClaudeCodeDiagLogger (Anthropic 1P diagnostic
// telemetry sink) is permanently disabled in UMMAYA. instrumentation.ts byte-copy
// (R-5) references this export; UMMAYA uses stdlib logging (AGENTS.md hard rule).

import { DiagLogger } from '@opentelemetry/api'

export class ClaudeCodeDiagLogger implements DiagLogger {
  // Intentional no-op (Epic #2637 stub). Anthropic 1P diagnostic logger is swap-1 dependent.
  verbose(..._args: unknown[]): void {}
  debug(..._args: unknown[]): void {}
  info(..._args: unknown[]): void {}
  warn(..._args: unknown[]): void {}
  error(..._args: unknown[]): void {}
}
