#!/usr/bin/env bun
// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — UX snapshot dumper.
//
// Renders each UI L2 surface in isolation via ink-testing-library and writes
// the last frame to specs/1635-ui-l2-citizen-port/ux-snapshots/<surface>.txt
// so the Lead can visually verify the citizen-facing UX without an
// interactive PTY session.
//
// Run: bun run scripts/dump-ui-l2-snapshots.tsx

import React from 'react';
import { render } from 'ink-testing-library';
import { mkdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';

// Inline ANSI strip — covers CSI, OSC, and basic SGR sequences.
// Avoids adding strip-ansi as a runtime dep (SC-008 compliance).
const ANSI_RE = /[][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-PRZcf-nqry=><]/g;
function stripAnsi(s: string): string {
  return s.replace(ANSI_RE, '');
}

import { PermissionLayerHeader } from '../src/components/permissions/PermissionLayerHeader.js';
import { PermissionGauntletModal } from '../src/components/permissions/PermissionGauntletModal.js';
import { ReceiptToast } from '../src/components/permissions/ReceiptToast.js';
import { BypassReinforcementModal } from '../src/components/permissions/BypassReinforcementModal.js';
import { ErrorEnvelope } from '../src/components/messages/ErrorEnvelope.js';
import { ContextQuoteBlock } from '../src/components/messages/ContextQuoteBlock.js';
import { StreamingChunk } from '../src/components/messages/StreamingChunk.js';
import { SlashCommandSuggestions } from '../src/components/PromptInput/SlashCommandSuggestions.js';
import { HelpV2Grouped } from '../src/components/help/HelpV2Grouped.js';
import { PluginBrowser } from '../src/components/plugins/PluginBrowser.js';
import { HistorySearchDialog } from '../src/components/history/HistorySearchDialog.js';
import { AgentVisibilityPanel } from '../src/components/agents/AgentVisibilityPanel.js';
import { AgentDetailRow } from '../src/components/agents/AgentDetailRow.js';
import { PreflightStep } from '../src/components/onboarding/PreflightStep.js';
import { ThemeStep } from '../src/components/onboarding/ThemeStep.js';
import { PipaConsentStep } from '../src/components/onboarding/PipaConsentStep.js';
import { TerminalSetupStep } from '../src/components/onboarding/TerminalSetupStep.js';

import type { PermissionReceiptT } from '../src/schemas/ui-l2/permission.js';
import type { ErrorEnvelopeT } from '../src/schemas/ui-l2/error.js';
import type { AgentVisibilityEntryT } from '../src/schemas/ui-l2/agent.js';
import { UI_L2_SLASH_COMMANDS } from '../src/commands/catalog.js';

const OUT_DIR = join(import.meta.dir, '..', '..', 'specs', '1635-ui-l2-citizen-port', 'ux-snapshots');
mkdirSync(OUT_DIR, { recursive: true });

type Snapshot = { name: string; component: React.ReactElement; note: string };

const snapshots: Snapshot[] = [
  // UI-C Permission Gauntlet (FR-015..018, 022)
  {
    name: '01-permission-modal-layer1',
    note: 'FR-015/016/017 — Layer 1 (green ⓵) modal with [Y/A/N]',
    component: React.createElement(PermissionGauntletModal, {
      layer: 1,
      toolName: 'koroad_traffic_lookup',
      description: '도로교통공단 사고 정보 조회',
      onDecide: () => {},
    }),
  },
  {
    name: '02-permission-modal-layer2',
    note: 'FR-016 — Layer 2 (orange ⓶) modal',
    component: React.createElement(PermissionGauntletModal, {
      layer: 2,
      toolName: 'hira_hospital_lookup',
      description: '심평원 의료기관 조회 (개인정보 포함)',
      onDecide: () => {},
    }),
  },
  {
    name: '03-permission-modal-layer3',
    note: 'FR-016 — Layer 3 (red ⓷) modal with reinforcement notice',
    component: React.createElement(PermissionGauntletModal, {
      layer: 3,
      toolName: 'gov24_civil_application_submit',
      description: '정부24 민원 제출 (시민 명의로 외부 시스템에 영향)',
      onDecide: () => {},
    }),
  },
  {
    name: '04-receipt-toast-issued',
    note: 'FR-018 — Receipt issued toast',
    component: React.createElement(ReceiptToast, {
      variant: 'issued',
      receiptId: 'rcpt-7d3a8f2e9c4b',
    }),
  },
  {
    name: '05-receipt-toast-revoked',
    note: 'FR-020 — Receipt revoked toast',
    component: React.createElement(ReceiptToast, {
      variant: 'revoked',
      receiptId: 'rcpt-7d3a8f2e9c4b',
    }),
  },
  {
    name: '06-receipt-toast-already-revoked',
    note: 'FR-021 — Idempotent already-revoked toast',
    component: React.createElement(ReceiptToast, {
      variant: 'already_revoked',
      receiptId: 'rcpt-7d3a8f2e9c4b',
    }),
  },
  {
    name: '07-bypass-reinforcement',
    note: 'FR-022 — bypassPermissions reinforcement modal',
    component: React.createElement(BypassReinforcementModal, {
      onConfirm: () => {},
      onCancel: () => {},
    }),
  },
  {
    name: '08-permission-layer-header-1',
    note: 'FR-016 — Layer 1 header glyph component standalone',
    component: React.createElement(PermissionLayerHeader, { layer: 1 }),
  },
  {
    name: '09-permission-layer-header-2',
    note: 'FR-016 — Layer 2 header standalone',
    component: React.createElement(PermissionLayerHeader, { layer: 2 }),
  },
  {
    name: '10-permission-layer-header-3',
    note: 'FR-016 — Layer 3 header standalone',
    component: React.createElement(PermissionLayerHeader, { layer: 3 }),
  },

  // UI-B REPL Main (FR-008..014)
  {
    name: '11-error-envelope-llm',
    note: 'FR-012 — LLM error envelope (purple/🧠)',
    component: React.createElement(ErrorEnvelope, {
      error: {
        type: 'llm',
        title_ko: 'LLM 응답 오류',
        title_en: 'LLM response error',
        detail_ko: 'K-EXAONE 모델이 4xx 응답을 반환했습니다.',
        detail_en: 'K-EXAONE returned a 4xx response.',
        retry_suggested: true,
        occurred_at: new Date('2026-04-25T12:00:00Z').toISOString(),
      } as ErrorEnvelopeT,
      onRetry: () => {},
    }),
  },
  {
    name: '12-error-envelope-tool',
    note: 'FR-012 — Tool error envelope (orange/🔧)',
    component: React.createElement(ErrorEnvelope, {
      error: {
        type: 'tool',
        title_ko: '도구 호출 오류',
        title_en: 'Tool invocation error',
        detail_ko: 'KOROAD 어댑터가 timeout 에러를 반환했습니다.',
        detail_en: 'KOROAD adapter returned timeout.',
        retry_suggested: true,
        occurred_at: new Date('2026-04-25T12:00:00Z').toISOString(),
      } as ErrorEnvelopeT,
      onRetry: () => {},
    }),
  },
  {
    name: '13-error-envelope-network',
    note: 'FR-012 — Network error envelope (red/📡)',
    component: React.createElement(ErrorEnvelope, {
      error: {
        type: 'network',
        title_ko: '네트워크 연결이 끊어졌습니다',
        title_en: 'Network connection lost',
        detail_ko: '5초간 응답이 없습니다. 다시 시도해주세요.',
        detail_en: 'No response for 5 seconds. Please retry.',
        retry_suggested: true,
        occurred_at: new Date('2026-04-25T12:00:00Z').toISOString(),
      } as ErrorEnvelopeT,
      onRetry: () => {},
    }),
  },
  {
    name: '14-context-quote-block',
    note: 'FR-013 — ⎿ quote block with single-border',
    component: React.createElement(ContextQuoteBlock, {
      label: 'Turn 3',
      children: '시민님이 차상위 가구 대상 의료급여 신청을 시작했습니다.',
    }),
  },
  {
    name: '15-streaming-chunk-active',
    note: 'FR-008 — 20-token chunk streaming (mid-stream sample)',
    component: React.createElement(StreamingChunk, {
      streamedText: '오늘 서울 강남구 일대 도로 상황을 조회하고 있습니다. 현재 잠실대교 부근에서 ',
      isStreaming: true,
    }),
  },
  {
    name: '16-slash-autocomplete',
    note: 'FR-014 — autocomplete dropdown after typing /',
    component: React.createElement(SlashCommandSuggestions, {
      inputText: '/c',
      selectedIndex: 0,
      onSelect: () => {},
    }),
  },

  // UI-D Ministry Agent (FR-025..028)
  {
    name: '17-agent-visibility-panel-swarm',
    note: 'FR-025 — proposal-iv 5-state panel with 3 ministries',
    component: React.createElement(AgentVisibilityPanel, {
      initialEntries: [
        {
          agent_id: 'mohw-001',
          ministry: 'MOHW',
          state: 'running',
          sla_remaining_ms: 8400,
          health: 'green',
          rolling_avg_response_ms: 320,
          last_transition_at: new Date('2026-04-25T12:00:00Z').toISOString(),
        },
        {
          agent_id: 'knpa-002',
          ministry: 'KNPA',
          state: 'waiting-permission',
          sla_remaining_ms: 12000,
          health: 'amber',
          rolling_avg_response_ms: 580,
          last_transition_at: new Date('2026-04-25T12:00:01Z').toISOString(),
        },
        {
          agent_id: 'mois-003',
          ministry: 'MOIS',
          state: 'done',
          sla_remaining_ms: null,
          health: 'green',
          rolling_avg_response_ms: 240,
          last_transition_at: new Date('2026-04-25T12:00:02Z').toISOString(),
        },
      ] as AgentVisibilityEntryT[],
      showDetail: false,
    }),
  },
  {
    name: '18-agent-visibility-panel-detail',
    note: 'FR-026 — /agents --detail with SLA + health + avg-response',
    component: React.createElement(AgentVisibilityPanel, {
      initialEntries: [
        {
          agent_id: 'mohw-001',
          ministry: 'MOHW',
          state: 'running',
          sla_remaining_ms: 8400,
          health: 'green',
          rolling_avg_response_ms: 320,
          last_transition_at: new Date('2026-04-25T12:00:00Z').toISOString(),
        },
        {
          agent_id: 'knpa-002',
          ministry: 'KNPA',
          state: 'waiting-permission',
          sla_remaining_ms: 12000,
          health: 'amber',
          rolling_avg_response_ms: 580,
          last_transition_at: new Date('2026-04-25T12:00:01Z').toISOString(),
        },
      ] as AgentVisibilityEntryT[],
      showDetail: true,
    }),
  },

  // UI-E Auxiliary (FR-029..033)
  {
    name: '19-help-v2-grouped',
    note: 'FR-029 — /help 4-group output (Session/Permission/Tool/Storage)',
    component: React.createElement(HelpV2Grouped, {
      catalog: UI_L2_SLASH_COMMANDS,
      locale: 'ko',
    }),
  },
  {
    name: '20-plugin-browser',
    note: 'FR-031 — /plugins browser ⏺/○ + Space/i/r/a',
    component: React.createElement(PluginBrowser, {
      plugins: [
        { id: 'kosmos-koroad', name: 'KOROAD 교통 정보', active: true, version: '0.1.0' },
        { id: 'kosmos-hira', name: 'HIRA 의료기관', active: true, version: '0.1.0' },
        { id: 'kosmos-gov24', name: '정부24 민원', active: false, version: '0.0.5' },
      ],
      onToggle: () => {},
      onDetail: () => {},
      onRemove: () => {},
      onMarketplace: () => {},
      onDismiss: () => {},
    }),
  },
  {
    name: '21-history-search-dialog',
    note: 'FR-033 — /history 3-filter form',
    component: React.createElement(HistorySearchDialog, {
      sessions: [
        {
          session_id: 'sess-2026-04-20-001',
          started_at: '2026-04-20T09:30:00Z',
          last_active_at: '2026-04-20T10:00:00Z',
          preview: '운전면허 갱신 안내',
          layers_touched: [1, 2],
        },
        {
          session_id: 'sess-2026-04-22-002',
          started_at: '2026-04-22T14:15:00Z',
          last_active_at: '2026-04-22T15:30:00Z',
          preview: '차상위 의료급여 신청',
          layers_touched: [1, 2, 3],
        },
      ],
      onSelect: () => {},
      onCancel: () => {},
    }),
  },

  // UI-A Onboarding 5-step (FR-001..006)
  {
    name: '22-onboarding-1-preflight',
    note: 'FR-001 step 1 — Preflight ✓/✗ checks',
    component: React.createElement(PreflightStep, {
      onAdvance: () => {},
      onBack: () => {},
    }),
  },
  {
    name: '23-onboarding-2-theme',
    note: 'FR-001 step 2 + FR-035 — UFO mascot purple palette',
    component: React.createElement(ThemeStep, {
      onAdvance: () => {},
      onBack: () => {},
    }),
  },
  {
    name: '24-onboarding-3-pipa-consent',
    note: 'FR-001 step 3 + FR-006 — PIPA §26 trustee notice',
    component: React.createElement(PipaConsentStep, {
      onAdvance: () => {},
      onBack: () => {},
    }),
  },
  {
    name: '25-onboarding-5-terminal-setup',
    note: 'FR-001 step 5 + FR-005 — 4 a11y toggles',
    component: React.createElement(TerminalSetupStep, {
      onAdvance: () => {},
      onBack: () => {},
    }),
  },
  {
    name: '26-agent-detail-row',
    note: 'FR-026 — Single agent detail row',
    component: React.createElement(AgentDetailRow, {
      agent: {
        agent_id: 'mohw-001',
        ministry: 'MOHW',
        state: 'running',
        sla_remaining_ms: 8400,
        health: 'green',
        rolling_avg_response_ms: 320,
        last_transition_at: new Date('2026-04-25T12:00:00Z').toISOString(),
      } as AgentVisibilityEntryT,
    }),
  },
];

let pass = 0;
let fail = 0;
const failures: { name: string; error: string }[] = [];

for (const { name, component, note } of snapshots) {
  try {
    const { lastFrame, unmount } = render(component);
    // Allow a tick for useEffect to fire
    await new Promise((resolve) => setTimeout(resolve, 30));
    const frame = lastFrame() ?? '<empty frame>';
    const cleaned = stripAnsi(frame);
    const out = `# UX Snapshot: ${name}\n# Note: ${note}\n# Generated: ${new Date().toISOString()}\n\n${cleaned}\n`;
    writeFileSync(join(OUT_DIR, `${name}.txt`), out, 'utf8');
    unmount();
    pass++;
    console.log(`✓ ${name}`);
  } catch (err) {
    fail++;
    const errMsg = err instanceof Error ? err.message : String(err);
    failures.push({ name, error: errMsg });
    console.error(`✗ ${name}: ${errMsg}`);
  }
}

// Index file
const indexLines = [
  '# UX Snapshots — Spec 1635 P4 UI L2 Citizen Port',
  `# Generated: ${new Date().toISOString()}`,
  `# Pass: ${pass} · Fail: ${fail} · Total: ${snapshots.length}`,
  '',
];
for (const { name, note } of snapshots) {
  indexLines.push(`- ${name}.txt — ${note}`);
}
writeFileSync(join(OUT_DIR, 'INDEX.txt'), indexLines.join('\n') + '\n', 'utf8');

console.log(`\n=== Summary ===`);
console.log(`Pass: ${pass} / Fail: ${fail} / Total: ${snapshots.length}`);
console.log(`Output: ${OUT_DIR}`);
if (fail > 0) {
  console.log('\nFailures:');
  for (const f of failures) {
    console.log(`  ${f.name}: ${f.error}`);
  }
  process.exit(1);
}
