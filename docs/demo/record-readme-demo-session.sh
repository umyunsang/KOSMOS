#!/usr/bin/env bash
# SPDX-License-Identifier: Apache-2.0
#
# Deprecated guard. README demo recording must not run expect inside t-rec.

set -euo pipefail

cat >&2 <<'MSG'
docs/demo/record-readme-demo-session.sh is deprecated.

README demo recording now runs t-rec directly around docs/demo/run-readme-demo.sh.
For Codex/operator automation, use docs/demo/drive-readme-demo-gui.sh, which types
into the visible macOS Terminal from outside the t-rec child process.
MSG
exit 2
