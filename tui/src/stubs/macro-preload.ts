// [P0 reconstructed · Bun MACRO shim]
// CC 2.1.88 uses `MACRO.*` build-time constants that Bun's bundler inlines.
// Without a build step, those references throw `ReferenceError: MACRO is not
// defined`. This preload script injects a global `MACRO` object with plausible
// defaults so the module-load phase succeeds and the splash renders.
//
// Referenced from `bunfig.toml` `preload = ["./src/stubs/macro-preload.ts"]`.
/* eslint-disable @typescript-eslint/no-explicit-any */

// Shim React.useEffectEvent — experimental hook used by CC but not dispatched by Ink.
// We alias it to useCallback, which is functionally close (latest-closure semantics
// differ but acceptable for baseline render).
// Preload runs before any import, so we patch the React module cache eagerly.
import React from 'react'
if (typeof (React as any).useEffectEvent !== 'function') {
  ;(React as any).useEffectEvent = (React as any).useCallback ?? ((fn: any) => fn)
}

;(globalThis as any).MACRO = {
  VERSION: '2.1.88-kosmos',
  VERSION_CHANGELOG: 'https://github.com/umyunsang/KOSMOS/releases',
  BUILD_TIME: new Date(0).toISOString(),
  FEEDBACK_CHANNEL: 'https://github.com/umyunsang/KOSMOS/issues',
  ISSUES_EXPLAINER: 'Please open a GitHub issue at https://github.com/umyunsang/KOSMOS/issues',
  PACKAGE_URL: 'https://github.com/umyunsang/KOSMOS',
  NATIVE_PACKAGE_URL: 'https://github.com/umyunsang/KOSMOS',
}
