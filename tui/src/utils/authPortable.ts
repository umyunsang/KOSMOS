// utils/secureStorage removed in P1+P2 (Spec 1633); KOSMOS uses .env-backed secrets, not OS keychain.
const getMacOsKeychainStorageServiceName = (): string => 'kosmos'

export async function maybeRemoveApiKeyFromMacOSKeychainThrows(): Promise<void> {
  // KOSMOS: no OS keychain — API keys managed via .env only.
  void getMacOsKeychainStorageServiceName()
}

export function normalizeApiKeyForConfig(apiKey: string): string {
  return apiKey.slice(-20)
}
