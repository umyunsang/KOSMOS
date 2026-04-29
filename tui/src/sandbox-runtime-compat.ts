// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #2293 FR-010 · sandbox-runtime compatibility shim.
//
// Purpose: every tui/src/ file that needs sandbox-runtime types or values
// imports from 'src/sandbox-runtime-compat.js' instead of directly from the
// sandbox-runtime package. This keeps the package literal isolated to a single
// shim file (FR-010 / SC-007 grep gate).
//
// Type-only imports (interfaces, enums) are forwarded with `export type`.
// Value exports (classes, schema objects) are forwarded directly.

export {
  SandboxManager,
  SandboxViolationStore,
  SandboxRuntimeConfigSchema,
} from '@anthropic-ai/sandbox-runtime'

export type {
  SandboxRuntimeConfig,
  NetworkConfig,
  FilesystemConfig,
  IgnoreViolationsConfig,
  SandboxAskCallback,
  FsReadRestrictionConfig,
  FsWriteRestrictionConfig,
  NetworkRestrictionConfig,
  NetworkHostPattern,
  SandboxDependencyCheck,
  SandboxViolationEvent,
} from '@anthropic-ai/sandbox-runtime'
