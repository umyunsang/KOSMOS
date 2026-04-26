#!/usr/bin/env bun
// SPDX-License-Identifier: Apache-2.0
// KOSMOS Spec 1637 P6 / T033 — surface frame dumper.
//
// Renders each TUI surface through ink-testing-library's `render()`,
// captures the last frame as text, and writes the result into
// specs/1637-p6-docs-smoke/visual-evidence/<slug>.txt.
//
// This automates the visual-evidence half of the smoke checklist
// (FR-013 / FR-014 / SC-005). Surfaces requiring real keystrokes (4
// primitive flows + 4 slash commands + PDF-render path) cannot be
// driven by a deterministic dump — for those we capture the renderable
// component skeleton with mock props so the visual contract (layout,
// glyphs, copy) is recorded.

import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import React from 'react'
import { render } from 'ink-testing-library'
import { Box, Text } from 'ink'

import { ThemeProvider } from '../src/theme/provider'
import { WelcomeV2 } from '../src/components/LogoV2/WelcomeV2'
import { PIPAConsentStep } from '../src/components/onboarding/PIPAConsentStep'
import { MinistryScopeStep } from '../src/components/onboarding/MinistryScopeStep'
import { ErrorEnvelope } from '../src/components/messages/ErrorEnvelope'
import { PluginBrowser } from '../src/components/plugins/PluginBrowser'
import type { PluginEntry } from '../src/components/plugins/PluginBrowser'

const OUT_DIR = join(
  import.meta.dir,
  '..',
  '..',
  'specs',
  '1637-p6-docs-smoke',
  'visual-evidence',
)

mkdirSync(OUT_DIR, { recursive: true })

interface Surface {
  readonly slug: string
  readonly description: string
  readonly element: React.ReactElement
}

function withTheme(child: React.ReactElement): React.ReactElement {
  return <ThemeProvider>{child}</ThemeProvider>
}

