import type { Command } from '../../commands.js'

const stickers = {
  type: 'local',
  name: 'stickers',
  description: 'Order UMMAYA stickers',
  supportsNonInteractive: false,
  load: () => import('./stickers.js'),
} satisfies Command

export default stickers
