// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
});

export type AgentMcpServerInfo = any;
export const AgentMcpServerInfo: any = __stub;
export type ClaudeAIServerInfo = any;
export const ClaudeAIServerInfo: any = __stub;
export type HTTPServerInfo = any;
export const HTTPServerInfo: any = __stub;
export type MCPViewState = any;
export const MCPViewState: any = __stub;
export type SSEServerInfo = any;
export const SSEServerInfo: any = __stub;
export type ServerInfo = any;
export const ServerInfo: any = __stub;
export type StdioServerInfo = any;
export const StdioServerInfo: any = __stub;

export default __stub;
