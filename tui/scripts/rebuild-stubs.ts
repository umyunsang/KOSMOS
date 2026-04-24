#!/usr/bin/env bun
// P0 stub rebuilder — parses every `.ts/.tsx` under `src/`, resolves each
// import to an absolute repo path, and aggregates the set of named symbols
// demanded from each module. Then for every KOSMOS minimal-stub file (auto-
// generated Pass 4 marker or Proxy pattern), writes a stub with the union of
// destructured symbols so downstream consumers load cleanly.

import { readFileSync, writeFileSync } from 'node:fs'
import { Glob } from 'bun'
import { dirname, resolve } from 'node:path'

const ROOT = new URL('../', import.meta.url).pathname
const SRC = `${ROOT}src`

// Collect all source files
const files: string[] = []
const glob = new Glob('**/*.{ts,tsx}')
for await (const f of glob.scan({ cwd: SRC, followSymlinks: false })) {
  files.push(`${SRC}/${f}`)
}

// Parse imports. Regex-based but handles multi-line.
// Matches: import [type] { A, B as C, type D } from 'path'
// Also: import X, { A } from 'path'
// Also: import X from 'path' (default only — skipped for destructure collection)
const importBlock = /import\s+(?:type\s+)?(?:\*\s+as\s+\w+|(?:\w+\s*,\s*)?(?:\{[\s\S]*?\}))\s+from\s+['"]([^'"]+)['"]/g
const namedBlock = /\{([\s\S]*?)\}/

// Build: target-module-absolute-path → Set<symbol>
const demands = new Map<string, Set<string>>()

for (const file of files) {
  const src = readFileSync(file, 'utf8')
  const dir = dirname(file)
  let m: RegExpExecArray | null
  importBlock.lastIndex = 0
  while ((m = importBlock.exec(src)) !== null) {
    const raw = m[0]
    const target = m[1]

    // Resolve to absolute path (best effort)
    let resolved: string | null = null
    if (target.startsWith('./') || target.startsWith('../')) {
      resolved = resolve(dir, target)
    } else if (target.startsWith('src/')) {
      resolved = resolve(ROOT, target)
    } else {
      continue // external package
    }

    // Strip extension; try both .ts/.tsx/ /index.ts
    resolved = resolved.replace(/\.js$|\.tsx$|\.ts$/, '')

    // Extract destructured names from the { ... } block
    const bm = namedBlock.exec(raw)
    if (!bm) continue
    const body = bm[1]
    const parts = body.split(',').map((s) => s.trim())
    if (!demands.has(resolved)) demands.set(resolved, new Set())
    const set = demands.get(resolved)!
    for (const p of parts) {
      const cleaned = p
        .replace(/^type\s+/, '')
        .replace(/\s+as\s+\w+$/, '')
        .trim()
      if (/^[A-Za-z_][A-Za-z0-9_]*$/.test(cleaned)) set.add(cleaned)
    }
  }
}

// Find all stub files (P0 markers or Proxy pattern)
const stubFiles: string[] = []
for (const file of files) {
  const src = readFileSync(file, 'utf8')
  if (
    (src.includes('const __noop') && src.includes('Proxy')) ||
    src.includes('[P0 reconstructed') ||
    src.includes('[P0 auto-stub') ||
    src.includes('Stage-1 NO-OP stub')
  ) {
    stubFiles.push(file)
  }
}

let rebuilt = 0
let preserved = 0

for (const stubFile of stubFiles) {
  // Derive possible resolved paths for this stub (drop .ts/.tsx, and also /index)
  const base = stubFile.replace(/\.tsx?$/, '')
  const altIndex = base.endsWith('/index') ? base : `${base}/index`
  // Collect unique symbols demanded
  const syms = new Set<string>()
  for (const [path, set] of demands) {
    if (path === base || path === altIndex) {
      for (const s of set) syms.add(s)
    }
  }

  // Preserve human-authored stubs (has real functions, not just Proxy)
  const existingSrc = readFileSync(stubFile, 'utf8')
  const hasRealImpl =
    /export const [A-Za-z_]\w* = \(/.test(existingSrc) &&
    !existingSrc.includes('__noop') &&
    !existingSrc.includes('__stub: any = new Proxy')
  if (hasRealImpl && syms.size === 0) {
    preserved++
    continue
  }

  if (syms.size === 0) {
    preserved++
    continue
  }

  // Build rebuilt content
  const lines: string[] = []
  lines.push('// [P0 reconstructed · rebuild-stubs.ts · symbol-complete stub]')
  lines.push('// Aggregated from every consumer import across src/.')
  lines.push('/* eslint-disable @typescript-eslint/no-explicit-any */')
  lines.push('')
  lines.push('const __noop = (..._args: unknown[]): any => undefined as any;')
  lines.push('const __stub: any = new Proxy(function () {} as any, {')
  lines.push('  get: (_t, p) => (p === \'then\' ? undefined : __stub),')
  lines.push('  apply: () => __stub,')
  lines.push('  construct: () => __stub,')
  lines.push('});')
  lines.push('')

  for (const s of [...syms].sort()) {
    if (/^[A-Z]/.test(s)) {
      lines.push(`export type ${s} = any;`)
      lines.push(`export const ${s}: any = __stub;`)
    } else {
      lines.push(`export const ${s}: any = __noop;`)
    }
  }

  lines.push('')
  lines.push('export default __stub;')
  writeFileSync(stubFile, lines.join('\n') + '\n')
  rebuilt++
}

console.log(`stubs processed: ${stubFiles.length}`)
console.log(`rebuilt with symbols: ${rebuilt}`)
console.log(`preserved (no demands / has real impl): ${preserved}`)
