# Family Partition — 389 CC component files

**Source**: `find .references/claude-code-sourcemap/restored-src/src/components -type f \( -name "*.tsx" -o -name "*.ts" \) | sort`
**Sourcemap commit**: `a8a678c`
**Enumerated at**: 2026-04-20 (KOSMOS HEAD `34c48f4`)
**Invariant I3**: sum of per-family counts == 389.

## 1 · Subdirectory families (31 families, 276 files)

| Family | Files | Classification group (Phase 3 teammate) |
|---|---:|---|
| `design-system` | 16 | Team A — design-system / chrome |
| `ui` | 3 | Team A — design-system / chrome |
| `Spinner` | 12 | Team A — design-system / chrome |
| `LogoV2` | 15 | Team A — design-system / chrome |
| `HighlightedCode` | 1 | Team A — design-system / chrome |
| `StructuredDiff` | 2 | Team A — design-system / chrome |
| `diff` | 3 | Team A — design-system / chrome |
| `CustomSelect` | 10 | Team A — design-system / chrome |
| `messages` | 41 | Team B — conversation / IO |
| `PromptInput` | 21 | Team B — conversation / IO |
| `HelpV2` | 3 | Team B — conversation / IO |
| `hooks` | 6 | Team B — conversation / IO |
| `memory` | 2 | Team B — conversation / IO |
| `shell` | 4 | Team B — conversation / IO |
| `ClaudeCodeHint` | 1 | Team B — conversation / IO |
| `permissions` | 51 | Team C — permission / safety |
| `TrustDialog` | 2 | Team C — permission / safety |
| `ManagedSettingsSecurityDialog` | 2 | Team C — permission / safety |
| `sandbox` | 5 | Team C — permission / safety |
| `Passes` | 1 | Team C — permission / safety |
| `agents` | 26 | Team C — permission / safety |
| `teams` | 2 | Team C — permission / safety |
| `grove` | 1 | Team C — permission / safety |
| `mcp` | 13 | Team D — tooling / integration |
| `skills` | 1 | Team D — tooling / integration |
| `tasks` | 12 | Team D — tooling / integration |
| `wizard` | 5 | Team D — tooling / integration |
| `DesktopUpsell` | 1 | Team D — tooling / integration |
| `FeedbackSurvey` | 9 | Team D — tooling / integration |
| `LspRecommendation` | 1 | Team D — tooling / integration |
| `Settings` | 4 | Team D — tooling / integration |
| **Subtotal (subdirs)** | **276** | — |

## 2 · Root-level semantic bins (6 bins, 113 files)

Per `catalog-row-schema.md §2.1`. Authored by Lead (T014).

### `root.logo-wordmark` (3 files)

- `FastIcon.tsx`
- `PrBadge.tsx`
- `TagTabs.tsx`

### `root.dialogs` (40 files — citizen- and dev-facing modal surfaces)

- `ApproveApiKey.tsx`
- `AutoModeOptInDialog.tsx`
- `BridgeDialog.tsx`
- `BypassPermissionsModeDialog.tsx`
- `ChannelDowngradeDialog.tsx`
- `ClaudeMdExternalIncludesDialog.tsx`
- `CostThresholdDialog.tsx`
- `DesktopHandoff.tsx`
- `DevChannelsDialog.tsx`
- `ExitFlow.tsx`
- `ExportDialog.tsx`
- `GlobalSearchDialog.tsx`
- `HistorySearchDialog.tsx`
- `IdeAutoConnectDialog.tsx`
- `IdeOnboardingDialog.tsx`
- `IdleReturnDialog.tsx`
- `InvalidConfigDialog.tsx`
- `InvalidSettingsDialog.tsx`
- `LanguagePicker.tsx`
- `LogSelector.tsx`
- `MCPServerApprovalDialog.tsx`
- `MCPServerDesktopImportDialog.tsx`
- `MCPServerDialogCopy.tsx`
- `MCPServerMultiselectDialog.tsx`
- `MessageSelector.tsx`
- `ModelPicker.tsx`
- `OutputStylePicker.tsx`
- `QuickOpenDialog.tsx`
- `RemoteEnvironmentDialog.tsx`
- `SearchBox.tsx`
- `ShowInIDEPrompt.tsx`
- `ThemePicker.tsx`
- `WorkflowMultiselectDialog.tsx`
- `WorktreeExitDialog.tsx`
- `TeleportRepoMismatchDialog.tsx`
- `SessionPreview.tsx`
- `SkillImprovementSurvey.tsx`
- `KeybindingWarnings.tsx`
- `Feedback.tsx`
- `ClickableImageRef.tsx`

