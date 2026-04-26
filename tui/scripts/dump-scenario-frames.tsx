#!/usr/bin/env bun
// SPDX-License-Identifier: Apache-2.0
// KOSMOS Spec 1637 P6 / KSC 2026 presentation — citizen-scenario frame dump.
//
// Captures the end-to-end visual flow of three high-impact citizen
// scenarios (응급 / 위기 / 재난) by rendering each step of the conversation
// through ink-testing-library and writing the lastFrame() to
// docs/presentation/v0.1-alpha/scenarios/<scenario>/<step>.txt.
//
// Each scenario is broken into ordered steps showing how a single citizen
// question fans out across multiple ministries via the KOSMOS query engine
// and tool system, then collapses back into one consolidated answer.

import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import React from 'react'
import { render } from 'ink-testing-library'
import { Box, Text } from 'ink'

import { ThemeProvider } from '../src/theme/provider'
import { CollectionList } from '../src/components/primitive/CollectionList'
import { DetailView } from '../src/components/primitive/DetailView'
import { SubmitReceipt } from '../src/components/primitive/SubmitReceipt'
import { AuthContextCard } from '../src/components/primitive/AuthContextCard'

const OUT_DIR = join(
  import.meta.dir,
  '..',
  '..',
  'docs',
  'presentation',
  'v0.1-alpha',
  'scenarios',
)

mkdirSync(OUT_DIR, { recursive: true })

interface ScenarioStep {
  readonly slug: string
  readonly description: string
  readonly element: React.ReactElement
}

function withTheme(child: React.ReactElement): React.ReactElement {
  return <ThemeProvider>{child}</ThemeProvider>
}

// ---------------------------------------------------------------------------
// Reusable presentational helpers
// ---------------------------------------------------------------------------

function CitizenMessage({ text }: { text: string }): React.ReactElement {
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="#a78bfa" paddingX={2} paddingY={1}>
      <Text color="#7c3aed" bold>
        ✻ 시민
      </Text>
      <Text color="#e9d5ff">{text}</Text>
    </Box>
  )
}

function KosmosResponse({
  title,
  lines,
}: {
  title: string
  lines: readonly string[]
}): React.ReactElement {
  return (
    <Box flexDirection="column" borderStyle="round" borderColor="#7c3aed" paddingX={2} paddingY={1}>
      <Text color="#a78bfa" bold>
        ✻ KOSMOS · {title}
      </Text>
      {lines.map((line, idx) => (
        <Text key={idx} color="#e9d5ff">
          {line}
        </Text>
      ))}
    </Box>
  )
}

function ProcessingBanner({
  step,
  total,
  message,
}: {
  step: number
  total: number
  message: string
}): React.ReactElement {
  return (
    <Box borderStyle="single" borderColor="#5b21b6" paddingX={2} paddingY={0}>
      <Text color="#c4b5fd">
        ⏺ 단계 {step}/{total} · {message}
      </Text>
    </Box>
  )
}

