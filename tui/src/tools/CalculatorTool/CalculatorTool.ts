import { z } from 'zod/v4'
import { buildTool, type ToolDef } from '../../Tool.js'
import { lazySchema } from '../../utils/lazySchema.js'
import { CALCULATOR_TOOL_NAME, DESCRIPTION } from './prompt.js'
import { evaluate } from './parser.js'

const inputSchema = lazySchema(() =>
  z.strictObject({
    expression: z
      .string()
      .describe(
        'Arithmetic expression using only digits, decimal point, operators (+ - * / %), and parentheses. ' +
          'No variables, function calls, or identifiers are allowed.',
      ),
    precision: z
      .number()
      .int()
      .min(1)
      .max(21)
      .default(28)
      .optional()
      .describe(
        'Number of significant digits for non-integer results. Default 28 (capped to JS max of 21).',
      ),
  }),
)
type InputSchema = ReturnType<typeof inputSchema>

const outputSchema = lazySchema(() =>
  z.object({
    result: z
      .string()
      .describe('Computed value serialized as a string for JSON safety (may be a large integer or high-precision decimal).'),
    kind: z
      .enum(['int', 'float', 'fraction'])
      .describe(
        '"int" when the result is an exact integer, ' +
          '"float" when the decimal terminates (denominator is a product of 2s and 5s), ' +
          '"fraction" when the decimal repeats (irrational denominator factor).',
      ),
  }),
)
type OutputSchema = ReturnType<typeof outputSchema>

export type Output = z.infer<OutputSchema>

export const CalculatorTool = buildTool({
  name: CALCULATOR_TOOL_NAME,
  searchHint: 'evaluate arithmetic expression — add, subtract, multiply, divide, modulo',
  maxResultSizeChars: 1_000,
  userFacingName() {
    return 'Calculate'
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
    return input.expression
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
      content: `Result: ${output.result} (${output.kind})`,
    }
  },
  renderToolUseMessage() {
    return null
  },
  renderToolResultMessage() {
    return null
  },
  async call({ expression, precision }) {
    const effectivePrecision = Math.min(precision ?? 28, 21)
    const evalResult = evaluate(expression, effectivePrecision)
    return {
      data: {
        result: evalResult.result,
        kind: evalResult.kind,
      },
    }
  },
} satisfies ToolDef<InputSchema, Output>)
