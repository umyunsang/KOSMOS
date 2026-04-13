# SPDX-License-Identifier: Apache-2.0
"""KOSMOS CLI entry point — initialises the backend stack and launches the REPL."""

from __future__ import annotations

import asyncio
import logging
import sys
from typing import Annotated

import typer
from rich.console import Console

from kosmos.cli.config import CLIConfig
from kosmos.cli.renderer import EventRenderer
from kosmos.cli.repl import REPLLoop

logger = logging.getLogger(__name__)

# KOSMOS version string
__version__ = "0.1.0"

# Typer application
_app = typer.Typer(
    name="kosmos",
    help="KOSMOS — Korean Public API Conversational Platform",
    add_completion=False,
)

_stderr_console = Console(stderr=True)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"kosmos {__version__}")
        raise typer.Exit()


@_app.command()
def _cli_command(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            "-v",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = False,
    debug: Annotated[
        bool,
        typer.Option("--debug", help="Enable debug logging."),
    ] = False,
) -> None:
    """Launch the KOSMOS interactive CLI."""
    if debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.WARNING)

    _run_repl()


def _run_repl() -> None:
    """Initialise the full backend stack and run the REPL.

    All initialisation errors are caught and printed as user-friendly messages.
    """
    from kosmos.context.builder import ContextBuilder
    from kosmos.engine.engine import QueryEngine
    from kosmos.llm.client import LLMClient
    from kosmos.llm.errors import ConfigurationError
    from kosmos.tools.executor import ToolExecutor
    from kosmos.tools.register_all import register_all_tools
    from kosmos.tools.registry import ToolRegistry

    console = Console()

    # --- Load CLI config ---
    try:
        config = CLIConfig()
    except Exception as exc:  # noqa: BLE001
        _stderr_console.print(f"[red]CLI 설정 오류:[/red] {exc}")
        sys.exit(1)

    # --- Initialise LLM client ---
    try:
        llm_client = LLMClient()
    except ConfigurationError as exc:
        _stderr_console.print(
            f"[red]설정 오류:[/red] {exc}\n\n"
            "[dim]KOSMOS_FRIENDLI_TOKEN 환경 변수가 설정되어 있는지 확인하세요.[/dim]"
        )
        sys.exit(1)
    except Exception as exc:  # noqa: BLE001
        _stderr_console.print(f"[red]LLM 클라이언트 초기화 오류:[/red] {exc}")
        sys.exit(1)

    # --- Initialise tool registry and executor ---
    registry = ToolRegistry()
    executor = ToolExecutor(registry)
    register_all_tools(registry, executor)

    # --- Initialise context builder ---
    context_builder = ContextBuilder(registry=registry)

    # --- Initialise query engine ---
    engine = QueryEngine(
        llm_client=llm_client,
        tool_registry=registry,
        tool_executor=executor,
        context_builder=context_builder,
    )

    # --- Launch REPL ---
    renderer = EventRenderer(console, registry=registry, show_usage=config.show_usage)
    repl = REPLLoop(
        engine=engine,
        registry=registry,
        console=console,
        config=config,
        renderer=renderer,
    )

    try:
        asyncio.run(repl.run())
    except KeyboardInterrupt:
        console.print("\n[dim]종료합니다.[/dim]")
        sys.exit(130)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Unexpected error in REPL: %s", exc)
        _stderr_console.print(f"[red]예상치 못한 오류:[/red] {exc}")
        sys.exit(1)


def main() -> None:
    """Public entry point called by ``[project.scripts]`` and ``__main__.py``."""
    _app()