// ---------------------------------------------------------------------------
// Scenario 1 — 응급 (Emergency)
// ---------------------------------------------------------------------------
const SCENARIO_1: readonly ScenarioStep[] = [
  {
    slug: '응급/01-citizen-input',
    description: '응급 시나리오 — 시민 자연어 입력',
    element: withTheme(
      <CitizenMessage text="엄마가 갑자기 쓰러지셨어요. 119 부르고 가장 가까운 응급실 어디예요?" />,
    ),
  },
  {
    slug: '응급/02-query-engine-search',
    description: '응급 시나리오 — 쿼리엔진이 BM25 검색으로 후보 어댑터 도출',
    element: withTheme(
      <Box flexDirection="column" gap={1}>
        <ProcessingBanner step={2} total={5} message="쿼리엔진 → 도구 시스템 BM25 검색 (4 부처 후보)" />
        <CollectionList
          payload={{
            kind: 'lookup',
            subtype: 'collection',
            tool_id: 'lookup',
            items: [
              { index: 1, title: 'nfa_emergency_info_service', meta: '119 응급 신고 / 출동 안내' },
              { index: 2, title: 'hira_hospital_search', meta: '병의원 + 응급실 검색' },
              { index: 3, title: 'nmc_emergency_search', meta: '실시간 응급실 가용 병상 (L3 인증)' },
              { index: 4, title: 'kma_weather_alert_status', meta: '도로 결빙 / 강풍 특보' },
              { index: 5, title: 'resolve_location', meta: '시민 위치 → 좌표 (kakao/juso/sgis)' },
            ],
          }}
        />
      </Box>,
    ),
  },
  {
    slug: '응급/03-permission-gauntlet',
    description: '응급 시나리오 — L3 권한 게이트 (NMC 실시간 병상 데이터)',
    element: withTheme(
      <Box flexDirection="column" gap={1}>
        <ProcessingBanner step={3} total={5} message="권한 게이트 — NMC 실시간 병상 (Layer 3)" />
        <Box flexDirection="column" borderStyle="round" borderColor="#f87171" paddingX={2} paddingY={1}>
          <Text color="#fca5a5" bold>⓷ Layer 3 — 본인 인증 필요</Text>
          <Text color="#e9d5ff">도구: nmc_emergency_search (실시간 병상)</Text>
          <Text color="#c4b5fd">사유: 의료기관 가용 정보 · PIPA §26 수탁자</Text>
          <Box marginTop={1}>
            <Text color="#a78bfa">[Y] 한 번만 허용  [A] 세션 자동  [N] 거부</Text>
          </Box>
          <Text color="#7c3aed">→ 영수증: rcpt-emergency-2026-04-26-7B3F</Text>
        </Box>
      </Box>,
    ),
  },
  {
    slug: '응급/04-adapter-detail',
    description: '응급 시나리오 — 어댑터 응답 (강남세브란스 응급실 상세)',
    element: withTheme(
      <Box flexDirection="column" gap={1}>
        <ProcessingBanner step={4} total={5} message="어댑터 실행 → 다부처 응답 합성" />
        <DetailView
          payload={{
            kind: 'lookup',
            subtype: 'detail',
            tool_id: 'hira_hospital_search + nmc_emergency_search',
            fields: [
              { label: '추천 응급실', value: '강남세브란스병원 응급의료센터' },
              { label: '거리 / 예상 도착', value: '8분 (2.4 km, 차량)' },
              { label: '실시간 가용 병상', value: '3 / 28 (NMC 갱신 1분 전)' },
              { label: '진료과', value: '응급의학 · 심혈관 · 신경과 24시간' },
              { label: 'KMA 도로 기상', value: '⚠ 빙판 결빙 주의보 발효 중 (서울 전역)' },
              { label: '119 신고', value: '자동 호출 가이드 — 시민 위치 좌표 첨부됨' },
            ],
          }}
        />
      </Box>,
    ),
  },
  {
    slug: '응급/05-kosmos-response',
    description: '응급 시나리오 — KOSMOS 통합 응답 (시민 입장의 다음 행동)',
    element: withTheme(
      <KosmosResponse
        title="응답 (4 부처 통합)"
        lines={[
          '',
          '1. 119 즉시 호출 — 위치 좌표 자동 전달 가능 (탭하여 호출).',
          '2. 가장 가까운 응급실: 강남세브란스 (8분, 2.4 km).',
          '   · 가용 병상 3 / 28 · 응급·심혈관·신경과 24시간',
          '3. ⚠ 빙판 주의 — 도로 결빙 경보 발효, 보호자 차량 이동 시 감속 필수.',
          '',
          '권한 영수증: rcpt-emergency-2026-04-26-7B3F (NMC L3 사용)',
          '데이터 출처: NFA 119 · HIRA · NMC · KMA · 카카오 로컬',
        ]}
      />,
    ),
  },
] as const

