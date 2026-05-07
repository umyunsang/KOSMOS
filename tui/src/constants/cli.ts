export const KOSAX_CLI_COMMAND = 'kosax'
export const KOSAX_CONTINUE_COMMAND = `${KOSAX_CLI_COMMAND} --continue`
export const KOSAX_PRINT_RESUME_USAGE = `${KOSAX_CLI_COMMAND} -p --resume <session-id>`

export function formatKosaxResumeCommand(resumeArg: string): string {
  return `${KOSAX_CLI_COMMAND} --resume ${resumeArg}`
}
