// SPDX-License-Identifier: Apache-2.0
// KOSMOS-original — Epic #1634 P4 · TranslateTool prompt strings.

export const TRANSLATE_TOOL_NAME = 'Translate'

/** One-line description shown to the LLM (bilingual per Constitution § III). */
export const DESCRIPTION =
  '번역(한국어↔영어↔일본어) / Translate text between Korean, English, and Japanese'

/** Extended prompt included in the system-prompt tool-use section. */
export const TRANSLATE_TOOL_PROMPT = `Translate text between Korean (ko), English (en), and Japanese (ja).

Input:
  - \`text\` — the source text to translate
  - \`source_lang\` — language code of the source: "ko" | "en" | "ja"
  - \`target_lang\` — language code of the target: "ko" | "en" | "ja"

Output:
  - \`text\` — the translated text only, no preamble

Use this tool whenever the user's request requires a language conversion. Do not add explanations or commentary in the output — return only the translation.`

/**
 * Build the internal prompt sent to EXAONE via the LLMClient bridge.
 * The model must return ONLY the translated text (no preamble, no quotes).
 */
export function buildTranslatePrompt(
  text: string,
  sourceLang: 'ko' | 'en' | 'ja',
  targetLang: 'ko' | 'en' | 'ja',
): string {
  return `Translate the following ${sourceLang} text to ${targetLang}. Return ONLY the translation, no preamble.

${text}`
}
