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
Sleep 500ms

# Launch KOSMOS TUI (mirrors Spec 2112 working pattern: cd tui && bun run tui)
Type "cd tui && bun run tui"
Enter
Sleep 8s

# Citizen install command
Type "/plugin install seoul-subway"
Enter
Sleep 7s

# Approve at consent modal
Type "Y"
Sleep 5s

# Citizen query — model should invoke the new plugin via 5-primitive surface
Type "강남역 다음 열차 언제?"
Enter
Sleep 8s

# Open browser to verify the plugin is registered
Type "/plugins"
Enter
Sleep 3s

# Close browser
Escape
Sleep 1s
