export const CALCULATOR_TOOL_NAME = 'Calculator'

export const DESCRIPTION = `
- Evaluates a restricted arithmetic expression and returns the numeric result
- Supports: digits, decimal point, parentheses, and operators + - * / % (modulo), and unary minus
- Does NOT support: variables, function calls, Math.*, or any identifier
- Uses BigInt for integer-precision arithmetic; Decimal-like precision (up to 28 significant digits) for fractional results
- Returns result as a string (JSON-safe serialization) with kind "int" | "float" | "fraction"
- Rejects any expression containing disallowed characters or syntax with an error

Usage notes:
  - expression must contain only: 0-9 . + - * / % ( ) and whitespace
  - precision controls the number of significant digits for non-integer results (default 28)
  - For integer results, the exact BigInt value is returned as a string
  - Division that produces a non-terminating decimal is returned as "float" with the given precision
  - Zero division raises an error
`
