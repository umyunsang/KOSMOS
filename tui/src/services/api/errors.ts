// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]
// Aggregated from every consumer import across src/.
/* eslint-disable @typescript-eslint/no-explicit-any */

const __noop = (..._args: unknown[]): any => undefined as any;
const __stub: any = new Proxy(function () {} as any, {
  get: (_t, p) => (p === 'then' ? undefined : __stub),
  apply: () => __stub,
  construct: () => __stub,
});

export type API_ERROR_MESSAGE_PREFIX = any;
export const API_ERROR_MESSAGE_PREFIX: any = __stub;
export type API_TIMEOUT_ERROR_MESSAGE = any;
export const API_TIMEOUT_ERROR_MESSAGE: any = __stub;
export type CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE = any;
export const CREDIT_BALANCE_TOO_LOW_ERROR_MESSAGE: any = __stub;
export type CUSTOM_OFF_SWITCH_MESSAGE = any;
export const CUSTOM_OFF_SWITCH_MESSAGE: any = __stub;
export type INVALID_API_KEY_ERROR_MESSAGE = any;
export const INVALID_API_KEY_ERROR_MESSAGE: any = __stub;
export type INVALID_API_KEY_ERROR_MESSAGE_EXTERNAL = any;
export const INVALID_API_KEY_ERROR_MESSAGE_EXTERNAL: any = __stub;
export type ORG_DISABLED_ERROR_MESSAGE_ENV_KEY = any;
export const ORG_DISABLED_ERROR_MESSAGE_ENV_KEY: any = __stub;
export type ORG_DISABLED_ERROR_MESSAGE_ENV_KEY_WITH_OAUTH = any;
export const ORG_DISABLED_ERROR_MESSAGE_ENV_KEY_WITH_OAUTH: any = __stub;
export type PROMPT_TOO_LONG_ERROR_MESSAGE = any;
export const PROMPT_TOO_LONG_ERROR_MESSAGE: any = __stub;
export type REPEATED_529_ERROR_MESSAGE = any;
export const REPEATED_529_ERROR_MESSAGE: any = __stub;
export type TOKEN_REVOKED_ERROR_MESSAGE = any;
export const TOKEN_REVOKED_ERROR_MESSAGE: any = __stub;
export const categorizeRetryableAPIError: any = __noop;
export const classifyAPIError: any = __noop;
export const getAssistantMessageFromError: any = __noop;
export const getErrorMessageIfRefusal: any = __noop;
export const getImageTooLargeErrorMessage: any = __noop;
export const getPdfInvalidErrorMessage: any = __noop;
export const getPdfPasswordProtectedErrorMessage: any = __noop;
export const getPdfTooLargeErrorMessage: any = __noop;
export const getPromptTooLongTokenGap: any = __noop;
export const getRequestTooLargeErrorMessage: any = __noop;
export const isPromptTooLongMessage: any = __noop;
export const parsePromptTooLongTokenCounts: any = __noop;
export const startsWithApiErrorPrefix: any = __noop;

export default __stub;