const SURFACES: readonly Surface[] = [
  {
    slug: 'onboarding-1-splash',
    description: 'Onboarding step 1 — splash (WelcomeV2 logo + brand glyph)',
    element: withTheme(<WelcomeV2 />),
  },
  {
    slug: 'onboarding-3-pipa',
    description: 'Onboarding step 3 — PIPA consent prompt',
    element: withTheme(
      <PIPAConsentStep
        sessionId="smoke-session"
        consentVersion="v1"
        ministries={[
          { code: 'koroad', name: '도로교통공단' },
          { code: 'kma', name: '기상청' },
          { code: 'hira', name: '건강보험심사평가원' },
        ]}
        aalGate="AAL2"
        writeRecord={() => {}}
        onAdvance={() => {}}
        onExit={() => {}}
      />,
    ),
  },
  {
    slug: 'onboarding-4-ministry',
    description: 'Onboarding step 4 — ministry-scope acknowledgement',
    element: withTheme(
      <MinistryScopeStep
        sessionId="smoke-session"
        scopeVersion="v1"
        ministries={[
          { code: 'koroad', name: '도로교통공단' },
          { code: 'kma', name: '기상청' },
          { code: 'hira', name: '건강보험심사평가원' },
          { code: 'nfa119', name: '소방청 119' },
          { code: 'mohw', name: '보건복지부' },
        ]}
        writeRecord={() => {}}
        onAdvance={() => {}}
        onExit={() => {}}
      />,
    ),
  },
  {
    slug: 'plugin-browser',
    description: 'Slash command — `/plugins` browser',
    element: withTheme(
      <PluginBrowser
        plugins={[
          {
            id: 'seoul-subway',
            name: 'Seoul Subway Arrivals',
            version: '1.0.0',
            description_ko: '서울 지하철 실시간 도착 정보',
            description_en: 'Seoul subway real-time arrivals',
            isActive: true,
          } satisfies PluginEntry,
          {
            id: 'post-office',
            name: 'Korea Post Tracking',
            version: '1.2.0',
            description_ko: '우정사업본부 택배 추적',
            description_en: 'Korea Post parcel tracking',
            isActive: false,
          } satisfies PluginEntry,
          {
            id: 'nts-homtax',
            name: 'NTS Hometax (Mock)',
            version: '0.1.0',
            description_ko: '홈택스 마이데이터 모의 어댑터',
            description_en: 'Hometax MyData mock adapter',
            isActive: false,
          } satisfies PluginEntry,
        ]}
        onToggle={() => {}}
        onShowDetail={() => {}}
        onRemove={() => {}}
        onOpenMarketplace={() => {}}
        onClose={() => {}}
      />,
    ),
  },
  {
    slug: 'error-llm-4xx',
    description: 'Error envelope — LLM 4xx (purple, brain glyph)',
    element: withTheme(
      <ErrorEnvelope
        error={{
          type: 'llm',
          title_ko: 'LLM 응답 오류',
          title_en: 'LLM response error',
          detail_ko: 'EXAONE 모델이 4xx 오류를 반환했습니다. 잠시 후 다시 시도해 주세요.',
          detail_en: 'EXAONE returned a 4xx error. Please retry in a moment.',
          retry_suggested: true,
          occurred_at: '2026-04-26T00:00:00.000Z',
        }}
      />,
    ),
  },
  {
    slug: 'error-tool-fail-closed',
    description: 'Error envelope — tool fail-closed (orange, wrench glyph)',
    element: withTheme(
      <ErrorEnvelope
        error={{
          type: 'tool',
          title_ko: '도구 호출 차단',
          title_en: 'Tool call refused',
          detail_ko:
            'Layer-3 권한이 필요한 nmc_emergency_search 호출이 fail-closed로 거부되었습니다. /consent 로 권한을 부여하세요.',
          detail_en:
            'nmc_emergency_search requires Layer-3 authorization and was refused fail-closed. Grant via /consent.',
          retry_suggested: false,
          occurred_at: '2026-04-26T00:00:00.000Z',
        }}
      />,
    ),
  },
  {
    slug: 'error-network-timeout',
    description: 'Error envelope — network timeout (red, signal-broken glyph)',
    element: withTheme(
      <ErrorEnvelope
        error={{
          type: 'network',
          title_ko: '네트워크 시간 초과',
          title_en: 'Network timeout',
          detail_ko: 'data.go.kr 서버 응답이 30초 이내에 도착하지 않았습니다. R 키로 재시도하세요.',
          detail_en: "data.go.kr did not respond within 30s. Press 'R' to retry.",
          retry_suggested: true,
          occurred_at: '2026-04-26T00:00:00.000Z',
        }}
      />,
    ),
  },
]

interface DumpOutcome {
  readonly slug: string
  readonly status: 'ok' | 'fail'
  readonly bytes: number
  readonly error?: string
}

function dump(surface: Surface): DumpOutcome {
  try {
    const { lastFrame, unmount } = render(surface.element)
    const frame = lastFrame() ?? '(empty frame)'
    const header = `# Visual evidence — ${surface.slug}\n# ${surface.description}\n# Captured ${new Date().toISOString()} via ink-testing-library render()\n\n`
    const txtPath = join(OUT_DIR, `${surface.slug}.txt`)
    mkdirSync(dirname(txtPath), { recursive: true })
    writeFileSync(txtPath, header + frame + '\n', 'utf-8')
    unmount()
    return { slug: surface.slug, status: 'ok', bytes: frame.length }
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    const txtPath = join(OUT_DIR, `${surface.slug}.txt`)
    writeFileSync(
      txtPath,
      `# Visual evidence — ${surface.slug}\n# ${surface.description}\n# RENDER FAILED: ${error}\n`,
      'utf-8',
    )
    return { slug: surface.slug, status: 'fail', bytes: 0, error }
  }
}

const outcomes = SURFACES.map(dump)
const ok = outcomes.filter((o) => o.status === 'ok').length
const fail = outcomes.filter((o) => o.status === 'fail').length

console.log(`[dump-tui-frames] ${ok} ok, ${fail} fail (out: ${OUT_DIR})`)
for (const o of outcomes) {
  console.log(
    `  ${o.status === 'ok' ? '✓' : '✗'} ${o.slug.padEnd(28)} ${o.status === 'ok' ? `${o.bytes}B` : o.error}`,
  )
}

process.exit(fail === 0 ? 0 : 1)
