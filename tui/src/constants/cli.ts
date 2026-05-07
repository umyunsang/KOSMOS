export const UMMAYA_CLI_COMMAND = 'ummaya'
export const UMMAYA_CONTINUE_COMMAND = `${UMMAYA_CLI_COMMAND} --continue`
export const UMMAYA_PRINT_RESUME_USAGE = `${UMMAYA_CLI_COMMAND} -p --resume <session-id>`

export function formatUmmayaResumeCommand(resumeArg: string): string {
  return `${UMMAYA_CLI_COMMAND} --resume ${resumeArg}`
}
