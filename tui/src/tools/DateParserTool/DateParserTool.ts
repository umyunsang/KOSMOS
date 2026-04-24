import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { DATE_PARSER_TOOL_NAME, DESCRIPTION } from './prompt.js'
import { parseKoreanDate, toIso8601WithTz } from './korean-date-parser.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    text: z
      .string()
      .describe(
        'Korean natural language date/time phrase ("오늘", "내일", "다음 주 월요일", "2026년 4월 24일", "어제 저녁 7시") ' +
          'or an ISO-8601 date/time string. Must be non-empty.',
      ),
    tz: z
      .string()
      .default('Asia/Seoul')
      .optional()
      .describe(
        'IANA timezone identifier for resolving relative phrases and formatting the output. ' +
          'Default: "Asia/Seoul" (KST, UTC+9).',
      ),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

const outputSchema = lazySchema(() =>
  z.object({
    iso8601: z
      .string()
      .describe(
        'Resolved date/time in ISO-8601 format with timezone offset, e.g. "2026-04-24T00:00:00+09:00".',
      ),
    interpreted_text: z
      .string()
      .describe(
        'Human-readable interpretation of what was parsed, echoed for LLM confirmation before acting on ambiguous input.',
      ),
  }),
)
type OutputSchema = ReturnType<typeof outputSchema>

export type Output = z.infer<OutputSchema>

export const DateParserTool = buildTool({
  name: DATE_PARSER_TOOL_NAME,
  searchHint: '날짜 시간 파싱 — parse Korean date/time phrases and ISO-8601 strings',
  maxResultSizeChars: 500,
  userFacingName() {
    return 'DateParser'
  },
  get inputSchema(): InputSchema {
    return inputSchema()
  },
  get outputSchema(): OutputSchema {
    return outputSchema()
  },
  isConcurrencySafe() {
    return true
  },
  isReadOnly() {
    return true
  },
  toAutoClassifierInput(input) {
    return input.text
  },
  async description() {
    return DESCRIPTION
  },
  async prompt() {
    return DESCRIPTION
  },
  mapToolResultToToolResultBlockParam(output, toolUseID) {
    return {
      tool_use_id: toolUseID,
      type: 'tool_result',
      content: `Parsed: ${output.iso8601} (${output.interpreted_text})`,
    }
  },
  async call({ text, tz }) {
    const effectiveTz = tz ?? 'Asia/Seoul'
    const parseResult = parseKoreanDate(text, effectiveTz)
    const iso8601 = toIso8601WithTz(parseResult.date, effectiveTz)
    return {
      data: {
        iso8601,
        interpreted_text: parseResult.interpretedText,
      },
    }
  },
} satisfies ToolDef<InputSchema, Output>)
