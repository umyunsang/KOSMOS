// SPDX-License-Identifier: Apache-2.0
// Shim for React Compiler memoization runtime.
//
// The `c(size)` sentinel returns an array used by compiler-emitted code as a
// per-component memoization cache. The real runtime pre-fills each slot with
// `Symbol.for("react.memo_cache_sentinel")` so the generated code's "first
// render" branch (`if ($[N] === sentinel) { ... compute ... }`) executes.
// If we fill with `undefined`, the comparison is always false and the code
// takes the "use cache" branch, returning undefined for every memoized value
// (which crashes downstream on `store.setState` etc.).

const SENTINEL = Symbol.for('react.memo_cache_sentinel')

export function c(size: number): unknown[] {
  return new Array(size).fill(SENTINEL)
}
