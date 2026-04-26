// SPDX-License-Identifier: Apache-2.0
// KOSMOS-1633 — ink-reconciler devtools no-op shim.
//
// Ink's reconciler attempts a dynamic `import('./devtools.js')` only when
// `NODE_ENV === 'development'` (see `tui/src/ink/reconciler.ts:33`). The
// original module wires React DevTools through `react-devtools-core` for
// CC's developer-internal flow. KOSMOS exposes no React DevTools surface,
// so this module is intentionally empty: importing it succeeds but
// performs no side effect.
export {}
