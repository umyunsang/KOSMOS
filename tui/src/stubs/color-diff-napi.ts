// [P0 stub · color-diff-napi]
// Anthropic's internal native module is not publicly available. KOSMOS disables
// syntax highlighting at the source level (CLAUDE_CODE_SYNTAX_HIGHLIGHT=0 is
// the documented gate); these exports keep consumer types honest.
/* eslint-disable @typescript-eslint/no-explicit-any */

export type SyntaxTheme = {
  name: string;
  colors: Record<string, string>;
};

export const ColorDiff: any = class {
  constructor(..._args: unknown[]) {}
  diff() { return []; }
};

export const ColorFile: any = class {
  constructor(..._args: unknown[]) {}
  read() { return ''; }
};

export const getSyntaxTheme = (..._args: unknown[]): SyntaxTheme => ({
  name: 'no-op',
  colors: {},
});

export default { ColorDiff, ColorFile, getSyntaxTheme };
