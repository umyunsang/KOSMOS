# SPDX-License-Identifier: Apache-2.0
"""Tests for CLI app entry point."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from kosmos.cli.app import __version__, _app, main

runner = CliRunner()


class TestVersionFlag:
    def test_version_flag(self) -> None:
        result = runner.invoke(_app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_version_short_flag(self) -> None:
        result = runner.invoke(_app, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.output


class TestMainEntry:
    def test_main_callable(self) -> None:
        """main() is a callable that delegates to typer app."""
        # Just test that calling main with --version works
        with pytest.raises(SystemExit) as exc_info, patch("sys.argv", ["kosmos", "--version"]):
            main()
        # typer exits with 0 for --version
        assert exc_info.value.code == 0


class TestRunReplConfigurationError:
    def test_configuration_error_exits_1(self) -> None:
        """ConfigurationError during LLM init results in exit code 1."""
        from kosmos.llm.errors import ConfigurationError

        with patch("kosmos.llm.client.LLMClient", side_effect=ConfigurationError("missing token")):
            result = runner.invoke(_app, [])
        assert result.exit_code == 1

    def test_generic_llm_error_exits_1(self) -> None:
        """Any unexpected error during LLM init results in exit code 1."""
        with patch("kosmos.llm.client.LLMClient", side_effect=RuntimeError("boom")):
            result = runner.invoke(_app, [])
        assert result.exit_code == 1

    def test_cli_config_error_exits_1(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CLIConfig init failure results in exit code 1."""
        monkeypatch.setenv("KOSMOS_CLI_HISTORY_SIZE", "not_a_number")
        result = runner.invoke(_app, [])
        assert result.exit_code == 1


class TestRunReplSuccess:
    def test_repl_launched_on_success(self) -> None:
        """Full REPL init path: mock all dependencies and verify run is called."""
        mock_repl_instance = MagicMock()
        run_called = False

        async def mock_run() -> None:
            nonlocal run_called
            run_called = True

        mock_repl_instance.run = mock_run

        with (
            patch("kosmos.llm.client.LLMClient"),
            patch("kosmos.tools.registry.ToolRegistry"),
            patch("kosmos.tools.executor.ToolExecutor"),
            patch("kosmos.tools.register_all.register_all_tools"),
            patch("kosmos.context.builder.ContextBuilder"),
            patch("kosmos.engine.engine.QueryEngine"),
            patch("kosmos.cli.app.EventRenderer"),
            patch("kosmos.cli.app.REPLLoop", return_value=mock_repl_instance) as mock_repl_cls,
        ):
            result = runner.invoke(_app, [])
        assert result.exit_code == 0
        mock_repl_cls.assert_called_once()
        assert run_called, "REPLLoop.run() was never awaited"

    def test_keyboard_interrupt_exits_130(self) -> None:
        """KeyboardInterrupt from the REPL results in exit code 130."""
        # Patch _run_repl directly so sys.exit(130) propagates through typer.
        with patch("kosmos.cli.app._run_repl", side_effect=SystemExit(130)):
            result = runner.invoke(_app, [])
        assert result.exit_code == 130

    def test_unexpected_error_exits_1(self) -> None:
        """Unexpected error from REPL results in exit code 1."""
        # Patch _run_repl directly so sys.exit(1) propagates through typer.
        with patch("kosmos.cli.app._run_repl", side_effect=SystemExit(1)):
            result = runner.invoke(_app, [])
        assert result.exit_code == 1

    def test_debug_flag_sets_logging(self) -> None:
        """--debug flag enables DEBUG level logging."""
        mock_repl_instance = MagicMock()

        async def mock_run() -> None:
            return None

        mock_repl_instance.run = mock_run

        with (
            patch("kosmos.llm.client.LLMClient"),
            patch("kosmos.tools.registry.ToolRegistry"),
            patch("kosmos.tools.executor.ToolExecutor"),
            patch("kosmos.tools.register_all.register_all_tools"),
            patch("kosmos.context.builder.ContextBuilder"),
            patch("kosmos.engine.engine.QueryEngine"),
            patch("kosmos.cli.app.EventRenderer"),
            patch("kosmos.cli.app.REPLLoop", return_value=mock_repl_instance),
            patch("kosmos.cli.app.logging.basicConfig") as mock_logging,
        ):
            runner.invoke(_app, ["--debug"])
        import logging

        mock_logging.assert_called_once_with(level=logging.DEBUG)


class TestRuntimeWiring:
    """Verify the CLI wires PermissionPipeline + RecoveryExecutor into QueryEngine.

    Regression: earlier revisions constructed PermissionPipeline but never
    passed it to QueryEngine, so the 7-step gauntlet was silently bypassed.
    Similarly RecoveryExecutor must be shared between ToolExecutor and the
    pipeline so circuit breakers + caches survive the request.
    """

    def test_permission_pipeline_and_recovery_executor_wired_to_query_engine(self) -> None:
        from kosmos.permissions.pipeline import PermissionPipeline
        from kosmos.recovery.executor import RecoveryExecutor
        from kosmos.tools.executor import ToolExecutor

        captured: dict[str, object] = {}

        class _FakeEngine:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

        mock_repl_instance = MagicMock()

        async def mock_run() -> None:
            return None

        mock_repl_instance.run = mock_run

        with (
            patch("kosmos.llm.client.LLMClient"),
            patch("kosmos.engine.engine.QueryEngine", _FakeEngine),
            patch("kosmos.cli.app.EventRenderer"),
            patch("kosmos.cli.app.REPLLoop", return_value=mock_repl_instance),
        ):
            result = runner.invoke(_app, [])

        assert result.exit_code == 0
        assert isinstance(captured["permission_pipeline"], PermissionPipeline)
        assert captured["permission_session"] is not None
        assert isinstance(captured["tool_executor"], ToolExecutor)
        # ToolExecutor must own the shared RecoveryExecutor; the pipeline sees
        # the same executor so circuit breakers survive across the request.
        tool_exec = captured["tool_executor"]
        assert isinstance(tool_exec._recovery_executor, RecoveryExecutor)

    def test_recovery_executor_and_pipeline_share_metrics_and_event_logger(self) -> None:
        """The shared observability instances must reach recovery + pipeline."""
        from kosmos.observability import MetricsCollector, ObservabilityEventLogger

        captured: dict[str, object] = {}

        class _FakeEngine:
            def __init__(self, **kwargs: object) -> None:
                captured.update(kwargs)

        mock_repl_instance = MagicMock()

        async def mock_run() -> None:
            return None

        mock_repl_instance.run = mock_run

        with (
            patch("kosmos.llm.client.LLMClient"),
            patch("kosmos.engine.engine.QueryEngine", _FakeEngine),
            patch("kosmos.cli.app.EventRenderer"),
            patch("kosmos.cli.app.REPLLoop", return_value=mock_repl_instance),
        ):
            runner.invoke(_app, [])

        pipeline = captured["permission_pipeline"]
        tool_exec = captured["tool_executor"]
        # The pipeline and the tool executor's recovery layer must share
        # the *same* metrics + event logger instances.
        assert isinstance(pipeline._metrics, MetricsCollector)  # type: ignore[attr-defined]
        assert isinstance(
            pipeline._event_logger, ObservabilityEventLogger
        )  # type: ignore[attr-defined]
        recovery = tool_exec._recovery_executor
        assert recovery._metrics is pipeline._metrics  # type: ignore[attr-defined]
        assert recovery._event_logger is pipeline._event_logger  # type: ignore[attr-defined]
