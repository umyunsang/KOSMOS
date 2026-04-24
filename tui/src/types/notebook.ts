// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
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
