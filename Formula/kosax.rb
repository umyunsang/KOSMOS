# typed: false
# frozen_string_literal: true

class Kosax < Formula
  desc "Conversational multi-agent harness for Korean public-service channels"
  homepage "https://github.com/umyunsang/KOSAX"
  url "https://registry.npmjs.org/kosax/-/kosax-0.1.0.tgz"
  sha256 "b4c05da7a726fbace2603e9fafbedd0b94ecc3acfac212472cbc7361a4825736"
  license "Apache-2.0"

  depends_on "node" => :build
  depends_on "uv"
  depends_on "oven-sh/bun/bun"

  def install
    libexec.install Dir["*"]
    bin.install_symlink libexec/"bin/kosax" => "kosax"
  end

  def caveats
    <<~EOS
      KOSAX uses Bun at runtime. If Homebrew cannot resolve the Bun dependency:
        brew tap oven-sh/bun
    EOS
  end

  test do
    assert_match version.to_s, shell_output("#{bin}/kosax --version")
  end
end
