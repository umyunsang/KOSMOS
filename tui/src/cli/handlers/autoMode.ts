/**
 * KOSMOS: Auto mode CLI handlers stubbed out.
 * utils/permissions/yoloClassifier deleted (Anthropic growthbook TRANSCRIPT_CLASSIFIER).
 * KOSMOS uses K-EXAONE on FriendliAI — the Anthropic-only auto-mode classifier
 * feature does not apply.
 */

export function autoModeDefaultsHandler(): void {
  process.stdout.write(
    'Auto mode classifier is not available in KOSMOS (K-EXAONE / FriendliAI build).\n',
  )
}

export function autoModeConfigHandler(): void {
  process.stdout.write(
    'Auto mode classifier is not available in KOSMOS (K-EXAONE / FriendliAI build).\n',
  )
}

export async function autoModeCritiqueHandler(_options: {
  model?: string
}): Promise<void> {
  process.stdout.write(
    'Auto mode classifier is not available in KOSMOS (K-EXAONE / FriendliAI build).\n',
  )
}
