// SPDX-License-Identifier: Apache-2.0
// Spec 288 · Barrel re-exports for the keybindings module.
//
// Foundational ports (registry, resolver, accessibilityAnnouncer) land via
// Lead's Phase 2 (T004..T025). Team C's deliverables surface here so the
// downstream consumers (`tui/src/main.tsx`, action handlers, overlay) get
// a single import path.

export * from './types'
export { parseChord, tryParseChord } from './chord'
export {
  DEFAULT_BINDINGS,
  defaultBindingsByAction,
  MODE_CYCLE_DEFAULT_CHORD,
} from './defaultBindings'
export {
  loadUserBindings,
  defaultOverridePath,
  type LoaderResult,
  type LoaderWarning,
  type LoadUserBindingsOptions,
} from './loadUserBindings'
export {
  generateKeybindingsTemplate,
  dumpTier1Catalogue,
  renderTier1CatalogueText,
  type CatalogueLine,
} from './template'
export {
  matchesHistoryQuery,
  filterHistoryEntries,
  toChoseongString,
  extractChoseong,
} from './hangulSearch'
export {
  openHistorySearchOverlay,
  selectHistoryEntry,
  cancelHistorySearch,
  filterByConsentScope,
  type HistoryEntry,
  type ConsentState,
  type HistorySearchActionInput,
  type OverlayOpenRequest,
  type SelectionResult,
  type CancelResult,
} from './actions/historySearch'
export {
  createAgentInterruptController,
  ARM_WINDOW_MS,
  type AgentInterruptController,
  type AgentInterruptDeps,
  type AgentInterruptOutcome,
} from './actions/agentInterrupt'
export {
  cancelDraft,
  type DraftCancelDeps,
  type DraftCancelOutcome,
} from './actions/draftCancel'
export {
  createHistoryNavigator,
  type HistoryNavigator,
  type HistoryNavigatorDeps,
  type HistoryNavigationEntry,
  type HistoryConsentState,
  type HistoryPrevOutcome,
  type HistoryNextOutcome,
} from './actions/historyNavigate'
export {
  buildChordEvent,
  lookupChord,
  type InkKeyLike,
} from './match'
export {
  RESERVED_ACTIONS,
  isReservedAction,
  isReservedChord,
} from './reservedShortcuts'
export {
  validateEntries,
  RegistryInvariantError,
} from './validate'
export { buildRegistry, type BuildRegistryOptions } from './registry'
export {
  resolve,
  drainBindingSpans,
  type ResolveContext,
  type SpanEmitter,
  type BindingSpanAttributes,
  type ImeStateLike,
} from './resolver'
export {
  createAccessibilityAnnouncer,
  type BufferedAnnouncer,
  type AnnounceRecord,
  type AccessibilityAnnouncerOptions,
} from './accessibilityAnnouncer'
export {
  KeybindingContext as KeybindingReactContext,
  useKeybindingSurfaces,
  type KeybindingSurfaces,
} from './KeybindingContext'
export {
  KeybindingProviderSetup,
  type KeybindingProviderSetupProps,
} from './KeybindingProviderSetup'
export {
  useKeybinding,
  dispatchAction,
  registerHandlers,
  type ActionHandlers,
} from './useKeybinding'
export { useShortcutDisplay } from './useShortcutDisplay'
