// KOSMOS Epic #2293: queryHaiku removed (Spec 1633 + Spec 2293 closure).
// KOSMOS DateParser (MVP7) handles datetime parsing via the Python backend.
// This module is kept for the looksLikeISO8601 utility only; NL parsing
// always returns a non-destructive error directing the user to ISO 8601 input.

export type DateTimeParseResult =
  | { success: true; value: string }
  | { success: false; error: string }

/**
 * Parse natural language date/time input into ISO 8601 format.
 *
 * KOSMOS Epic #2293: Anthropic Haiku call removed. NL parsing deferred to
 * the Python backend DateParser tool (MVP7, Spec 022). Returns an error
 * directing the user to enter ISO 8601 format directly.
 */
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export async function parseNaturalLanguageDateTime(
  _input: string,
  _format: 'date' | 'date-time',
  _signal: AbortSignal,
): Promise<DateTimeParseResult> {
  return {
    success: false,
    error:
      'Unable to parse date/time. Please enter in ISO 8601 format manually.',
  }
}

/**
 * Check if a string looks like it might be an ISO 8601 date/time.
 * Used to decide whether to attempt NL parsing.
 */
export function looksLikeISO8601(input: string): boolean {
  // ISO 8601 date: YYYY-MM-DD
  // ISO 8601 datetime: YYYY-MM-DDTHH:MM:SS...
  return /^\d{4}-\d{2}-\d{2}(T|$)/.test(input.trim())
}