### `root.shortcuts` (4 files)

- `ConfigurableShortcutHint.tsx`
- `CtrlOToExpand.tsx`
- `PressEnterToContinue.tsx`
- `ScrollKeybindingHandler.tsx`

### `root.dev-ui` (14 files — developer/diagnostic surfaces, mostly DISCARD per ADR-006 Part D-1)

- `AutoUpdater.tsx`
- `AutoUpdaterWrapper.tsx`
- `NativeAutoUpdater.tsx`
- `PackageManagerAutoUpdater.tsx`
- `AwsAuthStatusBox.tsx`
- `ConsoleOAuthFlow.tsx`
- `DevBar.tsx`
- `DiagnosticsDisplay.tsx`
- `IdeStatusIndicator.tsx`
- `MemoryUsageIndicator.tsx`
- `RemoteCallout.tsx`
- `ClaudeInChromeOnboarding.tsx`
- `SentryErrorBoundary.ts`
- `VimTextInput.tsx`

### `root.onboarding` (1 file — citizen-facing entry point)

- `Onboarding.tsx`

### `root.misc` (51 files — shell, messages, status, teleport, other root surfaces)

- `AgentProgressLine.tsx`
- `App.tsx`
- `BaseTextInput.tsx`
- `BashModeProgress.tsx`
- `CompactSummary.tsx`
- `ContextSuggestions.tsx`
- `ContextVisualization.tsx`
- `CoordinatorAgentStatus.tsx`
- `EffortCallout.tsx`
- `EffortIndicator.ts`
- `FallbackToolUseErrorMessage.tsx`
- `FallbackToolUseRejectedMessage.tsx`
- `FileEditToolDiff.tsx`
- `FileEditToolUpdatedMessage.tsx`
- `FileEditToolUseRejectedMessage.tsx`
- `FilePathLink.tsx`
- `FullscreenLayout.tsx`
- `HighlightedCode.tsx`
- `InterruptedByUser.tsx`
- `Markdown.tsx`
- `MarkdownTable.tsx`
- `Message.tsx`
- `messageActions.tsx`
- `MessageModel.tsx`
- `MessageResponse.tsx`
- `MessageRow.tsx`
- `Messages.tsx`
- `MessageTimestamp.tsx`
- `NotebookEditToolUseRejectedMessage.tsx`
- `OffscreenFreeze.tsx`
- `ResumeTask.tsx`
- `SandboxViolationExpandedView.tsx`
- `SessionBackgroundHint.tsx`
- `Spinner.tsx`
- `Stats.tsx`
- `StatusLine.tsx`
- `StatusNotices.tsx`
- `StructuredDiff.tsx`
- `StructuredDiffList.tsx`
- `TaskListV2.tsx`
- `TeammateViewHeader.tsx`
- `TeleportError.tsx`
- `TeleportProgress.tsx`
- `TeleportResumeWrapper.tsx`
- `TeleportStash.tsx`
- `TextInput.tsx`
- `ThinkingToggle.tsx`
- `TokenWarning.tsx`
- `ToolUseLoader.tsx`
- `ValidationErrorsList.tsx`
- `VirtualMessageList.tsx`

### Root subtotal: 3 + 40 + 4 + 14 + 1 + 51 = **113** ✓

## 3 · Grand total

276 (subdirs) + 113 (root) = **389** ✓ (matches `wc -l cc-file-list.txt`).

## 4 · Phase 3 team assignment recap

| Team | Families | File count |
|---|---|---:|
| A — design-system / chrome | design-system, ui, Spinner, LogoV2, HighlightedCode, StructuredDiff, diff, CustomSelect | 62 |
| B — conversation / IO | messages, PromptInput, HelpV2, hooks, memory, shell, ClaudeCodeHint | 78 |
| C — permission / safety | permissions, TrustDialog, ManagedSettingsSecurityDialog, sandbox, Passes, agents, teams, grove | 90 |
| D — tooling / integration | mcp, skills, tasks, wizard, DesktopUpsell, FeedbackSurvey, LspRecommendation, Settings | 46 |
| **Subdir subtotal** | — | **276** |
| Lead (T014) — root bins | 6 semantic bins | 113 |
| **Grand total** | — | **389** |
