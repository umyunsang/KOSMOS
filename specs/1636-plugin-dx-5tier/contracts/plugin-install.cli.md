# Contract — `kosmos plugin install <name>` CLI

**Surface**: `tui/src/commands/plugin-install.ts` (TUI front-end) → IPC → `src/kosmos/plugins/installer.py` (backend executor).
**Trigger**: User types `/plugin install <name>` in TUI REPL OR `kosmos plugin install <name>` shell.
**Purpose**: Resolve a plugin from the catalog, verify SLSA provenance, validate manifest, register adapter into running session, append consent receipt (FR-018).

## Arguments

| Position | Name | Required | Constraints | Description |
|---|---|---|---|---|
| 1 | `<name>` | ✓ | regex `^[a-z][a-z0-9-]*$` | Catalog name; matches `CatalogEntry.name`. |

## Flags

| Flag | Default | Description |
|---|---|---|
| `--version <semver>` | latest | Pin to a specific version. |
| `--catalog <url>` | `$KOSMOS_PLUGIN_CATALOG_URL` | Override catalog index URL. |
| `--vendor-slsa-from <path>` | `$KOSMOS_PLUGIN_VENDOR_ROOT/slsa-verifier/<platform>/slsa-verifier` | Override slsa-verifier binary path. |
| `--yes / -y` | false | Skip the consent confirmation prompt (CI / unattended). |
| `--dry-run` | false | Verify everything but do not write anything to disk. |

## Phases (Ink progress overlay shows each)

```
1. 📡 카탈로그 조회 중…
   GET <catalog_url> → resolve <name> → CatalogEntry → CatalogVersion
2. 📦 번들 다운로드 중…
   GET bundle_url → ~/.kosmos/cache/plugin-bundles/<plugin_id>-<sha>.tar.gz
   verify SHA-256 == CatalogVersion.bundle_sha256
3. 🔐 SLSA 서명 검증 중…
   GET provenance_url → ~/.kosmos/cache/plugin-bundles/<plugin_id>-<sha>.intoto.jsonl
   subprocess: slsa-verifier verify-artifact \
                  --provenance-path <prov> \
                  --source-uri github.com/kosmos-plugin-store/kosmos-plugin-<name> \
                  <bundle.tar.gz>
   exit code 0 expected
4. 🧪 매니페스트 검증 중…
   tar -xzf <bundle> manifest.yaml → PluginManifest.model_validate(...)
   all 50 review-checklist items re-applied locally (mirror of plugin-validation.yml)
5. 📝 동의 확인…
   Render permission summary (Layer X · processes_pii=Y · trustee_org=Z)
   Wait for citizen confirmation unless --yes
6. 🔄 등록 + BM25 색인 중…
   Move bundle contents → ~/.kosmos/memdir/user/plugins/<plugin_id>/
   Backend: registry.register_plugin_adapter(manifest)
            → ToolRegistry.register(adapter)
            → BM25Index.add_or_update(adapter.tool_id, search_hints)
            → emit OTEL span kosmos.plugin.install w/ kosmos.plugin.id=<id>
7. 📜 동의 영수증 기록 중…
   PluginConsentReceipt(action_type="plugin_install", ...) → ~/.kosmos/memdir/user/consent/<receipt_id>.json
8. ✓ 설치 완료. 영수증 ID: rcpt-<id>
   추천: lookup(search="<korean_keyword>") 호출하면 즉시 surface 됩니다.
```

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Success. Plugin installed and discoverable. |
| 1 | Catalog resolution failed (name not found, network error). |
| 2 | Bundle SHA-256 mismatch. |
| 3 | SLSA verification failed (`slsa-verifier` exit ≠ 0). |
| 4 | Manifest validation failed (one or more checklist items rejected — list shown). |
| 5 | Citizen rejected consent. |
| 6 | I/O error during bundle extraction or registry registration. |
| 7 | Backend IPC unavailable. |

## SLSA verification — failure modes (R-3)

The contract requires `slsa-verifier verify-artifact` to succeed. Specific failure subtypes shown in the error overlay:
- "provenance not signed by GitHub Actions OIDC" → exit 3, message points at the project's release workflow.
- "source-uri mismatch" → exit 3, message shows expected vs got.
- "binary not found" (vendored slsa-verifier missing for this platform) → exit 7 with bootstrap instruction.

`KOSMOS_PLUGIN_SLSA_SKIP=1` (env) bypasses verification entirely (dev only). Doing so writes `slsa_verification: "skipped"` to the consent receipt, AND the citizen sees a red banner "⚠️  서명 검증 우회됨 (개발 모드)". CI tests assert the banner appears.

## IPC envelope (Spec 032 extension)

New frame variant added to the 19-arm discriminated union:

```typescript
type PluginOpFrame =
  | { type: "plugin_op_request",   correlation_id: string, op: "install" | "uninstall" | "list", name?: string, version?: string, dry_run?: boolean }
  | { type: "plugin_op_progress",  correlation_id: string, phase: 1|2|3|4|5|6|7, message_ko: string, message_en: string }
  | { type: "plugin_op_complete",  correlation_id: string, result: "success" | "failure", exit_code: number, receipt_id?: string }
```

This becomes a 20th arm. The Spec 032 `frame.schema.json` must be updated; the SHA-256 hash emitted as the `kosmos.ipc.schema.hash` OTEL attribute changes accordingly. Contract change tracked in this Epic; Spec 032 schema bump documented in the eventual PR description.

## Negative-path test cases

1. `<name>` not in catalog → exit 1, error mentions catalog URL.
2. Tampered bundle (sha mismatch) → exit 2.
3. Tampered provenance (slsa-verifier exit 1) → exit 3.
4. Manifest with intentional Q3-V1-NO-EXTRA violation → exit 4 with item id in error.
5. Citizen presses N at consent → exit 5; nothing written; no consent receipt.
6. `--dry-run` succeeds but creates zero files; assert no `~/.kosmos/memdir/user/plugins/<plugin_id>/` exists after.
7. `KOSMOS_PLUGIN_SLSA_SKIP=1` → SLSA phase skipped; consent receipt records `slsa_verification: "skipped"`; red banner shown.

## Non-goals

- Not a publish path — only consume.
- Not a marketplace browser — #1820.
- Not a hot-reload (changes to installed plugin source require restart) — permanent OOS per spec.
