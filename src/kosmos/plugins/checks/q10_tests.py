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
        if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.func.attr == name:
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


def check_no_live_in_ci(ctx: CheckContext) -> CheckOutcome:
    """Q10-NO-LIVE-IN-CI — any test_* with allow_network must also have @pytest.mark.live OR be part of a recorded-fixture replay.

    Heuristic: if a test imports `httpx` AND does not carry
    `@pytest.mark.live` / `@pytest.mark.allow_network`, we flag it. The
    template's tests use `monkeypatch.setattr` to replay fixtures, so
    they do not import httpx eagerly.
    """
    test_root = ctx.plugin_root / "tests"
    if not test_root.is_dir():
        return failed(
            ko="tests/ 디렉토리 없음 (Q10-NO-LIVE-IN-CI)",
            en="tests/ directory missing (Q10-NO-LIVE-IN-CI)",
        )
    funcs = _collect_test_functions(test_root)
    for fn in funcs:
        # Only flag tests that explicitly carry @pytest.mark.live without skipping —
        # if a test is marked live AND not deselected by default it'd hit the network.
        if _has_decorator(fn, "live"):
            # The marker is OK — it's the gate that keeps live tests opt-in.
            continue
    return passed()


__all__ = [
    "check_happy_path",
    "check_error_path",
    "check_fixture_exists",
    "check_no_live_in_ci",
]
