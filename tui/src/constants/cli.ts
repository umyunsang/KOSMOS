export const KOSMOS_CLI_COMMAND = 'kosmos'
export const KOSMOS_CONTINUE_COMMAND = `${KOSMOS_CLI_COMMAND} --continue`
export const KOSMOS_PRINT_RESUME_USAGE = `${KOSMOS_CLI_COMMAND} -p --resume <session-id>`

export function formatKosmosResumeCommand(resumeArg: string): string {
  return `${KOSMOS_CLI_COMMAND} --resume ${resumeArg}`
}
