export const DATE_PARSER_TOOL_NAME = 'DateParser'

export const DESCRIPTION = `
- Parses Korean-first natural language date/time expressions and returns an ISO-8601 timestamp
- Accepts Korean phrases like "오늘", "내일", "어제", "다음 주 월요일", "지난 주 금요일", "2026년 4월 24일", "어제 저녁 7시"
- Also accepts ISO-8601 date/time strings as pass-through (e.g., "2026-04-24", "2026-04-24T15:30:00")
- Default timezone: Asia/Seoul (KST, UTC+9). Override with the tz parameter.
- Returns interpreted_text that echoes the human-readable interpretation for LLM confirmation
- For ambiguous input, the LLM should show interpreted_text to the user before proceeding

Usage notes:
  - text must be a non-empty string
  - tz must be a valid IANA timezone identifier (e.g., "Asia/Seoul", "UTC", "America/New_York")
  - The returned iso8601 is always in full datetime format with timezone offset
  - If parsing fails, an error is returned — do not guess; ask the user to rephrase
`
