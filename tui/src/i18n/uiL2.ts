// SPDX-License-Identifier: Apache-2.0
// Spec 1635 P4 UI L2 — bilingual string bundle (FR-004 ko-primary + en-fallback).
//
// Isolated from the legacy Spec 287 i18n bundle (tui/src/i18n/keys.ts) to
// avoid expanding the existing I18nBundle interface. UI L2 components import
// from this module directly.
import type { ErrorEnvelopeTypeT } from '../schemas/ui-l2/error.js';
import type { PermissionLayerT } from '../schemas/ui-l2/permission.js';

export type UiL2Bundle = {
  // UI-B REPL
  streamingHint: string;
  ctrlOExpand: string;
  ctrlOCollapse: string;
  pdfRenderingInline: string;
  pdfFallbackOpen: string;
  pdfFallbackText: (path: string, sizeKb: number, sha: string) => string;
  errorTitle: (type: ErrorEnvelopeTypeT) => string;
  errorRetryHint: string;

  // UI-C permission
  permissionLayer: (layer: PermissionLayerT) => string;
  permissionAllowOnce: string;
  permissionAllowSession: string;
  permissionDeny: string;
  permissionLayer3Reinforcement: string;
  receiptIssued: (id: string) => string;
  consentRevoked: (id: string) => string;
  consentAlreadyRevoked: string;
  bypassReinforcement: string;

  // UI-E auxiliary
  helpGroupSession: string;
  helpGroupPermission: string;
  helpGroupTool: string;
  helpGroupStorage: string;
  langChanged: (locale: 'ko' | 'en') => string;
  configOverlayTitle: string;
  envSecretEditorTitle: string;
  pluginBrowserTitle: string;
  pluginToggleHint: string;
  exportPdfWriting: string;
  exportPdfDone: (path: string) => string;
  historySearchTitle: string;
};

const KO: UiL2Bundle = {
  streamingHint: '응답 수신 중…',
  ctrlOExpand: 'Ctrl-O로 펼치기',
  ctrlOCollapse: 'Ctrl-O로 접기',
  pdfRenderingInline: 'PDF 인라인 렌더 중…',
  pdfFallbackOpen: '📄 PDF 열기 시도 중…',
  pdfFallbackText: (path, sizeKb, sha) => `📄 ${path} · ${sizeKb} KB · sha256:${sha.slice(0, 12)}…`,
  errorTitle: (type) => {
    switch (type) {
      case 'llm': return 'LLM 응답 오류';
      case 'tool': return '도구 호출 오류';
      case 'network': return '네트워크 오류';
    }
  },
  errorRetryHint: '다시 시도하시겠습니까? (R)',

  permissionLayer: (layer) => `Layer ${layer}`,
  permissionAllowOnce: '이번 한 번만 허용',
  permissionAllowSession: '세션 동안 자동 허용',
  permissionDeny: '거부',
  permissionLayer3Reinforcement: '⚠️ 이 작업은 시민님 계정으로 외부 시스템에 영향을 줍니다.',
  receiptIssued: (id) => `발급됨 ${id}`,
  consentRevoked: (id) => `철회 완료 ${id}`,
  consentAlreadyRevoked: '이미 철회됨',
  bypassReinforcement:
    '이 모드는 모든 권한 모달을 우회합니다. 정말로 진행하시겠습니까?',

  helpGroupSession: '세션',
  helpGroupPermission: '권한',
  helpGroupTool: '도구',
  helpGroupStorage: '저장',
  langChanged: (locale) => `언어가 ${locale === 'ko' ? '한국어' : '영어'}로 변경되었습니다.`,
  configOverlayTitle: '설정',
  envSecretEditorTitle: '.env 비밀값 편집 (격리 모드)',
  pluginBrowserTitle: '플러그인 브라우저',
  pluginToggleHint: 'Space 활성 토글 · i 상세 · r 제거 · a 스토어',
  exportPdfWriting: 'PDF 생성 중…',
  exportPdfDone: (path) => `PDF 저장됨: ${path}`,
  historySearchTitle: '과거 세션 검색',
};

const EN: UiL2Bundle = {
  streamingHint: 'Receiving response…',
  ctrlOExpand: 'Ctrl-O to expand',
  ctrlOCollapse: 'Ctrl-O to collapse',
  pdfRenderingInline: 'Rendering PDF inline…',
  pdfFallbackOpen: '📄 Opening PDF in external viewer…',
  pdfFallbackText: (path, sizeKb, sha) => `📄 ${path} · ${sizeKb} KB · sha256:${sha.slice(0, 12)}…`,
  errorTitle: (type) => {
    switch (type) {
      case 'llm': return 'LLM response error';
      case 'tool': return 'Tool invocation error';
      case 'network': return 'Network error';
    }
  },
  errorRetryHint: 'Retry? (R)',

  permissionLayer: (layer) => `Layer ${layer}`,
  permissionAllowOnce: 'Allow once',
  permissionAllowSession: 'Allow for the session',
  permissionDeny: 'Deny',
  permissionLayer3Reinforcement:
    '⚠️ This operation will affect external systems on your behalf.',
  receiptIssued: (id) => `Issued ${id}`,
  consentRevoked: (id) => `Revoked ${id}`,
  consentAlreadyRevoked: 'Already revoked',
  bypassReinforcement:
    'This mode bypasses ALL permission modals. Are you sure you want to continue?',

  helpGroupSession: 'Session',
  helpGroupPermission: 'Permission',
  helpGroupTool: 'Tool',
  helpGroupStorage: 'Storage',
  langChanged: (locale) => `Language changed to ${locale === 'ko' ? 'Korean' : 'English'}.`,
  configOverlayTitle: 'Settings',
  envSecretEditorTitle: '.env secret editor (isolated)',
  pluginBrowserTitle: 'Plugin browser',
  pluginToggleHint: 'Space toggle · i detail · r remove · a marketplace',
  exportPdfWriting: 'Writing PDF…',
  exportPdfDone: (path) => `PDF saved: ${path}`,
  historySearchTitle: 'History search',
};

/**
 * Resolve the current locale from UMMAYA_TUI_LOCALE on every call so that
 * /lang ko|en (which mutates process.env at runtime) takes effect on the
 * next render without a process restart. Per Codex review on PR #1847.
 */
function currentLocale(): 'ko' | 'en' {
  return process.env['UMMAYA_TUI_LOCALE'] === 'en' ? 'en' : 'ko';
}

/** Backwards-compat default export — equals KO unless UMMAYA_TUI_LOCALE=en at module load. */
export const uiL2I18n: UiL2Bundle = currentLocale() === 'en' ? EN : KO;

/**
 * Hook returning the active i18n bundle. Reads UMMAYA_TUI_LOCALE on every
 * call so /lang ko|en applies on the next render frame. Components that
 * already capture this value into closures (event handlers, useCallback
 * deps) will need to remount or re-execute the closure to pick up the
 * new locale — that is by design (FR-004 + Codex P2 fix).
 */
export function useUiL2I18n(): UiL2Bundle {
  return currentLocale() === 'en' ? EN : KO;
}

export function getUiL2I18n(locale: 'ko' | 'en'): UiL2Bundle {
  return locale === 'en' ? EN : KO;
}
