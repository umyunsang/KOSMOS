# Korean IME Strategy

Korean IME strategy for the KOSMOS TUI. See ADR-005 for the full decision rationale.

## Strategy Selector

The active IME strategy is controlled by the `KOSMOS_TUI_IME_STRATEGY` environment variable.

| Value | Behaviour |
|-------|-----------|
| `fork` (default) | Uses `@jrichman/ink@6.6.9` patched `useInput` — Korean Hangul composition works on macOS and Linux. |
| `readline` | Reserved for a future ADR revisit. Currently throws an error at hook invocation time. |

Set the variable in your shell before launching the TUI:

```sh
# Explicitly select the fork strategy (this is also the default)
export KOSMOS_TUI_IME_STRATEGY=fork
bun run tui
```

Or add it to a `.env` file in the project root (loaded by Bun automatically):

```
KOSMOS_TUI_IME_STRATEGY=fork
```

The strategy is read once at module load time and remains fixed for the lifetime of the process.

## Fork Path (Default)

When `KOSMOS_TUI_IME_STRATEGY=fork` (or the variable is unset), the TUI uses
`@jrichman/ink@6.6.9` in place of `ink@^7`. This fork patches Ink's `useInput`
hook to honour the system IME composition buffer, so that multi-step jamo
keystrokes (e.g., `ㅎ`, `ㅏ`, `ㄴ`) are assembled into a single precomposed
syllable (`한`) before being committed to the input buffer.

The fork is the same package that Gemini CLI ships in production (see
`.references/gemini-cli/package.json`). It is approximately 20 lines of diff
from upstream Ink 6.6.9, making its maintenance surface small and auditable.

The fork requires React 18 rather than React 19.2. This is an accepted
trade-off documented in ADR-005 — the KOSMOS TUI does not use any Ink 7-only
APIs or React 19-specific features that would be lost on the fork.

For more detail on the fork's input event handling, see
`tui/src/hooks/useKoreanIME.ts` and ADR-005.

## Readline Fallback (Deferred)

The `readline` strategy path is reserved for a future ADR revisit if the fork
diverges from Ink 7 upstream or becomes incompatible with a future Bun release.

At present, selecting `KOSMOS_TUI_IME_STRATEGY=readline` causes the
`useKoreanIME` hook to throw immediately at invocation time with the message:

```
KOSMOS_TUI_IME_STRATEGY=readline not yet implemented;
see docs/adr/ADR-005-korean-ime-strategy.md
```

Full implementation of the readline hybrid (replicating Ink's input state
machine over `readline.createInterface`) is explicitly deferred. Do not use
this strategy value in production until a follow-up spec ships the
implementation.

## Troubleshooting — Uncommon Terminals

### macOS

- If Korean characters do not compose (you see individual jamo like `ㅎㅏㄴ`
  instead of `한`), open `System Settings > Keyboard > Input Sources` and
  confirm that the 2벌식 Korean layout is installed and active.
- Restart your terminal after adding or changing the input source — some
  terminal emulators cache the input method at launch.
- Known-working terminals: iTerm2 4.x, Alacritty 0.13+, Ghostty 1.x.

### Linux

- If `fcitx5` or `ibus` does not surface the composition preview inside the
  TUI, export the relevant environment variables before launching:

  ```sh
  # fcitx5
  export GTK_IM_MODULE=fcitx5
  export QT_IM_MODULE=fcitx5
  export XMODIFIERS=@im=fcitx5

  # ibus
  export GTK_IM_MODULE=ibus
  export QT_IM_MODULE=ibus
  export XMODIFIERS=@im=ibus
  ```

- If you are running inside `tmux`, add the following to your `~/.tmux.conf`
  and restart the server:

  ```
  set -g default-terminal "tmux-256color"
  ```

  Additionally, confirm that the host terminal passes IME events through to
  tmux. iTerm2 and Alacritty are known good; basic `xterm` is known to suppress
  composition events.

### Windows

Windows (conhost and Windows Terminal) is not yet supported. The
`@jrichman/ink` fork has not been validated under Windows terminal emulators.
Track upstream Ink 7 parity and revisit ADR-005 once a Windows-compatible path
is confirmed.

### Last Resort

If Korean input fails on your terminal and none of the above steps help:

1. Set `KOSMOS_TUI_IME_STRATEGY=readline` to confirm you get the stub error
   message (this verifies the env var is being read correctly).
2. File a bug at the KOSMOS issue tracker with the terminal name and OS version.

## References

- Decision rationale: [`docs/adr/ADR-005-korean-ime-strategy.md`](../../docs/adr/ADR-005-korean-ime-strategy.md)
- Hook implementation: [`tui/src/hooks/useKoreanIME.ts`](../src/hooks/useKoreanIME.ts)
- Specification: [`specs/287-tui-ink-react-bun/spec.md`](../../specs/287-tui-ink-react-bun/spec.md) — US5 (Korean IME Input Module)
