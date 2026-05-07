// utils/secureStorage removed in P1+P2 (Spec 1633); UMMAYA uses process-scoped FriendliAI secrets, not OS keychain.
const getMacOsKeychainStorageServiceName = (): string => 'ummaya'

export async function maybeRemoveApiKeyFromMacOSKeychainThrows(): Promise<void> {
  // UMMAYA: no OS keychain — API keys are session/process-scoped.
  void getMacOsKeychainStorageServiceName()
}

export function normalizeApiKeyForConfig(apiKey: string): string {
  return apiKey.slice(-20)
}
