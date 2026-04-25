# /plugin slash command — visual review summary

# `/plugin`

**Acknowledgement**:
```
사용법: /plugin <install|list|uninstall|pipa-text> [...]
```

**Plugin frames emitted**: 0

# `/plugin install seoul-subway`

**Acknowledgement**:
```
🔄 seoul-subway 플러그인 설치 시작...
```

**Plugin frames emitted**: 1
```json
{
  "kind": "plugin_op",
  "version": "1.0",
  "session_id": "",
  "correlation_id": "e52b6be4-ad62-4181-9f3f-b7f8615b15aa",
  "ts": "2026-04-25T16:29:40.574Z",
  "role": "tui",
  "op": "request",
  "request_op": "install",
  "name": "seoul-subway",
  "requested_version": null,
  "dry_run": false
}
```

# `/plugin install seoul-subway --version 1.2.0 --dry-run`

**Acknowledgement**:
```
🔄 seoul-subway 플러그인 설치 시작... (dry-run)
```

**Plugin frames emitted**: 1
```json
{
  "kind": "plugin_op",
  "version": "1.0",
  "session_id": "",
  "correlation_id": "5bf5457a-75e4-4ae1-a133-3fe0995c882a",
  "ts": "2026-04-25T16:29:40.575Z",
  "role": "tui",
  "op": "request",
  "request_op": "install",
  "name": "seoul-subway",
  "requested_version": "1.2.0",
  "dry_run": true
}
```

# `/plugin list`

**Acknowledgement**:
```
📋 설치된 플러그인 목록 조회 중...
```

**Plugin frames emitted**: 1
```json
{
  "kind": "plugin_op",
  "version": "1.0",
  "session_id": "",
  "correlation_id": "9861ad5f-fbb3-49ad-b3b3-b27bcd91cf8d",
  "ts": "2026-04-25T16:29:40.576Z",
  "role": "tui",
  "op": "request",
  "request_op": "list"
}
```

# `/plugin uninstall seoul-subway`

**Acknowledgement**:
```
🗑️ seoul-subway 플러그인 제거 시작...
```

**Plugin frames emitted**: 1
```json
{
  "kind": "plugin_op",
  "version": "1.0",
  "session_id": "",
  "correlation_id": "fbfe2f40-1d29-4441-9d6c-6e93c2ffc5d2",
  "ts": "2026-04-25T16:29:40.578Z",
  "role": "tui",
  "op": "request",
  "request_op": "uninstall",
  "name": "seoul-subway"
}
```

# `/plugin pipa-text`

**Acknowledgement**:
```
PIPA §26 trustee acknowledgment canonical SHA-256:
  434074581cab35241c70f9b6e2191a7220fdac67aa627289ea64472cb87495d4
Source: docs/plugins/security-review.md (마커 사이 텍스트)
manifest.yaml 의 acknowledgment_sha256 필드에 위 값을 그대로 기록하세요.
```

**Plugin frames emitted**: 0

# `/plugin reinstall foo`

**Acknowledgement**:
```
알 수 없는 subcommand: reinstall
사용법: /plugin <install|list|uninstall|pipa-text> [...]
```

**Plugin frames emitted**: 0
