# SPDX-License-Identifier: Apache-2.0
"""Unit tests for the ``plugin_op`` IPC frame arm (Epic #1636 P5 / T012).

Covers the per-op-state shape rules in
:meth:`kosmos.ipc.frame_schema.PluginOpFrame._v_plugin_op_shape`. The
broader Spec 032 envelope round-trip + schema-parity gates already cover
``plugin_op`` after the kind count was bumped 19 → 20; this file
exercises the shape-validator branches in isolation so a regression
points at the exact rule that broke.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from kosmos.ipc.frame_schema import PluginOpFrame

_BASE = {
    "session_id": "sess-1636",
    "correlation_id": "01JXKZ8NXKZ8NXKZ8NXKZ8NXKZ",
    "ts": "2026-04-25T00:00:00.000Z",
    "frame_seq": 0,
    "transaction_id": None,
    "trailer": None,
}


class TestPluginOpRequest:
    def test_install_request_minimal(self) -> None:
        frame = PluginOpFrame(
            **_BASE,
            role="tui",
            op="request",
            request_op="install",
            name="seoul-subway",
        )
        assert frame.kind == "plugin_op"
        assert frame.op == "request"
        assert frame.request_op == "install"
        assert frame.name == "seoul-subway"

    def test_list_request_omits_name(self) -> None:
        frame = PluginOpFrame(
            **_BASE,
            role="tui",
            op="request",
            request_op="list",
        )
        assert frame.request_op == "list"
        assert frame.name is None

    def test_install_request_requires_name(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="tui",
                op="request",
                request_op="install",
                name=None,
            )
        assert "non-empty name" in str(exc.value)

    def test_request_must_not_set_progress_fields(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="tui",
                op="request",
                request_op="list",
                progress_phase=2,
            )
        assert "must not set progress/complete fields" in str(exc.value)


class TestPluginOpProgress:
    def test_minimal_progress(self) -> None:
        frame = PluginOpFrame(
            **_BASE,
            role="backend",
            op="progress",
            progress_phase=3,
            progress_message_ko="🔐 SLSA 서명 검증 중…",
            progress_message_en="Verifying SLSA provenance...",
        )
        assert frame.op == "progress"
        assert frame.progress_phase == 3

    @pytest.mark.parametrize("phase", [0, 8, -1, 99])
    def test_phase_must_be_in_range(self, phase: int) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="backend",
                op="progress",
                progress_phase=phase,
                progress_message_ko="x",
                progress_message_en="x",
            )
        assert "progress_phase in [1, 7]" in str(exc.value)

    def test_progress_requires_both_locales(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="backend",
                op="progress",
                progress_phase=1,
                progress_message_ko="ok",
                progress_message_en="",
            )
        assert "message_ko + progress_message_en" in str(exc.value)

    def test_progress_must_not_set_request_fields(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="backend",
                op="progress",
                progress_phase=1,
                progress_message_ko="x",
                progress_message_en="x",
                name="leak",
            )
        assert "must not set request/complete fields" in str(exc.value)


class TestPluginOpComplete:
    def test_minimal_success(self) -> None:
        frame = PluginOpFrame(
            **_BASE,
            role="backend",
            op="complete",
            result="success",
            exit_code=0,
            receipt_id="rcpt-abc",
        )
        assert frame.result == "success"
        assert frame.exit_code == 0
        assert frame.receipt_id == "rcpt-abc"

    def test_minimal_failure(self) -> None:
        frame = PluginOpFrame(
            **_BASE,
            role="backend",
            op="complete",
            result="failure",
            exit_code=3,
        )
        assert frame.result == "failure"
        assert frame.receipt_id is None

    def test_complete_requires_result(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="backend",
                op="complete",
                exit_code=0,
            )
        assert "requires result" in str(exc.value)

    def test_complete_requires_exit_code(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="backend",
                op="complete",
                result="success",
            )
        assert "requires exit_code" in str(exc.value)

    def test_failure_must_not_set_receipt(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="backend",
                op="complete",
                result="failure",
                exit_code=4,
                receipt_id="should-not-be-here",
            )
        assert "result='failure' must not set receipt_id" in str(exc.value)

    def test_complete_must_not_set_request_fields(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="backend",
                op="complete",
                result="success",
                exit_code=0,
                request_op="install",
            )
        assert "must not set request/progress fields" in str(exc.value)


class TestPluginOpRoleAllowList:
    def test_tui_can_emit_plugin_op(self) -> None:
        # Already covered above (role="tui"); re-asserting for the role gate.
        PluginOpFrame(
            **_BASE,
            role="tui",
            op="request",
            request_op="list",
        )

    def test_backend_can_emit_plugin_op(self) -> None:
        PluginOpFrame(
            **_BASE,
            role="backend",
            op="progress",
            progress_phase=1,
            progress_message_ko="x",
            progress_message_en="x",
        )

    def test_notification_role_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc:
            PluginOpFrame(
                **_BASE,
                role="notification",
                op="progress",
                progress_phase=1,
                progress_message_ko="x",
                progress_message_en="x",
            )
        assert "is not allowed" in str(exc.value) or "role=" in str(exc.value)
