# frozen_string_literal: true

cask "ummaya" do
  arch arm: "arm64", intel: "x64"

  version "0.1.17"
  sha256 arm:   "ded4fa8b48f8d6d4ad3e48b006b4cb6199cb5e2d50c1d23cb0f772c0deeba70a",
         intel: "4e18032520490fe0452b24574f1d488a2674bc7dcec64dbb5c65be28c590f25f"

  url "https://ummaya-docs.pages.dev/downloads/homebrew/v#{version}/ummaya-#{version}-macos-#{arch}.tar.gz"
  name "UMMAYA"
  desc "Conversational multi-agent harness for Korean public-service channels"
  homepage "https://ummaya-docs.pages.dev/"

  livecheck do
    url "https://ummaya-docs.pages.dev/downloads/homebrew/latest.json"
    strategy :json do |json|
      json["version"]
    end
  end

  depends_on :macos
  depends_on formula: "uv"

  binary "ummaya"

  postflight do
    system_command "/usr/bin/xattr",
                   args: ["-dr", "com.apple.quarantine", staged_path.to_s],
                   sudo: false
  end

  zap trash: "~/.ummaya"
end
