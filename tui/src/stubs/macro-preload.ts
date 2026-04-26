/// <reference types="bun-types" />
// [P0 reconstructed · Bun MACRO shim + TTY shim + useEffectEvent polyfill]
// CC 2.1.88 uses `MACRO.*` build-time constants that Bun's bundler would
// normally inline. Without a build step, those references throw
// `ReferenceError: MACRO is not defined`. This preload script injects a
// global `MACRO` object, a TTY detection shim, and a `useEffectEvent` fallback
// so the module-load phase succeeds and the splash renders.
//
// Referenced from `bunfig.toml` `preload = ["./src/stubs/macro-preload.ts"]`.
/* eslint-disable @typescript-eslint/no-explicit-any */

// ═══════════════════════════════════════════════════════════════════════
// bun:bundle virtual module plugin
// Bun's default resolver treats `bun:` as a reserved built-in namespace and
// ignores tsconfig paths for it. We register a Bun plugin that intercepts
// imports of `bun:bundle` at runtime and routes them to our stub file.
// ═══════════════════════════════════════════════════════════════════════
try {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const bunGlobal = (globalThis as any).Bun
  if (bunGlobal && typeof bunGlobal.plugin === 'function') {
    bunGlobal.plugin({
      name: 'kosmos-bun-bundle-shim',
      setup(build: {
        onResolve: (
          opts: { filter: RegExp },
          cb: (args: { path: string }) => { path: string } | undefined,
        ) => void
      }) {
        build.onResolve({ filter: /^bun:bundle$/ }, () => ({
          path: new URL('./bun-bundle.ts', import.meta.url).pathname,
        }))
      },
    })
  }
} catch {
  /* Bun plugin API not available — tsconfig paths will still cover tsc */
}

// ═══════════════════════════════════════════════════════════════════════
// Bun MACRO.* build-time constants
// ═══════════════════════════════════════════════════════════════════════
// KOSMOS version is sourced from tui/package.json — the single source of
// truth. Bun supports native JSON imports, so editing package.json (manually
// or via `npm version` / `bun pm version`) is the only step required to
// bump the user-visible version. The previous "2.1.88-kosmos" hardcode was
// a residue of the CC 2.1.88 source-map import; KOSMOS is a separate
// project with its own release cadence (github.com/umyunsang/KOSMOS).
//
// BUILD_TIME is injected from the env var KOSMOS_BUILD_TIME at runtime
// (set by the packaging step). When unset (e.g. local dev) we fall back to
// the deterministic epoch-zero ISO string so reproducible builds stay
// byte-stable across machines.
import pkg from '../../package.json' with { type: 'json' }

;(globalThis as any).MACRO = {
  VERSION: pkg.version,
  VERSION_CHANGELOG: 'https://github.com/umyunsang/KOSMOS/releases',
  BUILD_TIME: process.env.KOSMOS_BUILD_TIME ?? new Date(0).toISOString(),
  FEEDBACK_CHANNEL: 'https://github.com/umyunsang/KOSMOS/issues',
  ISSUES_EXPLAINER:
    'Please open a GitHub issue at https://github.com/umyunsang/KOSMOS/issues',
  PACKAGE_URL: 'https://github.com/umyunsang/KOSMOS',
  NATIVE_PACKAGE_URL: 'https://github.com/umyunsang/KOSMOS',
}

// ═══════════════════════════════════════════════════════════════════════
// TTY detection shim
// Bun v1.3 reports `process.{stdin,stdout,stderr}.isTTY === undefined` by
// default, which makes CC evaluate `!process.stdout.isTTY` as `true` and
// switch to `--print` mode even inside iTerm2. We check the real signal
// (`tty.isatty(fd)`) and force the flag so CC routes to the interactive REPL.
// ═══════════════════════════════════════════════════════════════════════
try {
  const tty = require('node:tty')
  for (const fd of [0, 1, 2]) {
    if (tty.isatty(fd)) {
      const stream =
        fd === 0 ? process.stdin : fd === 1 ? process.stdout : process.stderr
      try {
        Object.defineProperty(stream, 'isTTY', {
          value: true,
          configurable: true,
        })
      } catch {
        /* stream's isTTY is frozen; fallback accepted */
      }
    }
  }
} catch {
  /* node:tty not available; fall through */
}

// ═══════════════════════════════════════════════════════════════════════
// React.useEffectEvent polyfill
// Ink's react-reconciler (v0.32) does not dispatch `useEffectEvent` through
// the hook dispatcher, so CC callsites throw
// `resolveDispatcher().useEffectEvent is not a function`. useCallback is
// functionally close for the baseline — latest-closure semantics differ
// (stale closures possible) but the splash path doesn't depend on that.
// TODO(Epic #1633): replace with a real latest-closure ref+effect polyfill.
// ═══════════════════════════════════════════════════════════════════════
import React from 'react'
if (typeof (React as any).useEffectEvent !== 'function') {
  ;(React as any).useEffectEvent =
    (React as any).useCallback ?? ((fn: any) => fn)
}

// ═══════════════════════════════════════════════════════════════════════
// Debug hooks — OFF by default. Enable with `KOSMOS_DEBUG_PRELOAD=1`.
// ═══════════════════════════════════════════════════════════════════════
if (process.env.KOSMOS_DEBUG_PRELOAD === '1') {
  process.stderr.write(
    `[KOSMOS/PRELOAD] loaded, pid=${process.pid}\n` +
      `[KOSMOS/TTY] stdin=${process.stdin.isTTY} stdout=${process.stdout.isTTY} stderr=${process.stderr.isTTY}\n`,
  )
  process.on('unhandledRejection', (reason: unknown) => {
    try {
      require('fs').writeSync(
        2,
        `[KOSMOS/DEBUG] unhandledRejection: ${
          reason instanceof Error ? reason.stack || reason.message : String(reason)
        }\n`,
      )
    } catch {
      /* stderr torn down */
    }
  })
  process.on('uncaughtException', (err: Error) => {
    try {
      require('fs').writeSync(
        2,
        `[KOSMOS/DEBUG] uncaughtException: ${err.stack || err.message}\n`,
      )
    } catch {
      /* stderr torn down */
    }
  })
  process.on('beforeExit', (code: number) => {
    try {
      require('fs').writeSync(2, `[KOSMOS/DEBUG] beforeExit(${code})\n`)
    } catch {
      /* stderr torn down */
    }
  })
  process.on('exit', (code: number) => {
    try {
      require('fs').writeSync(
        2,
        `[KOSMOS/DEBUG] exit(${code}) exitCode=${process.exitCode}\n`,
      )
    } catch {
      /* stderr torn down */
    }
  })
}
