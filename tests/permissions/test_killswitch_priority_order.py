# SPDX-License-Identifier: Apache-2.0
"""Mutation test — killswitch pipeline priority order (T035).

Invariant K1: The killswitch MUST be the FIRST step in the permission pipeline.
Any re-ordering that places Mode / Rule / Prompt evaluation BEFORE the killswitch
MUST cause this test to fail.

This test imports:
  - ``killswitch.assert_killswitch_first``  — structural assertion helper
  - ``pipeline_v2``                         — the real pipeline module (stub + docstring
                                              encode the step order contract)

It asserts two things:
  1. The documented pipeline step order in ``pipeline_v2.evaluate()`` lists
     ``killswitch.pre_evaluate`` at position 0.
  2. Passing a re-ordered list to ``assert_killswitch_first()`` raises
     ``AssertionError`` — the helper correctly enforces K1.

Reference:
    specs/033-permission-v2-spectrum/data-model.md § 2.1 K1
    specs/033-permission-v2-spectrum/contracts/mode-transition.contract.md § 5
"""

from __future__ import annotations

import inspect

import pytest

from kosmos.permissions.killswitch import KILLSWITCH_ORDER, assert_killswitch_first

# ---------------------------------------------------------------------------
# 1. KILLSWITCH_ORDER constant assertion
# ---------------------------------------------------------------------------


def test_killswitch_order_constant_is_one() -> None:
    """KILLSWITCH_ORDER must equal 1 (step 1 in the pipeline)."""
    assert KILLSWITCH_ORDER == 1, (
        f"Invariant K1: KILLSWITCH_ORDER must be 1 (first pipeline step). "
        f"Found {KILLSWITCH_ORDER!r}."
    )


# ---------------------------------------------------------------------------
# 2. assert_killswitch_first — correct order passes silently
# ---------------------------------------------------------------------------


def test_assert_killswitch_first_passes_when_killswitch_is_first() -> None:
    """assert_killswitch_first does not raise when killswitch is step 0."""
    pipeline_order = [
        "killswitch.pre_evaluate",
        "mode.evaluate",
        "rule.resolve",
        "prompt.ask",
    ]
    # Must not raise
    assert_killswitch_first(pipeline_order)


# ---------------------------------------------------------------------------
# 3. Mutation: mode before killswitch → AssertionError (K1 enforcement)
# ---------------------------------------------------------------------------


def test_assert_killswitch_first_raises_when_mode_is_first() -> None:
    """Any order with mode.evaluate BEFORE killswitch MUST raise AssertionError (K1)."""
    bad_order = [
        "mode.evaluate",           # ← WRONG: mode before killswitch
        "killswitch.pre_evaluate",
        "rule.resolve",
        "prompt.ask",
    ]
    with pytest.raises(AssertionError, match="Invariant K1 violation"):
        assert_killswitch_first(bad_order)


def test_assert_killswitch_first_raises_when_rule_is_first() -> None:
    """Any order with rule.resolve BEFORE killswitch MUST raise AssertionError (K1)."""
    bad_order = [
        "rule.resolve",
        "killswitch.pre_evaluate",
        "mode.evaluate",
        "prompt.ask",
    ]
    with pytest.raises(AssertionError, match="Invariant K1 violation"):
        assert_killswitch_first(bad_order)


def test_assert_killswitch_first_raises_when_prompt_is_first() -> None:
    """Any order with prompt.ask BEFORE killswitch MUST raise AssertionError (K1)."""
    bad_order = [
        "prompt.ask",
        "mode.evaluate",
        "killswitch.pre_evaluate",
        "rule.resolve",
    ]
    with pytest.raises(AssertionError, match="Invariant K1 violation"):
        assert_killswitch_first(bad_order)


# ---------------------------------------------------------------------------
# 4. Edge cases for assert_killswitch_first
# ---------------------------------------------------------------------------


def test_assert_killswitch_first_raises_on_empty_order() -> None:
    """Empty pipeline order raises ValueError (not AssertionError)."""
    with pytest.raises(ValueError):
        assert_killswitch_first([])


