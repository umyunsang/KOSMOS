# frozen_string_literal: true

cask "ummaya" do
  version "0.1.9"
  sha256 "d6cff6371c3afc3ec711ad9e5f9155eaa8857c8fe4e5d0c7c4dfff961fb1faf9"

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
