// P0 Baseline Runnable stub — resolves `bun:bundle` to a no-op feature flag gate.
// Every flag returns `false`, so gated code paths never execute at runtime.
// Dead-code elimination of those paths is tracked in Epic #1633.
export function feature(_flag: string): boolean {
  return false;
}
