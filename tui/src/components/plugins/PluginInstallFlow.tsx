// SPDX-License-Identifier: Apache-2.0
//
// Spec 1979 — KOSMOS citizen plugin install/uninstall/list flow component.
//
// Source pattern (per memory feedback_cc_source_migration_pattern):
//   .references/claude-code-sourcemap/restored-src/src/commands/plugin/plugin.tsx
//   .references/claude-code-sourcemap/restored-src/src/components/permissions/PermissionPrompt.tsx
//
// CC 2.1.88's permission UX uses:
//   - <Select options={...} onChange={...} onCancel={...} /> for option selection
//   - Arrow keys + Enter for navigation (NOT direct Y/N/A keystrokes)
//   - Esc for cancellation
//
// KOSMOS-internal Y/N/A direct-keystroke pattern (earlier dev iteration) is
// replaced here by CC's Select-based pattern for consistency with the rest
// of the TUI (PluginBrowser, PermissionGauntletModal in Spec 1978, etc).

import { Box, Text } from 'ink';
import * as React from 'react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { Select, type OptionWithDescription } from '../CustomSelect/index.js';
import { getKosmosBridgeSessionId, getOrCreateKosmosBridge } from '../../ipc/bridgeSingleton.js';
import { useTheme } from '../../theme/provider.js';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type PluginInstallFlowProps = {
  /** Sub-command parsed by /plugin command (install / uninstall / list). */
  sub: 'install' | 'uninstall' | 'list';
  /** Catalog name for install/uninstall (omitted for list). */
  name?: string;
  /** Optional --version pin. */
  requestedVersion?: string;
  /** --dry-run flag. */
  dryRun?: boolean;
  /** Called with the final acknowledgement when the flow completes. */
  onComplete: (summary?: string, options?: { display?: 'system' | 'skip' | 'user' }) => void;
};

type FlowState =
  | { kind: 'idle' }
  | { kind: 'sent' }
  | { kind: 'progress'; phase: number; messageKo: string }
  | { kind: 'awaiting_consent'; requestId: string; descriptionKo: string; descriptionEn: string }
  | { kind: 'completed'; summary: string }
  | { kind: 'failed'; summary: string };

// ---------------------------------------------------------------------------
// Frame builder
// ---------------------------------------------------------------------------

function _newCorrelationId(): string {
  return crypto.randomUUID();
}