def test_assert_killswitch_first_raises_when_killswitch_absent() -> None:
    """Pipeline with no killswitch step at all raises AssertionError (K1)."""
    no_killswitch_order = [
        "mode.evaluate",
        "rule.resolve",
        "prompt.ask",
    ]
    with pytest.raises(AssertionError, match="Invariant K1 violation"):
        assert_killswitch_first(no_killswitch_order)


def test_assert_killswitch_first_accepts_tuple() -> None:
    """assert_killswitch_first works with a tuple as well as a list."""
    pipeline_order = (
        "killswitch.pre_evaluate",
        "mode.evaluate",
        "rule.resolve",
    )
    # Must not raise
    assert_killswitch_first(pipeline_order)


def test_assert_killswitch_first_case_insensitive() -> None:
    """Step name matching is case-insensitive (Killswitch / KILLSWITCH both valid)."""
    pipeline_order = [
        "Killswitch.PreEvaluate",  # Different casing
        "mode.evaluate",
    ]
    # Must not raise
    assert_killswitch_first(pipeline_order)


# ---------------------------------------------------------------------------
# 5. Pipeline v2 docstring encodes the step order (structural mutation test)
# ---------------------------------------------------------------------------


def test_pipeline_v2_docstring_lists_killswitch_as_step_1() -> None:
    """pipeline_v2.evaluate docstring MUST list killswitch as the first step.

    This test parses the ``evaluate`` function's docstring to verify that the
    step order documented there places ``killswitch.pre_evaluate`` at step 1.
    If a developer re-orders the steps in the docstring, this test fails —
    providing an early warning before any wiring change.
    """
    from kosmos.permissions import pipeline_v2  # noqa: PLC0415 — import inside test

    doc = inspect.getdoc(pipeline_v2.evaluate) or ""
    # The docstring must mention killswitch before mode, rule, and prompt.
    killswitch_pos = doc.find("killswitch")
    mode_pos = doc.find("mode.evaluate")
    rule_pos = doc.find("rule.resolve")
    prompt_pos = doc.find("prompt.ask")

    # killswitch must appear in the docstring
    assert killswitch_pos >= 0, (
        "pipeline_v2.evaluate docstring does not mention 'killswitch'. "
        "Invariant K1 requires killswitch to be documented as step 1."
    )

    # If mode, rule, or prompt are mentioned, killswitch must come first.
    for other_name, other_pos in [
        ("mode.evaluate", mode_pos),
        ("rule.resolve", rule_pos),
        ("prompt.ask", prompt_pos),
    ]:
        if other_pos >= 0:
            assert killswitch_pos < other_pos, (
                f"Invariant K1: 'killswitch' appears AFTER '{other_name}' in "
                f"pipeline_v2.evaluate docstring. The documented order MUST list "
                f"killswitch as the first step."
            )


def test_pipeline_v2_module_docstring_references_killswitch_first() -> None:
    """pipeline_v2 module docstring MUST list killswitch as step 1."""
    from kosmos.permissions import pipeline_v2  # noqa: PLC0415 — import inside test

    module_doc = pipeline_v2.__doc__ or ""
    # The module docstring must place killswitch at step 1 in its numbered list.
    # Check that "1." and "killswitch" appear in the docstring and that
    # "1." precedes "2." precedes "3." precedes "4." in that document.
    assert "killswitch" in module_doc.lower(), (
        "pipeline_v2 module docstring does not mention 'killswitch'. "
        "Invariant K1 requires the module to document killswitch as step 1."
    )
    # Verify "1." killswitch appears before "2." mode in the module docstring.
    step1_pos = module_doc.find("1.")
    killswitch_pos = module_doc.lower().find("killswitch")
    step2_pos = module_doc.find("2.")
    assert killswitch_pos >= 0
    # Between step1_pos and step2_pos there should be "killswitch".
    assert step1_pos < killswitch_pos < step2_pos, (
        "Invariant K1: pipeline_v2 module docstring does not list killswitch "
        "as step 1 (between '1.' and '2.'). Re-ordering violates K1."
    )
