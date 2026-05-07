import type { Command } from '../../commands.js'
// UMMAYA: policyLimits deleted by Spec 1633 P1. isPolicyAllowed → false (remote sessions disabled in UMMAYA).
const isPolicyAllowed = (_policy: string): boolean => false
import { isClaudeAISubscriber } from '../../utils/auth.js'

export default {
  type: 'local-jsx',
  name: 'remote-env',
  description: 'Configure the default remote environment for teleport sessions',
  isEnabled: () =>
    isClaudeAISubscriber() && isPolicyAllowed('allow_remote_sessions'),
  get isHidden() {
    return !isClaudeAISubscriber() || !isPolicyAllowed('allow_remote_sessions')
  },
  load: () => import('./remote-env.js'),
} satisfies Command
