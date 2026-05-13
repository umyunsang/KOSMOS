#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0

import { readFileSync } from 'node:fs'

const reportPath = process.argv[2]
if (!reportPath) {
  throw new Error('Usage: scripts/check-npm-package.mjs <npm-pack-json>')
}

const report = JSON.parse(readFileSync(reportPath, 'utf8'))
const pack = Array.isArray(report) ? report[0] : report
if (!pack || !Array.isArray(pack.files)) {
  throw new Error('npm pack report must contain a files array')
}

const maxPackedBytes = Number(process.env.UMMAYA_NPM_MAX_PACKED_BYTES ?? 15_000_000)
const maxUnpackedBytes = Number(process.env.UMMAYA_NPM_MAX_UNPACKED_BYTES ?? 70_000_000)
const maxEntries = Number(process.env.UMMAYA_NPM_MAX_ENTRIES ?? 2_700)

const files = pack.files.map((entry) => entry.path)
const fileSet = new Set(files)

const required = [
  'bin/ummaya',
  'package.json',
  'bun.lock',
  'npm-shrinkwrap.json',
  'README.md',
  'LICENSE',
  'assets/ummaya-banner-dark.svg',
  'assets/ummaya-banner-light.svg',
  'assets/ummaya-logo.svg',
  'pyproject.toml',
  'uv.lock',
  'src/ummaya/__init__.py',
  'prompts/manifest.yaml',
  'tui/src/entrypoints/cli.tsx',
  'tui/src/stubs/macro-preload.ts',
  'docs/plugins/security-review.md',
  'tests/fixtures/plugin_validation/checklist_manifest.yaml',
]

const deny = [
  /(^|\/)\.env($|[./])/,
  /^\.github\//,
  /^\.references\//,
  /^\.specify\//,
  /(^|\/)secrets(\/|$)/,
  /^specs\//,
  /(^|\/)node_modules(\/|$)/,
  /(^|\/)\.venv(\/|$)/,
  /(^|\/)dist(\/|$)/,
  /(^|\/)coverage\.xml$/,
  /(^|\/)\.DS_Store$/,
  /(^|\/)__pycache__(\/|$)/,
  /(^|\/)__tests__(\/|$)/,
  /\.(test|snap)\.(ts|tsx|js|jsx|snap)$/,
]

const missing = required.filter((path) => !fileSet.has(path))
if (missing.length > 0) {
  throw new Error(`npm package missing required paths:\n${missing.join('\n')}`)
}

const forbidden = files.filter((path) => deny.some((pattern) => pattern.test(path)))
if (forbidden.length > 0) {
  throw new Error(`npm package contains forbidden paths:\n${forbidden.join('\n')}`)
}

if (pack.size > maxPackedBytes) {
  throw new Error(`npm package packed size ${pack.size} exceeds ${maxPackedBytes}`)
}
if (pack.unpackedSize > maxUnpackedBytes) {
  throw new Error(
    `npm package unpacked size ${pack.unpackedSize} exceeds ${maxUnpackedBytes}`,
  )
}
if (files.length > maxEntries) {
  throw new Error(`npm package entry count ${files.length} exceeds ${maxEntries}`)
}

console.log(
  `check-npm-package: clean (${pack.size} packed bytes, ${pack.unpackedSize} unpacked bytes, ${files.length} files)`,
)
