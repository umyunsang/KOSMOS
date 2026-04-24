// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export type EnvironmentKind = 'cloud' | 'local' | 'unknown'

export interface EnvironmentResource {
  readonly kind: EnvironmentKind
  readonly id: string
}

export function createDefaultCloudEnvironment(): EnvironmentResource {
  return { kind: 'cloud', id: 'kosmos-placeholder' }
}

export async function fetchEnvironments(): Promise<readonly EnvironmentResource[]> {
  return []
}
