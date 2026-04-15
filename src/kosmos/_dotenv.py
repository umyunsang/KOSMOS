# SPDX-License-Identifier: Apache-2.0
"""Repo-root ``.env`` loader used by both the CLI entry point and the test suite.

Tool adapters (``tools/errors.py``, ``permissions/credentials.py``, ``cli/themes.py``)
read env vars directly via ``os.environ.get()`` rather than through
``pydantic-settings``. Without this loader, a developer who configured
``KOSMOS_*`` keys via ``.env`` would see tool adapters report "not set"
because ``pydantic-settings`` materialises values into its own settings
object — never into ``os.environ``. Shell-exported variables always win,
so production deployments that inject secrets via GitHub Actions / systemd
/ Docker env are unaffected.

Stdlib-only parser — no new runtime dependency (see ``AGENTS.md``).
"""

from __future__ import annotations

import os
from pathlib import Path


def load_repo_dotenv(repo_root: Path | None = None) -> None:
    """Populate ``os.environ`` from ``<repo_root>/.env`` if present.

    Pre-existing ``os.environ`` entries win — never overwrites a variable
    that the shell (or CI secret injection) already exported. Silently
    no-ops when ``.env`` is absent.
    """
    root = repo_root if repo_root is not None else _default_repo_root()
    env_path = root / ".env"
    if not env_path.is_file():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _default_repo_root() -> Path:
    """Resolve the repo root assuming this file lives at ``src/kosmos/_dotenv.py``."""
    return Path(__file__).resolve().parent.parent.parent
