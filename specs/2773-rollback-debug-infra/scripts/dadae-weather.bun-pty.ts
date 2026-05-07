// SPDX-License-Identifier: Apache-2.0

type Harness = {
  waitForPane(pattern: RegExp | string, deadlineSec?: number): Promise<void>
  snapshot(label: string): string
  sendText(text: string): void
  sendEnter(): void
  sendKey(name: 'C-o' | 'C-c'): void
}

export default async function run(h: Harness): Promise<void> {
  await h.waitForPane(/KOSAX|❯/, 60)
  h.snapshot('boot')

  h.sendText('부산 사하구 다대1동 날씨 알려줘')
  h.sendEnter()
  h.snapshot('input-submitted')

  await h.waitForPane(/resolve_location|kma_forecast_fetch|Invalid parameters|검색 오류|날씨|도구 결과/, 180)
  h.snapshot('post-tool-flow')

  h.sendKey('C-o')
  await h.waitForPane(/outbound_traces|request_url|response_status|status_code|Ctrl\+O|Error|검색 오류|날씨/, 30)
  h.snapshot('expanded-tool-detail')

  h.sendKey('C-c')
  h.sendKey('C-c')
}
