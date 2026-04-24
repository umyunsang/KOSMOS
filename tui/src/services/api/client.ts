// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.
//
// The Anthropic SDK client factory is replaced by `ipc/llmClient.ts` in
// KOSMOS. Legacy callers that still import `getAnthropicClient` receive a
// proxy that fail-closes on any method access, surfacing the misuse.

function stubThrow(name: string): never {
  throw new Error(
    `KOSMOS: services/api/client.${name} removed — use ipc/llmClient instead`,
  )
}

export async function getAnthropicClient(
  _opts?: unknown,
): Promise<Record<string, never>> {
  return new Proxy(
    {},
    {
      get(_t, prop) {
        stubThrow(String(prop))
      },
    },
  )
}