// ---------------------------------------------------------------------------
// Scenario 2 — 위기 (Sudden job loss)
// ---------------------------------------------------------------------------
const SCENARIO_2: readonly ScenarioStep[] = [
  {
    slug: '위기/01-citizen-input',
    description: '위기 시나리오 — 시민 자연어 입력 (실직)',
    element: withTheme(
      <CitizenMessage text="회사가 갑자기 망했어요. 실업급여 받고 새 직장도 알아봐야 하고, 임대주택 우선순위까지 신청하고 싶어요." />,
    ),
  },
  {
    slug: '위기/02-query-engine-search',
    description: '위기 시나리오 — 쿼리엔진 검색 (4 부처 fan-out)',
    element: withTheme(
      <Box flexDirection="column" gap={1}>
        <ProcessingBanner step={2} total={5} message="쿼리엔진 → 도구 시스템 BM25 검색 (4 부처 fan-out)" />
        <CollectionList
          payload={{
            kind: 'lookup',
            subtype: 'collection',
            tool_id: 'lookup',
            items: [
              { index: 1, title: 'mock_unemployment_benefit', meta: '고용노동부 실업급여 자격 / 신청' },
              { index: 2, title: 'mock_worknet_jobsearch', meta: '워크넷 직업훈련 + 재취업 매칭' },
              { index: 3, title: 'mock_verify_mydata', meta: '마이데이터 — 소득 정보 자동 인증' },
              { index: 4, title: 'mock_lh_priority_apply', meta: 'LH 임대주택 우선순위 (실직 가산점)' },
              { index: 5, title: 'mock_welfare_application_submit_v1', meta: '정부24 통합 신청' },
            ],
          }}
        />
      </Box>,
    ),
  },
  {
    slug: '위기/03-mydata-verify',
    description: '위기 시나리오 — 마이데이터 본인 인증 (소득 자동 조회)',
    element: withTheme(
      <Box flexDirection="column" gap={1}>
        <ProcessingBanner step={3} total={5} message="마이데이터 인증 — 소득 정보 자동 조회 (AAL2)" />
        <AuthContextCard
          payload={{
            kind: 'verify',
            tool_id: 'mock_verify_mydata',
            family: 'mydata',
            ok: true,
            korea_tier: '마이데이터 v240930',
            nist_aal_hint: 'AAL2',
            identity_label: '홍길동 (1985년생) · 인증 완료',
          }}
        />
      </Box>,
    ),
  },
  {
    slug: '위기/04-adapter-detail',
    description: '위기 시나리오 — 4 부처 응답 합성 (자격 + 우선순위)',
    element: withTheme(
      <Box flexDirection="column" gap={1}>
        <ProcessingBanner step={4} total={5} message="4 부처 응답 합성 → 자격 / 우선순위 / 다음 단계" />
        <DetailView
          payload={{
            kind: 'lookup',
            subtype: 'detail',
            tool_id: '4-adapter fan-out (employment + worknet + lh + mydata)',
            fields: [
              { label: '실업급여 자격', value: '✓ 적격 — 고용보험 18개월 가입 (12개월 이상)' },
              { label: '예상 수급액', value: '월 184만원 × 240일 (총 1,472만원)' },
              { label: '직업훈련 추천', value: 'IT 5종 · 디자인 3종 · 사무직 7종 (워크넷)' },
              { label: 'LH 임대주택 가산점', value: '+20점 (실직자 우선순위)' },
              { label: '신청 마감일', value: '실직 후 14일 내 고용센터 방문 필수' },
              { label: '소득 인증', value: '마이데이터 자동 인증 완료 — 별도 서류 불요' },
            ],
          }}
        />
      </Box>,
    ),
  },
  {
    slug: '위기/05-kosmos-response',
    description: '위기 시나리오 — KOSMOS 통합 응답 (다음 행동 단계)',
    element: withTheme(
      <KosmosResponse
        title="응답 (4 부처 통합 + 다음 단계)"
        lines={[
          '',
          '✓ 실업급여 신청 가능: 월 184만원 × 240일 (총 1,472만원)',
          '✓ LH 임대주택 우선순위 +20점 부여 (실직 가산)',
          '✓ 추천 직업훈련: IT 5종 · 디자인 3종 · 사무직 7종',
          '✓ 마이데이터 소득 인증 완료 — 종이 서류 불요',
          '',
          '다음 단계 (시간순):',
          '  ① 14일 내 가까운 고용센터 방문 (위치 안내 →)',
          '  ② 워크넷 직업훈련 신청 (자격 인정 후 즉시)',
          '  ③ LH 임대 신청 (다음 분기 선정 cycle)',
        ]}
      />,
    ),
  },
] as const

