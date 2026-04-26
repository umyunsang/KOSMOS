// SPDX-License-Identifier: Apache-2.0
// Proposal IV · 최종 — 2026-04-24 사용자 요구사항 반영
//
// • Empty state: CC LogoV2 원본 그대로 (부처 feed 표시 안 함)
// • Active session 평소: CondensedLogo + tool_use(⏺ MINISTRY, primitive-colored dot)
// • Multi-ministry swarm: PhaseIndicator + SpinnerWithVerb
// • Mock은 UI에 노출하지 않음 — live와 동일하게 표시
// • /agents 명령: 활성 부처 에이전트 목록 (bordered notice)
// • /plugins 명령: 설치된 플러그인 목록 (bordered notice)
//
// 도트 색 규약:
//     🔵 blue    lookup    · 정보 조회
//     🟠 orange  submit    · 민원 제출
//     🔴 red     verify    · 본인 확인
//     🟢 green   subscribe · 알림 구독
//     🟣 purple  plugin.*  · 플러그인 네임스페이스 verb
//
// 신규 컴포넌트 0개 — 모두 포팅된 CC 컴포넌트 재사용.
//
// Run:  cd tui && bun ../docs/wireframes/proposal-iv.mjs

import { render } from 'ink'
import {
  h, Box, Text, C, Divider, WelcomeV2Block, FeedColumn, CondensedLogo,
  BorderedNotice, PhaseIndicator, Spinner, PromptBand, PromptFooter,
  UserMsg, ToolUseBlock, AsstLine,
} from './_shared.mjs'

// ─── State 1 · Empty (first launch) — CC 간결 ───────────────────────────
// 부처 feed 제거. CC LogoV2 원본 2-column + 일반 Feed만.
function EmptyState() {
  const whatsNewFeed = [
    { glyph: '▸', primary: 'CC TUI 시각 구조 ≥90% 포트 완료', secondary: 'v0.1' },
    { glyph: '▸', primary: 'PIPA 동의 온보딩 + 시민-안전 권한', secondary: 'v0.1' },
    { glyph: '▸', primary: '플러그인 인프라 준비 중',            secondary: 'v0.1' },
  ]
  const startTips = [
    { glyph: '▸', primary: '/help    자주 쓰는 커맨드 보기' },
    { glyph: '▸', primary: '/agents  활성 부처 에이전트' },
    { glyph: '▸', primary: '/plugins 설치된 플러그인' },
  ]
  return h(Box, { flexDirection: 'column' },
    h(Box, {
      borderStyle: 'round', borderColor: C.dim, paddingX: 1,
      flexDirection: 'row', width: 80,
    },
      h(Box, { flexDirection: 'column', width: 40, paddingRight: 2 },
        WelcomeV2Block(),
        h(Box, { marginTop: 1 },
          h(Text, { color: C.subtle }, '   K-EXAONE · FriendliAI')
        ),
        h(Box, null, h(Text, { color: C.dim }, '   ~/KOSMOS/tui')),
      ),
      h(Box, { flexDirection: 'column', width: 38 },
        h(FeedColumn, { title: '새 소식',      rows: whatsNewFeed }),
        h(Box, { marginTop: 1 },
          h(FeedColumn, { title: '시작 가이드', rows: startTips })),
      )
    ),
    h(Box, { marginTop: 1 }, h(PromptBand)),
    h(PromptFooter, {
      left:  '? for shortcuts  ⋅  / commands  ⋅  ⇧⇥ mode',
      right: 'q:0  ⋅  대기',
    }),
  )
}

// ─── State 2 · Active · 단일 부처 ──────────────────────────────────────
function ActiveSingle() {
  return h(Box, { flexDirection: 'column' },
    h(CondensedLogo),
    h(Box, { marginTop: 1 }, h(UserMsg, { text: '오늘 서울 날씨 어때?' })),
    h(Box, { marginTop: 1 }, h(AsstLine, { text: 'assistant:' })),
    h(Box, { marginTop: 1 }, h(ToolUseBlock, {
      primitive: 'lookup',
      ministry:  'KMA',
      detail:    '현재 관측 · 서울',
      result:    '12°C, 맑음, 미세먼지 보통',
    })),
    h(Box, { marginTop: 1 },
      h(Text, null, '서울 현재 12°C, 맑고 미세먼지는 보통입니다.')
    ),
    h(Box, { marginTop: 2 }, h(PromptBand)),
    h(PromptFooter, {
      left:  '? for shortcuts  ⋅  / commands  ⋅  ⇧⇥ mode',
      right: 'q:0  ⋅  대기',
    }),
  )
}

// ─── State 3 · Active · multi-ministry swarm ───────────────────────────
function ActiveSwarm() {
  return h(Box, { flexDirection: 'column' },
    h(CondensedLogo),
    h(Box, { marginTop: 1 }, h(PhaseIndicator, { phase: 'swarm' })),
    h(Box, { marginTop: 1 }, h(UserMsg, {
      text: '이사 준비 중이야. 전입신고·자동차 주소변경·건보 주소변경 다 해야해',
    })),
    h(Box, { marginTop: 1 }, h(AsstLine, {
      text: 'assistant: 3개 부처 협력이 필요합니다.',
    })),
    h(Box, { marginTop: 1 }, h(ToolUseBlock, {
      primitive: 'lookup', ministry: 'MOIS',
      detail:    '전입신고 절차 조회',
      result:    '세대주 이전일 기준 14일 내 관할 주민센터 방문',
    })),
    h(Box, { marginTop: 1 }, h(ToolUseBlock, {
      primitive: 'lookup', ministry: 'MOLIT',
      detail:    '자동차 주소변경 절차',
      result:    '전입신고 후 15일 내 자동차 등록증 주소 변경',
    })),
    h(Box, { marginTop: 1 }, h(ToolUseBlock, {
      primitive: 'lookup', ministry: 'NHIS',
      detail:    '건보 주소변경',
      result:    '전입신고 데이터 자동 연계 (별도 절차 불요)',
    })),
    h(Box, { marginTop: 1 }, h(Spinner, { verb: '3개 부처 응답 취합 중...' })),
    h(Box, { marginTop: 2 }, h(PromptBand)),
    h(PromptFooter, {
      left:  '? for shortcuts  ⋅  / commands  ⋅  ⇧⇥ mode',
      right: 'q:0  ⋅  swarm',
    }),
  )
}

