// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1633 stub restoration.

export async function clearAuthRelatedCaches(): Promise<void> {
  /* no-op — KOSMOS has no auth cache */
}

export async function performLogout(): Promise<void> {
  /* no-op — KOSMOS auth is env-var based; logout is meaningless */
}
