# SPDX-License-Identifier: Apache-2.0
"""Theme system for the KOSMOS CLI.

Defines a :class:`Theme` model that maps semantic roles to Rich colour/style
strings, provides three built-in themes (``default``, ``dark``, ``light``),
and a :func:`load_theme` loader that respects the ``KOSMOS_THEME`` environment
variable with a ``KOSMOS_CLI_`` prefix for consistency.

Usage::

    from kosmos.cli.themes import load_theme

    theme = load_theme()
    console.print(f"[{theme.user_input}]You:[/]")
"""

from __future__ import annotations

import logging
import os

from pydantic import BaseModel, ConfigDict

logger = logging.getLogger(__name__)


class Theme(BaseModel):
    """Colour/style definitions for the KOSMOS CLI renderer.

    Each field maps a semantic role to a Rich markup style string accepted by
    :func:`rich.console.Console.print` (e.g. ``"bold cyan"``, ``"green"``).
    """

    model_config = ConfigDict(frozen=True)

    user_input: str = "bold white"
    """Style applied to the user prompt and echoed user text."""

    assistant_output: str = "white"
    """Style for streamed assistant response text."""

    tool_call: str = "bold cyan"
    """Style for tool-call spinner labels and tool names."""

    tool_result_ok: str = "green"
    """Style for successful tool results."""

    tool_result_err: str = "red"
    """Style for failed tool results."""

    error: str = "bold red"
    """Style for unrecoverable error messages."""

    info: str = "dim"
    """Style for informational/system messages (e.g. session ID, usage)."""

    system: str = "bold yellow"
    """Style for system-level warnings (e.g. budget exceeded notices)."""

    rule: str = "dim"
    """Style for horizontal rule separators (e.g. ``/new`` divider)."""


# ---------------------------------------------------------------------------
# Built-in themes
# ---------------------------------------------------------------------------

_THEMES: dict[str, Theme] = {
    "default": Theme(
        user_input="bold white",
        assistant_output="white",
        tool_call="bold cyan",
        tool_result_ok="green",
        tool_result_err="red",
        error="bold red",
        info="dim",
        system="bold yellow",
        rule="dim",
    ),
    "dark": Theme(
        user_input="bold grey82",
        assistant_output="grey78",
        tool_call="cyan3",
        tool_result_ok="dark_sea_green4",
        tool_result_err="indian_red",
        error="red3",
        info="grey42",
        system="dark_goldenrod",
        rule="grey35",
    ),
    "light": Theme(
        user_input="bold black",
        assistant_output="grey19",
        tool_call="dark_cyan",
        tool_result_ok="dark_green",
        tool_result_err="dark_red",
        error="bright_red",
        info="grey50",
        system="dark_orange3",
        rule="grey50",
    ),
}

_DEFAULT_THEME_NAME = "default"


def get_theme(name: str) -> Theme:
    """Return the named built-in theme.

    Args:
        name: One of ``"default"``, ``"dark"``, or ``"light"``.

    Returns:
        The corresponding :class:`Theme` instance.

    Raises:
        KeyError: If *name* is not a recognised built-in theme.
    """
    if name not in _THEMES:
        raise KeyError(f"Unknown theme {name!r}. Available themes: {list(_THEMES)}")
    return _THEMES[name]


def load_theme() -> Theme:
    """Load the active theme from the environment, falling back to ``default``.

    Reads ``KOSMOS_THEME`` (or its alias ``KOSMOS_CLI_THEME``) from the
    environment.  If the value matches a built-in theme name, that theme is
    returned.  Unrecognised values trigger a warning and fall back to
    ``default``.

    Returns:
        The resolved :class:`Theme`.
    """
    raw = os.environ.get("KOSMOS_THEME") or os.environ.get("KOSMOS_CLI_THEME", "")
    name = raw.strip().lower() or _DEFAULT_THEME_NAME
    if name not in _THEMES:
        logger.warning(
            "Unknown KOSMOS_THEME %r — falling back to %r. Valid choices: %s",
            name,
            _DEFAULT_THEME_NAME,
            ", ".join(_THEMES),
        )
        name = _DEFAULT_THEME_NAME
    return _THEMES[name]
