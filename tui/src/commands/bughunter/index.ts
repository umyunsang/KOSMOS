// [P0 auto-stub · CC 2.1.88 sourcemap reconstruction gap]
// The CC sourcemap reconstruction does not include the original implementation
// of this module; consumers are satisfied with a minimal symbol shape so
// `bun run src/main.tsx` can reach the splash render. Real implementation is
// tracked for recovery in Epic #1633 (dead code elimination may remove callers
// entirely).

/* eslint-disable */
// noinspection JSUnusedGlobalSymbols

const __stub: any = new Proxy(function () {} as any, {
  get: (t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
});

export default __stub;