function _now(): string {
  return new Date().toISOString();
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

const _ROUND_TRIP_TIMEOUT_MS = 90_000;

export function PluginInstallFlow({
  sub,
  name,
  requestedVersion,
  dryRun,
  onComplete,
}: PluginInstallFlowProps): React.ReactElement {
  const theme = useTheme();
  const [state, setState] = useState<FlowState>({ kind: 'idle' });
  const [correlationId] = useState<string>(_newCorrelationId());

  // Send a permission_response frame (allow_once / allow_session / deny).
  const sendPermissionResponse = useCallback(
    (requestId: string, decision: 'allow_once' | 'allow_session' | 'deny') => {
      const bridge = getOrCreateKosmosBridge();
      const sessionId = getKosmosBridgeSessionId();
      bridge.send({
        kind: 'permission_response',
        version: '1.0',
        session_id: sessionId,
        correlation_id: requestId,
        ts: _now(),
        role: 'tui',
        request_id: requestId,
        decision,
      } as never);
      setState({
        kind: 'progress',
        phase: 5,
        messageKo: decision === 'deny' ? '📝 동의 거부 처리 중…' : '📝 동의 처리 중…',
      });
    },
    [],
  );

  // CC PermissionPrompt pattern: 3 options with arrow+Enter selection.
  const consentOptions: OptionWithDescription<'allow_once' | 'allow_session' | 'deny'>[] = useMemo(
    () => [
      { label: '한 번만 허용 (Allow once)', value: 'allow_once' },
      { label: '세션 내 자동 허용 (Allow for session)', value: 'allow_session' },
      { label: '거부 (Deny)', value: 'deny' },
    ],
    [],
  );

  // Main round-trip effect: emit request + iterate frames until terminal.
  useEffect(() => {
    let cancelled = false;
    const bridge = getOrCreateKosmosBridge();
    const sessionId = getKosmosBridgeSessionId();

    // Build + send the request frame.
    const requestPayload: Record<string, unknown> = {
      kind: 'plugin_op',
      version: '1.0',
      session_id: sessionId,
      correlation_id: correlationId,
      ts: _now(),
      role: 'tui',
      op: 'request',
      request_op: sub,
    };
    if (sub === 'install') {
      requestPayload.name = name ?? '';
      requestPayload.requested_version = requestedVersion ?? null;
      requestPayload.dry_run = Boolean(dryRun);
    } else if (sub === 'uninstall') {
      requestPayload.name = name ?? '';
    }
    bridge.send(requestPayload as never);
    setState({ kind: 'sent' });

    // Iterate frames until terminal complete (or timeout / cancellation).
    const deadline = Date.now() + _ROUND_TRIP_TIMEOUT_MS;
    (async () => {
      try {
        for await (const frame of bridge.frames()) {
          if (cancelled) return;
          if (Date.now() > deadline) {
            setState({ kind: 'failed', summary: '✗ 라운드트립 타임아웃 (90s)' });
            onComplete('✗ 라운드트립 타임아웃 (90s)', { display: 'system' });
            return;
          }
          const f = frame as {
            kind?: string;
            correlation_id?: string;
            op?: string;
            result?: string;
            exit_code?: number;
            receipt_id?: string | null;
            progress_phase?: number;
            progress_message_ko?: string;
            progress_message_en?: string;
            request_id?: string;
            description_ko?: string;
            description_en?: string;
          };

          // permission_request — IPCConsentBridge correlates by request_id, NOT
          // by our top-level correlation_id. Match on request_id presence.
          if (f.kind === 'permission_request' && f.request_id) {
            setState({
              kind: 'awaiting_consent',
              requestId: f.request_id,
              descriptionKo: f.description_ko ?? '플러그인 설치 동의 요청',
              descriptionEn: f.description_en ?? 'Plugin install consent request',
            });
            continue;
          }

          if (f.correlation_id !== correlationId) continue;

          if (f.kind === 'plugin_op' && f.op === 'progress') {
            setState({
              kind: 'progress',
              phase: f.progress_phase ?? 0,
              messageKo: f.progress_message_ko ?? '',
            });
            continue;
          }

          if (f.kind === 'plugin_op' && f.op === 'complete') {
            const successSummary =
              sub === 'install' && name
                ? `✓ ${name} 플러그인 설치 완료${f.receipt_id ? ` · 영수증 ${f.receipt_id}` : ''}`
                : sub === 'uninstall' && name
                  ? `🗑️ ${name} 플러그인 제거 완료`
                  : '📋 플러그인 목록 조회 완료';
            const failureSummary =
              sub === 'install' && name
                ? `✗ ${name} 플러그인 설치 실패 (exit_code=${f.exit_code ?? 1})`
                : sub === 'uninstall' && name
                  ? `✗ ${name} 플러그인 제거 실패 (exit_code=${f.exit_code ?? 1})`
                  : `✗ 목록 조회 실패 (exit_code=${f.exit_code ?? 1})`;
            const summary = f.result === 'success' ? successSummary : failureSummary;
            setState({
              kind: f.result === 'success' ? 'completed' : 'failed',
              summary,
            });
            onComplete(summary, { display: 'system' });
            return;
          }
        }
      } catch (err) {
        if (cancelled) return;
        const summary = `✗ IPC 오류: ${err instanceof Error ? err.message : String(err)}`;
        setState({ kind: 'failed', summary });
        onComplete(summary, { display: 'system' });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [sub, name, requestedVersion, dryRun, correlationId, onComplete]);

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <Box flexDirection="column" paddingX={1} paddingY={1}>
      <Box marginBottom={1}>
        <Text bold color={theme.kosmosCore}>
          {'✻ '}
        </Text>
        <Text bold>
          {sub === 'install'
            ? `KOSMOS 플러그인 설치: ${name}`
            : sub === 'uninstall'
              ? `KOSMOS 플러그인 제거: ${name}`
              : 'KOSMOS 플러그인 목록 조회'}
        </Text>
      </Box>

      {state.kind === 'sent' ? (
        <Text color={theme.subtle}>{'⏳  요청 전송 — 백엔드 응답 대기 중…'}</Text>
      ) : null}

      {state.kind === 'progress' ? (
        <Text>{`⏳  Phase ${state.phase}/7 — ${state.messageKo}`}</Text>
      ) : null}

      {state.kind === 'awaiting_consent' ? (
        <Box flexDirection="column">
          <Box marginBottom={1}>
            <Text>{state.descriptionKo}</Text>
          </Box>
          <Box marginBottom={1}>
            <Text dimColor>{state.descriptionEn}</Text>
          </Box>
          <Box marginBottom={1}>
            <Text bold>{'설치를 진행하시겠습니까? (Do you want to proceed?)'}</Text>
          </Box>
          <Select
            options={consentOptions}
            onChange={(value) => sendPermissionResponse(state.requestId, value)}
            onCancel={() => sendPermissionResponse(state.requestId, 'deny')}
          />
          <Box marginTop={1}>
            <Text dimColor>{'Esc 취소 (Esc to cancel)'}</Text>
          </Box>
        </Box>
      ) : null}

      {state.kind === 'completed' ? <Text color={theme.kosmosCore}>{state.summary}</Text> : null}

      {state.kind === 'failed' ? <Text color="red">{state.summary}</Text> : null}
    </Box>
  );
}
