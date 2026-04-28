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
Set Theme "Tokyo Night Storm"

# Launch KOSMOS TUI (assumes `bun run --cwd tui dev` reachable)
Type "bun run --cwd tui dev"
Enter
Sleep 3s

# Citizen install command
Type "/plugin install seoul-subway"
Enter
Sleep 6s

# Approve at consent modal
Type "Y"
Sleep 4s

# Citizen query — model should invoke the new plugin via 5-primitive surface
Type "강남역 다음 열차 언제?"
Enter
Sleep 6s

# Open browser to verify the plugin is registered
Type "/plugins"
Enter
Sleep 3s

# Close browser
Escape
Sleep 1s
