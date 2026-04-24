// [P0 auto-stub · CC 2.1.88 sourcemap reconstruction gap]
// The CC sourcemap reconstruction does not include the original implementation
// of this module; consumers are satisfied with a minimal symbol shape so
// `bun run src/main.tsx` can reach the splash render. Real implementation is
// tracked for recovery in Epic #1633 (dead code elimination may remove callers
// entirely).

/* eslint-disable */
// noinspection JSUnusedGlobalSymbols

const __stub: any = new Proxy(function () {} as any, {
  get(_t, p) {
    if (p === Symbol.toPrimitive) return () => ""
    if (p === Symbol.iterator) return function* () {}
    if (p === Symbol.asyncIterator) return async function* () {}
    if (p === Symbol.toStringTag) return "Stub"
    if (p === Symbol.for("nodejs.util.inspect.custom")) return () => "<Stub>"
    if (p === "inspect") return () => "<Stub>"
    if (p === "then") return undefined
    if (p === "toString") return () => ""
    if (p === "valueOf") return () => undefined
    if (p === "toJSON") return () => null
    if (p === "length") return 0
    if (p === "name") return "Stub"
    if (p === "message") return ""
    if (p === "stack") return ""
    if (p === "constructor") return Object
    return __stub
  },
  apply() { return __stub },
  construct() { return __stub },
});


export default __stub;
export const SKILL: any = __stub;