// ---------------------------------------------------------------------------
// Scenario 3 — 재난 (Jeonse fraud)
// ---------------------------------------------------------------------------
const SCENARIO_3: readonly ScenarioStep[] = [
  {
    slug: '재난/01-citizen-input',
    description: '재난 시나리오 — 시민 자연어 입력 (전세사기)',
    element: withTheme(
      <CitizenMessage text="전세사기 당했어요. 보증금 못 돌려받을 것 같아요. 어떻게 해야 해요?" />,
    ),
  },
  {
    slug: '재난/02-query-engine-search',
    description: '재난 시나리오 — 쿼리엔진 검색 (4 부처 동시 트랙)',
    element: withTheme(
      <Box flexDirection="column" gap={1}>
        <ProcessingBanner step={2} total={5} message="쿼리엔진 → 도구 시스템 BM25 검색 (4 트랙 동시)" />
        <CollectionList
          payload={{
            kind: 'lookup',
            subtype: 'collection',
            tool_id: 'lookup',
            items: [
              { index: 1, title: 'mock_hug_warranty_claim', meta: 'HUG 전세보증보험 청구' },
              { index: 2, title: 'mock_lease_dispute_apply', meta: '주택임대차분쟁조정위원회' },
              { index: 3, title: 'mock_legal_aid_consult', meta: '대한법률구조공단 무료 상담' },
              { index: 4, title: 'mock_traffic_fine_pay_v1', meta: '경찰청 사기 신고 (mock)' },
              { index: 5, title: 'mock_verify_gongdong_injeungseo', meta: '공동인증서 — 신청 본인 확인' },
            ],
          }}
        />
      </Box>,
    ),
  },
  {
    slug: '재난/03-permission-gauntlet',
    description: '재난 시나리오 — L2 권한 게이트 (다부처 동시 신청)',
    element: withTheme(
      <Box flexDirection="column" gap={1}>
        <ProcessingBanner step={3} total={5} message="권한 게이트 — L2 인증 (4 부처 동시 신청)" />
        <Box flexDirection="column" borderStyle="round" borderColor="#f59e0b" paddingX={2} paddingY={1}>
          <Text color="#fbbf24" bold>⓶ Layer 2 — 본인 인증 필요</Text>
          <Text color="#e9d5ff">도구: HUG · 분쟁조정 · 법률구조 · 경찰 (4 트랙)</Text>
          <Text color="#c4b5fd">인증 옵션: 공동인증서 · 금융인증서 · 간편인증</Text>
          <Box marginTop={1}>
            <Text color="#a78bfa">[Y] 한 번만 허용  [A] 세션 자동  [N] 거부</Text>
          </Box>
          <Text color="#7c3aed">→ 영수증: rcpt-jeonse-2026-04-26-9C2D</Text>
        </Box>
      </Box>,
    ),
  },
  {
    slug: '재난/04-adapter-detail',
    description: '재난 시나리오 — 3트랙 동시 권고 (HUG + 분쟁조정 + 법률구조 + 경찰)',
    element: withTheme(
      <Box flexDirection="column" gap={1}>
        <ProcessingBanner step={4} total={5} message="4 부처 응답 합성 → 동시 트랙 권고" />
        <DetailView
          payload={{
            kind: 'lookup',
            subtype: 'detail',
            tool_id: '4-adapter fan-out (HUG + lease-dispute + legal-aid + police)',
            fields: [
              { label: '① HUG 보증금 반환', value: '✓ 청구 가능 — 보증보험 가입 확인' },
              { label: '② 임대차분쟁조정', value: '신청 가능 (서울지부 — 강남구) · 7~14일 결정' },
              { label: '③ 법률구조공단', value: '무료 상담 — 내일 14시 예약 가능' },
              { label: '④ 형사 신고 (경찰)', value: '사기죄 + 가해자 출국금지 신청 동반 권고' },
              { label: '예상 보증금 회수', value: '85% 확률 (HUG 보증) · 60일 이내' },
              { label: '필요 서류', value: '임대차계약서 · 보증보험증 · 통장사본 (자동첨부)' },
            ],
          }}
        />
      </Box>,
    ),
  },
  {
    slug: '재난/05-kosmos-response',
    description: '재난 시나리오 — KOSMOS 통합 응답 (3 트랙 동시 행동 가이드)',
    element: withTheme(
      <KosmosResponse
        title="응답 (4 부처 통합 · 3 트랙 동시 권고)"
        lines={[
          '',
          '동시에 진행하셔야 할 3 트랙:',
          '  ① HUG 보증금 반환 청구 — 오늘 신청, 60일 이내 회수 (85% 확률)',
          '  ② 임대차분쟁조정 신청 — 강남지부, 7~14일 결정',
          '  ③ 형사 신고 + 가해자 출국금지 — 가까운 경찰서, 즉시',
          '',
          '먼저 받으실 무료 법률 상담:',
          '  → 대한법률구조공단 강남지부 — 내일 14시 예약 (자동 등록 가능)',
          '',
          '필요 서류 자동 첨부 완료 (임대차계약서 · 보증보험 · 통장)',
          '권한 영수증: rcpt-jeonse-2026-04-26-9C2D',
        ]}
      />,
    ),
  },
] as const

