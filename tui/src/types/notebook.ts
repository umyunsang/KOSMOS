// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
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

export type NotebookCell = any;
export const NotebookCell: any = __stub;
export type NotebookCellOutput = any;
export const NotebookCellOutput: any = __stub;
export type NotebookCellSource = any;
export const NotebookCellSource: any = __stub;
export type NotebookCellSourceOutput = any;
export const NotebookCellSourceOutput: any = __stub;
export type NotebookCellType = any;
export const NotebookCellType: any = __stub;
export type NotebookContent = any;
export const NotebookContent: any = __stub;
export type NotebookOutputImage = any;
export const NotebookOutputImage: any = __stub;

export default __stub;
