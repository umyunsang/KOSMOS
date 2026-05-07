// utils/secureStorage removed in P1+P2 (Spec 1633); KOSAX uses process-scoped FriendliAI secrets, not OS keychain.
const getMacOsKeychainStorageServiceName = (): string => 'kosax'

export async function maybeRemoveApiKeyFromMacOSKeychainThrows(): Promise<void> {
  // KOSAX: no OS keychain — API keys are session/process-scoped.
  void getMacOsKeychainStorageServiceName()
}

export function normalizeApiKeyForConfig(apiKey: string): string {
  return apiKey.slice(-20)
}
