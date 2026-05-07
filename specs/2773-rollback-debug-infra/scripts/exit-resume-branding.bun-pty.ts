// SPDX-License-Identifier: Apache-2.0

import type { Harness } from '../../../scripts/bun-pty-capture'

async function sleep(ms: number): Promise<void> {
  await new Promise(resolve => setTimeout(resolve, ms))
}

export default async function run(h: Harness): Promise<void> {
  await h.waitForPane(/KOSAX|❯/, 60)
  if (/alpha\+1978/i.test(h.plain())) {
    throw new Error('Boot branding still contains alpha+1978')
  }
  h.snapshot('boot')

  h.sendText('resume branding smoke')
  h.sendEnter()
  await sleep(1200)
  h.snapshot('input-submitted')

  const exitMark = h.mark()
  h.sendCtrlC()
  await sleep(600)
  h.sendCtrlC()
  await sleep(600)
  h.sendCtrlC()

  await h.waitForPaneSince(
    exitMark,
    /Resume this session with:[\s\S]*kosax --resume [0-9a-f-]{36}/i,
    20,
  )

  const exitText = h.plainSince(exitMark)
  if (/claude --resume/i.test(exitText)) {
    throw new Error('Exit resume hint still contains claude --resume')
  }
  h.snapshot('exit-resume-hint')
}
