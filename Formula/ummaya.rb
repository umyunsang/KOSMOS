# typed: false
# frozen_string_literal: true

class Ummaya < Formula
  desc "Conversational multi-agent harness for Korean public-service channels"
  homepage "https://github.com/umyunsang/UMMAYA"
  url "https://registry.npmjs.org/ummaya/-/ummaya-0.1.0.tgz"
  sha256 "6fff4257b4f58d8bd23f3ce55c13e7d4772e9116a39a324d500a3035592c9662"
  license "Apache-2.0"

  depends_on "node" => :build
  depends_on "oven-sh/bun/bun"
  depends_on "uv"

  def install
    libexec.install Dir["*"]
    (bin/"ummaya").write <<~SH
      #!/bin/bash
      export PATH="#{Formula["bun"].opt_bin}:#{Formula["uv"].opt_bin}:$PATH"
      exec "#{Formula["bun"].opt_bin}/bun" "#{libexec}/bin/ummaya" "$@"
    SH
  end

  def caveats
    <<~EOS
      UMMAYA uses Bun at runtime. If Homebrew cannot resolve the Bun dependency:
        brew tap oven-sh/bun
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/ummaya --version")
  end
end
