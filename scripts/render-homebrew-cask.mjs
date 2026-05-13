#!/usr/bin/env node
// SPDX-License-Identifier: Apache-2.0

import { mkdirSync, writeFileSync } from 'node:fs'
import { dirname } from 'node:path'

const [version, sha256, outputPath = 'Casks/ummaya.rb'] = process.argv.slice(2)

if (!version || !sha256) {
  throw new Error('Usage: scripts/render-homebrew-cask.mjs <version> <sha256> [output-path]')
}

if (!/^\d+\.\d+\.\d+(-[0-9A-Za-z.-]+)?$/.test(version)) {
  throw new Error(`Invalid cask version: ${version}`)
}
if (!/^[0-9a-f]{64}$/.test(sha256)) {
  throw new Error(`Invalid SHA-256: ${sha256}`)
}

const cask = `# frozen_string_literal: true

cask "ummaya" do
  version "${version}"
  sha256 "${sha256}"

  url "https://registry.npmjs.org/ummaya/-/ummaya-#{version}.tgz",
      verified: "registry.npmjs.org/ummaya/"
  name "UMMAYA"
  desc "Conversational multi-agent harness for Korean public-service channels"
  homepage "https://github.com/umyunsang/UMMAYA"

  depends_on formula: "oven-sh/bun/bun"
  depends_on formula: "uv"

  preflight do
    install_args = ["install", "--production", "--cwd", "#{staged_path}/package"]
    if File.exist?("#{staged_path}/package/bun.lock")
      install_args << "--frozen-lockfile"
    else
      install_args << "--no-save"
    end

    system_command "#{HOMEBREW_PREFIX}/opt/bun/bin/bun",
                   args: install_args

    wrapper = staged_path/"ummaya"
    wrapper.write <<~SH
      #!/bin/bash
      export PATH="#{HOMEBREW_PREFIX}/opt/bun/bin:#{HOMEBREW_PREFIX}/opt/uv/bin:$PATH"
      exec "#{HOMEBREW_PREFIX}/opt/bun/bin/bun" "#{staged_path}/package/bin/ummaya" "$@"
    SH
    FileUtils.chmod 0755, wrapper
  end

  binary "ummaya"

  zap trash: "~/.ummaya"
end
`

mkdirSync(dirname(outputPath), { recursive: true })
writeFileSync(outputPath, cask)
console.log(`render-homebrew-cask: wrote ${outputPath}`)
