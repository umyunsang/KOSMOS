import type { Command } from '../../commands.js'
import { getFeatureValue_CACHED_MAY_BE_STALE } from '../../services/analytics/growthbook.js'
// policyLimits removed in P1+P2 (Spec 1633); KOSMOS opens features by default via Spec 033 permission gauntlet.
const isPolicyAllowed = (_policy: string): boolean => true

const web = {
  type: 'local-jsx',
  name: 'web-setup',
  description:
    'Setup Claude Code on the web (requires connecting your GitHub account)',
  availability: ['claude-ai'],
  isEnabled: () =>
    getFeatureValue_CACHED_MAY_BE_STALE('tengu_cobalt_lantern', false) &&
    isPolicyAllowed('allow_remote_sessions'),
  get isHidden() {
    return !isPolicyAllowed('allow_remote_sessions')
  },
  load: () => import('./remote-setup.js'),
} satisfies Command

export default web