// ---------------------------------------------------------------------------
// Run all scenarios
// ---------------------------------------------------------------------------

const ALL_STEPS: readonly ScenarioStep[] = [...SCENARIO_1, ...SCENARIO_2, ...SCENARIO_3]

interface DumpOutcome {
  readonly slug: string
  readonly status: 'ok' | 'fail'
  readonly bytes: number
  readonly error?: string
}

function dump(step: ScenarioStep): DumpOutcome {
  try {
    const { lastFrame, unmount } = render(step.element)
    const frame = lastFrame() ?? '(empty frame)'
    const header = `# Citizen scenario frame — ${step.slug}\n# ${step.description}\n# Captured ${new Date().toISOString()} via ink-testing-library render()\n# KOSMOS v0.1-alpha · K-EXAONE-236B-A23B + FriendliAI Serverless\n\n`
    const txtPath = join(OUT_DIR, `${step.slug}.txt`)
    mkdirSync(join(OUT_DIR, step.slug.split('/')[0] ?? ''), { recursive: true })
    writeFileSync(txtPath, header + frame + '\n', 'utf-8')
    unmount()
    return { slug: step.slug, status: 'ok', bytes: frame.length }
  } catch (err) {
    const error = err instanceof Error ? err.message : String(err)
    return { slug: step.slug, status: 'fail', bytes: 0, error }
  }
}

const outcomes = ALL_STEPS.map(dump)
const ok = outcomes.filter((o) => o.status === 'ok').length
const fail = outcomes.filter((o) => o.status === 'fail').length

console.log(`[dump-scenario-frames] ${ok} ok, ${fail} fail (out: ${OUT_DIR})`)
for (const o of outcomes) {
  console.log(
    `  ${o.status === 'ok' ? '✓' : '✗'} ${o.slug.padEnd(32)} ${o.status === 'ok' ? `${o.bytes}B` : o.error}`,
  )
}

process.exit(fail === 0 ? 0 : 1)