// ─── State 4 · /agents 명령 결과 ────────────────────────────────────────
function AgentsCommand() {
  return h(Box, { flexDirection: 'column' },
    h(CondensedLogo),
    h(Box, { marginTop: 1 }, h(UserMsg, { text: '/agents' })),
    h(Box, { marginTop: 1 },
      h(BorderedNotice, {
        label: '◆ 활성 부처 에이전트 · 6 ministries',
        color: C.brand, width: 70,
      },
        h(Box, null,
          h(Text, { color: C.lookupDot, bold: true }, '⏺ KOROAD '),
          h(Text, null, '· 도로교통공단'),
          h(Text, { color: C.dim, dimColor: true }, '      사고 · 위험구간 조회'),
        ),
        h(Box, null,
          h(Text, { color: C.lookupDot, bold: true }, '⏺ KMA    '),
          h(Text, null, '· 기상청'),
          h(Text, { color: C.dim, dimColor: true }, '            날씨 · 예보 · 특보'),
        ),
        h(Box, null,
          h(Text, { color: C.lookupDot, bold: true }, '⏺ HIRA   '),
          h(Text, null, '· 건강보험심사평가원'),
          h(Text, { color: C.dim, dimColor: true }, '     병원 검색 · 진료비'),
        ),
        h(Box, null,
          h(Text, { color: C.lookupDot, bold: true }, '⏺ NMC    '),
          h(Text, null, '· 국립중앙의료원'),
          h(Text, { color: C.dim, dimColor: true }, '        응급 · 병상'),
        ),
        h(Box, null,
          h(Text, { color: C.lookupDot, bold: true }, '⏺ NFA    '),
          h(Text, null, '· 소방청'),
          h(Text, { color: C.dim, dimColor: true }, '            119 · 응급 출동'),
        ),
        h(Box, null,
          h(Text, { color: C.lookupDot, bold: true }, '⏺ MOHW   '),
          h(Text, null, '· 보건복지부'),
          h(Text, { color: C.dim, dimColor: true }, '         복지 자격 · 신청'),
        ),
      )
    ),
    h(Box, { marginTop: 2 }, h(PromptBand)),
    h(PromptFooter, {
      left:  '? for shortcuts  ⋅  / commands  ⋅  ⇧⇥ mode',
      right: 'q:0  ⋅  대기',
    }),
  )
}

// ─── State 5 · /plugins 명령 결과 ───────────────────────────────────────
function PluginsCommand() {
  return h(Box, { flexDirection: 'column' },
    h(CondensedLogo),
    h(Box, { marginTop: 1 }, h(UserMsg, { text: '/plugins' })),
    h(Box, { marginTop: 1 },
      h(BorderedNotice, {
        label: '◆ 설치된 플러그인 · 2 enabled',
        color: C.pluginDot, width: 70,
      },
        h(Box, null,
          h(Text, { color: C.pluginDot, bold: true }, '⏺ SeoulSubway '),
          h(Text, null, '· plugin.seoul-subway'),
          h(Text, { color: C.dim, dimColor: true }, '  지하철 실시간 도착'),
        ),
        h(Box, null,
          h(Text, { color: C.pluginDot, bold: true }, '⏺ PostOffice  '),
          h(Text, null, '· plugin.post-office '),
          h(Text, { color: C.dim, dimColor: true }, '   우체국 택배 추적'),
        ),
        h(Box, { marginTop: 1 },
          h(Text, { color: C.dim, dimColor: true },
            '기여: docs/plugins/quickstart.ko.md  ·  kosmos plugin init <name>')
        ),
      )
    ),
    h(Box, { marginTop: 2 }, h(PromptBand)),
    h(PromptFooter, {
      left:  '? for shortcuts  ⋅  / commands  ⋅  ⇧⇥ mode',
      right: 'q:0  ⋅  대기',
    }),
  )
}

function App() {
  return h(Box, { flexDirection: 'column' },
    h(Text, { bold: true, color: C.brand },
      'Proposal IV · 최종 (2026-04-24 요구사항 반영)'),
    h(Text, { color: C.subtle },
      '도트 색: 🔵lookup · 🟠submit · 🔴verify · 🟢subscribe · 🟣plugin  ·  Mock UI 노출 안 함'),
    h(Divider, { label: 'State 1 · Empty · CC 간결 (부처 feed 제거)' }),
    h(EmptyState),
    h(Divider, { label: 'State 2 · Active · 단일 부처 (⏺ KMA blue)' }),
    h(ActiveSingle),
    h(Divider, { label: 'State 3 · Active · swarm (⏺ MOIS · MOLIT · NHIS)' }),
    h(ActiveSwarm),
    h(Divider, { label: 'State 4 · /agents 명령 결과' }),
    h(AgentsCommand),
    h(Divider, { label: 'State 5 · /plugins 명령 결과' }),
    h(PluginsCommand),
    h(Box, { marginTop: 1 },
      h(Text, { color: C.dim },
        '— 신규 컴포넌트 0 — 모두 포팅된 CC 컴포넌트 재사용')
    )
  )
}

render(h(App))
