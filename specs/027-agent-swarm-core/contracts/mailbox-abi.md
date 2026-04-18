# Mailbox ABI — On-Disk Layout + fsync Ordering Contract

**Spec**: [spec.md](../spec.md) · **Plan**: [plan.md](../plan.md) · **Data model**: [data-model.md](../data-model.md)

This document is the binding contract for the `FileMailbox` on-disk format. It is referenced by FR-014..FR-022 and exists so that (a) a future Redis backend (#21, Phase 3) can preserve the same semantics and (b) operators debugging a crash can read the mailbox without invoking KOSMOS code.

---

## 1. Directory layout

```
$KOSMOS_AGENT_MAILBOX_ROOT/                # default: ~/.kosmos/mailbox, mode 0o700
└── <session_id>/                          # UUID4, mode 0o700
    ├── coordinator/                       # mode 0o700; sender directory
    │   ├── <message_id>.json              # mode 0o600; payload file
    │   ├── <message_id>.json.consumed     # mode 0o600; zero-byte marker
    │   └── ...
    └── worker-<role>-<uuid4>/             # mode 0o700; one per live worker
        ├── <message_id>.json
        ├── <message_id>.json.consumed
        └── ...
```

**Invariants**:

- Every directory is created with mode `0o700` (user-only). Every file with mode `0o600`.
- A `<message_id>.json.consumed` marker MAY exist only if the sibling `<message_id>.json` exists.
- The reverse is not true: a `<message_id>.json` without a `.consumed` marker is an "unread" message and is eligible for `replay_unread`.
- `<message_id>` is the `id` field (UUID4) of the serialised `AgentMessage`.

---

## 2. Write ordering (send)

The sequence for `Mailbox.send(message)`:

```python
# Pseudocode — real impl in src/kosmos/agents/mailbox/file_mailbox.py
tmp = sender_dir / f"{message.id}.json.tmp"
final = sender_dir / f"{message.id}.json"

# Step A — overflow check
if count_json_files(session_dir) >= settings.agent_mailbox_max_messages:
    raise MailboxOverflowError(...)

# Step B — write payload to temp file
fd = os.open(tmp, O_WRONLY | O_CREAT | O_EXCL, 0o600)
os.write(fd, message.model_dump_json().encode("utf-8"))
os.fsync(fd)
os.close(fd)

# Step C — atomic rename into place
os.rename(tmp, final)

# Step D — fsync the sender directory so the directory entry survives
dir_fd = os.open(sender_dir, O_DIRECTORY | O_RDONLY)
os.fsync(dir_fd)
os.close(dir_fd)

# Only now does send() return
```

**Contractual consequences**:

- **At-least-once** — a successfully returned `send` guarantees the message survives kernel panic, process kill, and power loss.
- **Crash before Step D** — the payload file exists but may be invisible after reboot; treated as "message never sent" and caller may retry. Caller MUST either retry on timeout or accept at-most-once-under-uncoordinated-crash.
- **Crash during Step B (partial write)** — the `.tmp` file is discarded on reboot; `replay_unread` ignores `.tmp` files (FR-020).
- **Crash after Step C, before Step D** — filesystem dependent. ext4 / xfs with default options typically preserve the rename; macOS APFS typically preserves it. The contract is: replay-on-restart MUST be idempotent regardless.

---

## 3. Consumption marker ordering (ack)

After a reader (`Coordinator.receive` or `Worker.receive`) successfully processes a message, it writes the `.consumed` marker:

```python
tmp = sender_dir / f"{message.id}.json.consumed.tmp"
final = sender_dir / f"{message.id}.json.consumed"

fd = os.open(tmp, O_WRONLY | O_CREAT | O_EXCL, 0o600)
os.fsync(fd)
os.close(fd)
os.rename(tmp, final)

dir_fd = os.open(sender_dir, O_DIRECTORY | O_RDONLY)
os.fsync(dir_fd)
os.close(dir_fd)
```

**Contractual consequences**:

- If the process crashes AFTER processing but BEFORE writing the marker, the message WILL be re-delivered on restart. Callers MUST be idempotent (the coordinator's duplicate-result handling in spec Edge Cases row 3 is the realisation).
- The marker contains no data. Its existence is the entire signal.

---

## 4. Replay algorithm

`Mailbox.replay_unread(recipient)` executes:

```
for sender_dir in sorted(session_dir.iterdir()):         # cross-sender order = alphabetical
    messages = []
    for path in sorted(sender_dir.iterdir()):            # per-sender FIFO = filename sort
        if path.suffix != ".json":
            continue
        if (path.parent / f"{path.name}.consumed").exists():
            continue
        try:
            message = AgentMessage.model_validate_json(path.read_bytes())
        except (ValueError, pydantic.ValidationError):
            logger.warning("skipping corrupt mailbox file: %s", path)   # FR-020
            continue
        if message.recipient != recipient:
            continue                                     # FR-025 enforcement
        messages.append(message)
    for m in messages:
        yield m
```

**Ordering contract** (FR-018):

- **Per-sender FIFO** — guaranteed because filenames are UUID4 random; BUT to guarantee FIFO we append a monotonic timestamp prefix at write time. Actual filename format: `<timestamp_ns>-<uuid4>.json` so alphabetical sort == write-order sort.
- **Cross-sender** — no guarantee; currently alphabetical by sender directory name.

**Note**: The data-model.md and JSON Schema describe the on-wire shape (`{id, sender, recipient, msg_type, payload, timestamp, correlation_id}`). The filename prefix carries redundant timing information to support fast FIFO replay without parsing every file.

---

## 5. Overflow handling (FR-021)

Per-session message cap = `KOSMOS_AGENT_MAILBOX_MAX_MESSAGES` (default 1000, clamped `[100, 10000]`).

On every `send`:

```
count = number of *.json files (excluding .consumed markers) across all sender dirs
         within this session_dir
if count >= cap:
    raise MailboxOverflowError(f"session {session_id} at {count}/{cap} messages")
```

No silent drop. No retry. No prune. The caller (Coordinator or Worker) decides what to do; currently the answer is "fail the session and surface the error to the citizen."

---

## 6. Security

- Permissions `0o700` / `0o600` — readable only by the user running KOSMOS.
- Message bodies may contain citizen-identifying data (PIPA concern). Operators MUST NOT copy `$KOSMOS_AGENT_MAILBOX_ROOT` to shared storage. The directory is NEVER backed up by KOSMOS itself.
- `KOSMOS_AGENT_MAILBOX_ROOT` MUST be an absolute path under a writable user-owned directory; relative paths are rejected by `KosmosSettings` validation.

---

## 7. Observability

Every `send` emits one `gen_ai.agent.mailbox.message` span with:

| Attribute | Value |
|---|---|
| `kosmos.agent.mailbox.msg_type` | one of `task`/`result`/`error`/`permission_request`/`permission_response`/`cancel` |
| `kosmos.agent.mailbox.correlation_id` | `AgentMessage.correlation_id` (or empty) |
| `kosmos.agent.mailbox.sender` | `AgentMessage.sender` |
| `kosmos.agent.mailbox.recipient` | `AgentMessage.recipient` |

The message body itself is NEVER included as a span attribute (PIPA — no PII in telemetry).

---

## 8. Backend substitution (Phase 3 / #21)

Any future `RedisStreamsMailbox` MUST preserve:

- At-least-once delivery on `send`.
- Per-sender FIFO on `receive` and `replay_unread`.
- Strict routing by `recipient`.
- Overflow at `agent_mailbox_max_messages` with `MailboxOverflowError`.
- The same `AgentMessage` schema (see `agent-message.schema.json`).
- The same observability attributes (see § 7).

The on-disk layout in §1 is NOT contractual for a non-file backend; only the Python `Mailbox` ABC is.
