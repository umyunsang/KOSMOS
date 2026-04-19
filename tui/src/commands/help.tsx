// KOSMOS-original help renderer for slash commands.
// Renders the known-commands list via Ink <Box> + <Text>.
// Unknown command path passes an errorBanner prop for the error notice.

import { Box, Text } from 'ink'
import { useTheme } from '../theme/provider'
import { useI18n } from '../i18n'
import type { CommandDefinition } from './types.ts'

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface HelpViewProps {
  /** Sorted list of known commands to render */
  commands: CommandDefinition[]
  /**
   * Optional error message shown at the top (e.g. "Unknown command: /foo").
   * Rendered with error colour from the theme token set.
   */
  errorBanner?: string
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

/**
 * HelpView — renders the KOSMOS slash-command help listing.
 *
 * Reads labels from the i18n bundle.  New command keys
 * (helpTitle, helpUsage) are defined in keys.ts + en.ts + ko.ts.
 *
 * T050 NOTE: This component is returned via CommandResult.renderHelp=true.
 * The conversation layer (Team A, tui.tsx) is responsible for detecting
 * renderHelp and mounting <HelpView /> in the message stream.
 */
export function HelpView({ commands, errorBanner }: HelpViewProps) {
  const theme = useTheme()
  const i18n = useI18n()

  return (
    <Box flexDirection="column" paddingY={1}>
      {/* Error banner (unknown command) */}
      {errorBanner !== undefined && errorBanner !== '' && (
        <Box marginBottom={1}>
          <Text color={theme.error}>{'! '}</Text>
          <Text color={theme.error}>{errorBanner}</Text>
        </Box>
      )}

      {/* Title */}
      <Box marginBottom={1}>
        <Text bold color={theme.claude}>
          {i18n.helpTitle}
        </Text>
      </Box>

      {/* Usage line */}
      <Box marginBottom={1}>
        <Text color={theme.subtle}>{i18n.helpUsage}</Text>
      </Box>

      {/* Command list */}
      {commands.map((cmd) => (
        <Box key={cmd.name} flexDirection="row" gap={2}>
          {/* Command name + optional argument hint */}
          <Box minWidth={20}>
            <Text color={theme.success}>{'/'}{cmd.name}</Text>
            {cmd.argumentHint !== undefined && (
              <Text color={theme.subtle}>{' '}{cmd.argumentHint}</Text>
            )}
          </Box>

          {/* Description */}
          <Text color={theme.text}>{cmd.description}</Text>

          {/* Aliases */}
          {cmd.aliases !== undefined && cmd.aliases.length > 0 && (
            <Text color={theme.subtle}>
              {'(alias: /'}{cmd.aliases.join(', /')}{')'}
            </Text>
          )}
        </Box>
      ))}
    </Box>
  )
}
