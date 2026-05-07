# frozen_string_literal: true

cask "ummaya" do
  version "0.1.0"
  sha256 "6fff4257b4f58d8bd23f3ce55c13e7d4772e9116a39a324d500a3035592c9662"

  url "https://registry.npmjs.org/ummaya/-/ummaya-#{version}.tgz"
  name "UMMAYA"
  desc "Conversational multi-agent harness for Korean public-service channels"
  homepage "https://github.com/umyunsang/UMMAYA"

  depends_on formula: "oven-sh/bun/bun"
  depends_on formula: "uv"

  postflight do |c|
    wrapper = HOMEBREW_PREFIX/"bin/ummaya"
    wrapper.write <<~SH
      #!/bin/bash
      export PATH="#{HOMEBREW_PREFIX}/opt/bun/bin:#{HOMEBREW_PREFIX}/opt/uv/bin:$PATH"
      exec "#{HOMEBREW_PREFIX}/opt/bun/bin/bun" "#{c.staged_path}/package/bin/ummaya" "$@"
    SH
    FileUtils.chmod 0755, wrapper
  end

  uninstall delete: "#{HOMEBREW_PREFIX}/bin/ummaya"

  zap trash: "~/.ummaya"
end
