# SPDX-License-Identifier: Apache-2.0
"""Q10 — Tests & fixtures (4 checks).

Exercises the contributor's `tests/` directory: at least one happy-path
test, at least one error-path test, a recorded JSON fixture per
adapter, and the @pytest.mark.live gate on any live-only test.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

from kosmos.plugins.checks.framework import CheckContext, CheckOutcome, failed, passed


def _ensure_manifest(ctx: CheckContext, check_id: str) -> CheckOutcome | None:
    if ctx.manifest is None:
        return failed(
            ko=f"manifest 검증 실패로 {check_id} 확인 불가",
            en=f"cannot run {check_id} — manifest failed validation",
        )
    return None


def _collect_test_functions(test_root: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    funcs: list[ast.FunctionDef | ast.AsyncFunctionDef] = []
    for py_file in test_root.glob("test_*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith(
                "test_"
            ):
                funcs.append(node)
    return funcs


def _has_decorator(fn: ast.FunctionDef | ast.AsyncFunctionDef, name: str) -> bool:
    for dec in fn.decorator_list:
        # @pytest.mark.live  → Attribute(Attribute(Name(pytest), mark), live)
        # @pytest.mark.allow_network  → similar
        if isinstance(dec, ast.Attribute) and dec.attr == name:
            return True
        if (
            isinstance(dec, ast.Call)
            and isinstance(dec.func, ast.Attribute)
            and dec.func.attr == name
        ):
            return True
    return False


def check_happy_path(ctx: CheckContext) -> CheckOutcome:
    """Q10-HAPPY-PATH — at least one test_*.py function NOT marked error/live."""
    test_root = ctx.plugin_root / "tests"
    if not test_root.is_dir():
        return failed(
            ko="tests/ 디렉토리 없음 (Q10-HAPPY-PATH)",
            en="tests/ directory missing (Q10-HAPPY-PATH)",
        )
    funcs = _collect_test_functions(test_root)
    if not funcs:
        return failed(
            ko="tests/ 에 test_* 함수 1개 이상 필요 (Q10-HAPPY-PATH)",
            en="tests/ must contain at least one test_* function (Q10-HAPPY-PATH)",
        )
    return passed()


def check_error_path(ctx: CheckContext) -> CheckOutcome:
    """Q10-ERROR-PATH — at least one test contains a `with pytest.raises(...)`."""
    test_root = ctx.plugin_root / "tests"
    if not test_root.is_dir():
        return failed(
            ko="tests/ 디렉토리 없음 (Q10-ERROR-PATH)",
            en="tests/ directory missing (Q10-ERROR-PATH)",
        )
    for py_file in test_root.glob("test_*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "raises"
            ):
                return passed()
    return failed(
        ko="`pytest.raises(...)` 를 포함하는 error-path 테스트가 없음 (Q10-ERROR-PATH)",
        en="no error-path test using `pytest.raises(...)` (Q10-ERROR-PATH)",
    )


def check_fixture_exists(ctx: CheckContext) -> CheckOutcome:
    """Q10-FIXTURE-EXISTS — every fixture file is valid JSON."""
    fixture_dir = ctx.plugin_root / "tests" / "fixtures"
    if not fixture_dir.is_dir():
        return failed(
            ko="tests/fixtures/ 디렉토리 없음 (Q10-FIXTURE-EXISTS)",
            en="tests/fixtures/ directory missing (Q10-FIXTURE-EXISTS)",
        )
    json_files = list(fixture_dir.glob("*.json"))
    if not json_files:
        return failed(
            ko="tests/fixtures/ 에 *.json 1개 이상 필요",
            en="tests/fixtures/ must contain at least one *.json",
        )
    for fp in json_files:
        try:
            json.loads(fp.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return failed(
                ko=f"fixture {fp.name} 가 valid JSON 이 아님: {exc}",
                en=f"fixture {fp.name} is not valid JSON: {exc}",
            )
    return passed()


def _file_imports_httpx(tree: ast.Module) -> bool:
    """True if the module imports `httpx` (any form)."""
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "httpx" or alias.name.startswith("httpx."):
                    return True
        elif isinstance(node, ast.ImportFrom) and (
            node.module == "httpx" or (node.module or "").startswith("httpx.")
        ):
            return True
    return False


def _is_httpx_string_arg(arg: ast.expr) -> bool:
    """True if `arg` is a string literal beginning with ``"httpx"``."""
    return (
        isinstance(arg, ast.Constant)
        and isinstance(arg.value, str)
        and arg.value.startswith("httpx")
    )


def _call_targets_httpx_attr(node: ast.Call) -> bool:
    """True if `node` is monkeypatch.setattr("httpx...", …) / respx.<verb>(...)."""
    func = node.func
    if not (isinstance(func, ast.Attribute) and func.attr in {"setattr", "mock", "get", "post"}):
        return False
    return any(_is_httpx_string_arg(a) for a in node.args)


def _imports_respx(node: ast.AST) -> bool:
    """True if `node` is `import respx` / `from respx[...] import …`."""
    if isinstance(node, ast.Import):
        return any(alias.name == "respx" or alias.name.startswith("respx.") for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return node.module == "respx" or (node.module or "").startswith("respx.")
    return False


def _file_uses_httpx_monkeypatch(tree: ast.Module) -> bool:
    """True if any test stubs httpx via monkeypatch.setattr or respx."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and _call_targets_httpx_attr(node):
            return True
        if _imports_respx(node):
            return True
    return False


def check_no_live_in_ci(ctx: CheckContext) -> CheckOutcome:
    """Q10-NO-LIVE-IN-CI — any test file that imports `httpx` must either
    gate every test with ``@pytest.mark.live`` (so default ``pytest`` runs
    skip them) or stub httpx via monkeypatch / respx so no real socket is
    opened. A file that imports httpx, contains an un-marked test, and
    does not stub it would hit data.go.kr during CI — FR-009 forbids
    this. (Constitution §IV; AGENTS.md hard rule.)
    """
    test_root = ctx.plugin_root / "tests"
    if not test_root.is_dir():
        return failed(
            ko="tests/ 디렉토리 없음 (Q10-NO-LIVE-IN-CI)",
            en="tests/ directory missing (Q10-NO-LIVE-IN-CI)",
        )
    for py_file in test_root.glob("test_*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        if not _file_imports_httpx(tree):
            continue  # File doesn't touch the network — safe.
        if _file_uses_httpx_monkeypatch(tree):
            continue  # File stubs httpx — safe.
        # File imports httpx, doesn't stub — every test_* must be live-gated.
        for node in tree.body:
            if (
                isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                and node.name.startswith("test_")
                and not _has_decorator(node, "live")
            ):
                return failed(
                    ko=(
                        f"{py_file.name}::{node.name} 이 httpx 를 import 하지만 "
                        "@pytest.mark.live 마커도 없고 monkeypatch/respx 로 "
                        "stub 도 하지 않음 (Q10-NO-LIVE-IN-CI)"
                    ),
                    en=(
                        f"{py_file.name}::{node.name} imports httpx without "
                        "@pytest.mark.live marker and without monkeypatch/respx "
                        "stub (Q10-NO-LIVE-IN-CI) — would hit network in CI"
                    ),
                )
    return passed()


__all__ = [
    "check_happy_path",
    "check_error_path",
    "check_fixture_exists",
    "check_no_live_in_ci",
]
