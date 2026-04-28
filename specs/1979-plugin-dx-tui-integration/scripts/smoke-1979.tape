# SPDX-License-Identifier: Apache-2.0
# Spec 1979 T034 — L4 vhs visual demonstration.
#
# Drives the citizen scenario for human visual review. Output gif is
# gitignored (per AGENTS.md hard rule on >1 MB binaries).
#
# Render: bun run vhs scripts/smoke-1979.tape
#         (or: vhs specs/1979-plugin-dx-tui-integration/scripts/smoke-1979.tape)
#
# Output: specs/1979-plugin-dx-tui-integration/smoke-1979.gif (gitignored)

Output specs/1979-plugin-dx-tui-integration/smoke-1979.gif
Set Width 1200
Set Height 700
Set FontSize 14
Set FontFamily "JetBrains Mono"
Set Theme "TokyoNightStorm"

# Inject fixture catalog env vars so the backend can install the seoul-subway
# fixture without going through the live kosmos-plugin-store catalog.
Type "export KOSMOS_PLUGIN_CATALOG_URL=file:///Users/um-yunsang/KOSMOS/specs/1979-plugin-dx-tui-integration/scripts/fixtures/catalog.json"
Enter
Type "export KOSMOS_PLUGIN_SLSA_SKIP=true"
Enter
Type "export KOSMOS_ENV=development"
Enter
Type "export KOSMOS_BACKEND_STDERR_FILE=/tmp/kosmos-backend.stderr"
Enter
Sleep 500ms

# Launch KOSMOS TUI (mirrors Spec 2112 working pattern: cd tui && bun run tui)
Type "cd tui && bun run tui"
Enter
Sleep 8s

# Citizen install command (no preceding /help — modal would block input)
Type "/plugin install seoul-subway"
Enter
Sleep 12s
Screenshot specs/1979-plugin-dx-tui-integration/debug-install.png

# Approve at consent modal (give ample time for modal to render)
Sleep 3s
Type "Y"
Sleep 10s
Screenshot specs/1979-plugin-dx-tui-integration/debug-after-y.png

# Open browser to verify
Type "/plugins"
Enter
Sleep 3s
Screenshot specs/1979-plugin-dx-tui-integration/debug-browser.png

Escape
Sleep 1s
