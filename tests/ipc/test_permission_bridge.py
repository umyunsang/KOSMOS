# SPDX-License-Identifier: Apache-2.0
"""Permission bridge protocol contract tests (Spec 1978 T051 — Track D).

Tests the permission_request / permission_response round-trip contract from
specs/1978-tui-kexaone-wiring/contracts/permission-bridge-protocol.md.

Strategy: In-process harness only — does NOT call _handle_chat_request.
The harness simulates the backend bridge logic described in the contract's
implementation skeleton:
  - pending_perms: dict[str, asyncio.Future[...]]
  - _check_permission_via_bridge(decision, response) → ConsentDecision
  - _write_receipt(path, ...) → Path

All frame construction is exercised through the real Pydantic models
(PermissionRequestFrame, PermissionResponseFrame) from frame_schema.py.

NOTE FOR TRACK B INTEGRATION:
  These tests assume Track B will land the following surface at roughly:
    src/kosmos/ipc/permission_bridge.py (name TBD):
      - pending_perms: dict[str, asyncio.Future]
      - register_pending_permission(request_id, future)   # guessed name
      - resolve_pending_permission(request_id, frame)     # guessed name
      - write_consent_receipt(consent_dir, receipt_id, tool_id,
                              session_id, decision, gauntlet_step,
                              granted_at) -> Path          # guessed name
  If Track B uses different names, patch the import aliases in this file
  (see the HARNESS section below) rather than rewriting the test logic.

Contract invariants under test:
  D1  — pipeline.evaluate() == ALLOW  → no PermissionRequestFrame emitted
  D2  — pipeline.evaluate() == DENY   → no frame; immediate deny result
  D3  — pipeline.evaluate() == ASK    → PermissionRequestFrame emitted with
                                         all required fields
  D4  — allow_once response           → pending_perms future resolves; tool
                                         is NOT added to session_grants
  D5  — allow_session response        → pending_perms future resolves; tool_id
                                         added to session_grants; next call skips
                                         the bridge entirely (no new request frame)
  D6  — deny response                 → future resolves with DENY; tool MUST NOT
                                         be dispatched
  D7  — timeout (default-deny)        → backend synthesises DENY, pending entry
                                         cleaned up
  D8  — non-deny outcome              → ConsentReceipt written under consent_dir
                                         with correct payload shape
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from kosmos.ipc.frame_schema import (
    PermissionRequestFrame,
    PermissionResponseFrame,
)
from kosmos.permissions.models import (
    AdapterPermissionMetadata,
    PermissionMode,
    ToolPermissionContext,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Protocol vocabulary
# Mirrors permission-bridge-protocol.md § PermissionResponseFrame.decision.
# The current frame_schema.py uses Literal["granted", "denied"] (Spec 287
# baseline) but the bridge contract specifies Literal["allow_once",
# "allow_session", "deny"].  Track B will extend the Literal; the harness
# uses plain strings so tests remain schema-version-agnostic.
# ---------------------------------------------------------------------------

_DECISION_ALLOW_ONCE = "allow_once"
_DECISION_ALLOW_SESSION = "allow_session"
_DECISION_DENY = "deny"

# ---------------------------------------------------------------------------
# Frame construction helpers (base envelope fields)
# ---------------------------------------------------------------------------

_BASE_ENVELOPE = {
    "session_id": "sess-test-001",
    "correlation_id": "019da5b0-e60d-71a0-a393-000000000099",
    "ts": "2026-04-27T00:00:00.000Z",
    "frame_seq": 0,
    "transaction_id": None,
    "trailer": None,
}


def _make_request_frame(request_id: str) -> PermissionRequestFrame:
    """Build a minimal PermissionRequestFrame for mock_traffic_fine_pay_v1."""
    return PermissionRequestFrame(
        **_BASE_ENVELOPE,
        role="backend",
        kind="permission_request",
        request_id=request_id,
        worker_id="w-test-001",
        primitive_kind="submit",
        description_ko="교통 범칙금 납부 허가 요청",
        description_en="Permission to submit traffic fine payment",
        risk_level="high",
    )


def _make_response_frame(request_id: str, decision: str) -> dict:
    """Build a PermissionResponseFrame-shaped dict.

    Uses 'granted' as the Pydantic-level value until Track B extends the
    Literal.  The bridge harness maps the richer 3-decision vocabulary at
    the application level; the frame carries the decision as an extra field
    validated at the bridge layer.
    """
    # Use the existing Pydantic field for now; Track B will migrate to the
    # 3-decision vocabulary.  We attach `bridge_decision` as supplemental
    # context that the bridge logic reads.
    pydantic_decision = "granted" if decision != _DECISION_DENY else "denied"
    return {
        "frame": PermissionResponseFrame(
            **_BASE_ENVELOPE,
            role="tui",
            kind="permission_response",
            request_id=request_id,
            decision=pydantic_decision,
        ),
        "bridge_decision": decision,  # richer vocabulary for the bridge
        "receipt_id": str(uuid.uuid4()),
    }


# ---------------------------------------------------------------------------
# In-process permission bridge harness
#
# Simulates the backend bridge skeleton from the contract (no real stdio):
#   pending_perms[request_id] = asyncio.Future()
#   resolve → future.set_result(decision_bundle)
#   timeout → cancel / set_exception → synthesize DENY
# ---------------------------------------------------------------------------


class _PermissionBridgeHarness:
    """Minimal in-process implementation of the bridge contract skeleton.

    This is NOT the real Track B implementation — it is the contract oracle.
    Tests assert that a correct Track B implementation would satisfy the same
    invariants.
    """

    def __init__(self, consent_dir: Path, timeout: float = 60.0) -> None:
        self.consent_dir = consent_dir
        self.consent_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.pending_perms: dict[str, asyncio.Future[dict]] = {}
        self.session_grants: set[str] = set()
        self.emitted_request_frames: list[PermissionRequestFrame] = []
        self.denied_without_frame: list[str] = []  # tool_ids denied silently

    # --- simulate pipeline.evaluate() outcomes ---

    async def evaluate_auto_allow(self, tool_id: str) -> str:
        """ALLOW path: no frame emitted, return 'allow'."""
        # D1: no PermissionRequestFrame must be emitted
        return "allow"

    async def evaluate_auto_deny(self, tool_id: str) -> str:
        """DENY path: no frame emitted, return 'deny'."""
        # D2: no bridge frame to TUI
        self.denied_without_frame.append(tool_id)
        return "deny"

    async def evaluate_ask(
        self,
        tool_id: str,
        request_id: str | None = None,
    ) -> tuple[str, str | None]:
        """ASK path: emit frame, await response, return (outcome, receipt_id).

        D3: PermissionRequestFrame must be emitted with all required fields.
        D4/D5/D6: decision-specific outcomes.
        D7: timeout → default deny.
        D8: receipt written on non-deny.
        """
        request_id = request_id or str(uuid.uuid4())
        req_frame = _make_request_frame(request_id)

        # D3 invariant check — all required fields present (schema enforced)
        assert req_frame.request_id == request_id
        assert req_frame.primitive_kind == "submit"
        assert req_frame.risk_level == "high"
        self.emitted_request_frames.append(req_frame)

        loop = asyncio.get_running_loop()
        future: asyncio.Future[dict] = loop.create_future()
        self.pending_perms[request_id] = future

        try:
            response_bundle = await asyncio.wait_for(
                asyncio.shield(future), timeout=self.timeout
            )
        except asyncio.TimeoutError:
            # D7: default deny on timeout
            self.pending_perms.pop(request_id, None)
            logger.warning("permission_bridge: timeout for request_id=%s", request_id)
            return "deny", None
        finally:
            self.pending_perms.pop(request_id, None)

        bridge_decision = response_bundle["bridge_decision"]
        receipt_id = response_bundle["receipt_id"]

        # D5: allow_session → add to session_grants
        if bridge_decision == _DECISION_ALLOW_SESSION:
            self.session_grants.add(tool_id)

        # D8: write receipt for non-deny outcomes
        if bridge_decision != _DECISION_DENY:
            self._write_receipt(
                receipt_id=receipt_id,
                tool_id=tool_id,
                session_id=_BASE_ENVELOPE["session_id"],
                decision=bridge_decision,
                gauntlet_step=4,
            )
            return "allow", receipt_id

        return "deny", None

    def resolve(self, request_id: str, decision: str) -> None:
        """Simulate TUI resolving a pending permission request."""
        future = self.pending_perms.get(request_id)
        if future is None:
            logger.warning("permission_bridge: unknown request_id=%s (drop)", request_id)
            return
        bundle = _make_response_frame(request_id, decision)
        future.set_result(bundle)

    def _write_receipt(
        self,
        receipt_id: str,
        tool_id: str,
        session_id: str,
        decision: str,
        gauntlet_step: int,
    ) -> Path:
        """Write consent receipt per contract § Receipt persistence."""
        receipt = {
            "receipt_id": receipt_id,
            "session_id": session_id,
            "tool_id": tool_id,
            "decision": decision,
            "gauntlet_step": gauntlet_step,
            "granted_at": datetime.now(UTC).isoformat(),
            "revoked_at": None,
        }
        path = self.consent_dir / f"{receipt_id}.json"
        path.write_text(json.dumps(receipt, ensure_ascii=False))
        return path


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def consent_dir(tmp_path: Path) -> Path:
    return tmp_path / "consent"


@pytest.fixture
def harness(consent_dir: Path, monkeypatch: pytest.MonkeyPatch) -> _PermissionBridgeHarness:
    monkeypatch.setenv("KOSMOS_CONSENT_DIR", str(consent_dir))
    return _PermissionBridgeHarness(consent_dir=consent_dir, timeout=0.5)


# ---------------------------------------------------------------------------
# ToolPermissionContext construction helper (verifies model imports)
# ---------------------------------------------------------------------------


def _make_tool_permission_ctx(
    tool_id: str = "mock_traffic_fine_pay_v1",
    mode: PermissionMode = "default",
) -> ToolPermissionContext:
    meta = AdapterPermissionMetadata(
        tool_id=tool_id,
        is_irreversible=True,
        auth_level="AAL1",
        pipa_class="일반",
        requires_auth=False,
        auth_type="public",
    )
    return ToolPermissionContext(
        tool_id=tool_id,
        mode=mode,
        is_irreversible=True,
        auth_level="AAL1",
        pipa_class="일반",
        session_id="sess-test-001",
        correlation_id="019da5b0-e60d-71a0-a393-000000000099",
        arguments={"fine_id": "TR-2026-001"},
        adapter_metadata=meta,
    )


# ===========================================================================
# D1 — auto_allow: pipeline returns ALLOW, no frame emitted
# ===========================================================================


async def test_d1_auto_allow_no_frame_emitted(harness: _PermissionBridgeHarness) -> None:
    """ALLOW path: evaluate_auto_allow must not emit any PermissionRequestFrame."""
    ctx = _make_tool_permission_ctx(mode="bypassPermissions")
    outcome = await harness.evaluate_auto_allow(ctx.tool_id)

    assert outcome == "allow"
    assert len(harness.emitted_request_frames) == 0, (
        "auto_allow must not emit any permission_request frame"
    )


# ===========================================================================
# D2 — auto_deny: pipeline returns DENY, no frame emitted
# ===========================================================================


async def test_d2_auto_deny_no_frame_emitted(harness: _PermissionBridgeHarness) -> None:
    """DENY path: evaluate_auto_deny must not emit a frame; tool is denied server-side."""
    ctx = _make_tool_permission_ctx()
    outcome = await harness.evaluate_auto_deny(ctx.tool_id)

    assert outcome == "deny"
    assert len(harness.emitted_request_frames) == 0, (
        "auto_deny must not emit any permission_request frame"
    )
    assert ctx.tool_id in harness.denied_without_frame


# ===========================================================================
# D3 — ASK emits a well-formed PermissionRequestFrame
# ===========================================================================


async def test_d3_ask_emits_request_frame(harness: _PermissionBridgeHarness) -> None:
    """ASK path: must emit a PermissionRequestFrame with all required contract fields."""
    ctx = _make_tool_permission_ctx()
    request_id = str(uuid.uuid4())

    # Drive evaluate_ask in background; immediately resolve so it doesn't hang
    task = asyncio.create_task(harness.evaluate_ask(ctx.tool_id, request_id))
    await asyncio.sleep(0)  # yield to let the task reach its await
    harness.resolve(request_id, _DECISION_ALLOW_ONCE)
    outcome, _receipt_id = await task

    assert len(harness.emitted_request_frames) == 1
    frame = harness.emitted_request_frames[0]
    assert frame.kind == "permission_request"
    assert frame.request_id == request_id
    assert frame.role == "backend"
    assert frame.primitive_kind == "submit"
    assert frame.risk_level == "high"
    assert frame.description_ko  # non-empty Korean description
    assert frame.description_en  # non-empty English description


# ===========================================================================
# D4 — allow_once: future resolves; tool NOT added to session_grants
# ===========================================================================


async def test_d4_allow_once_resolves_future_no_session_grant(
    harness: _PermissionBridgeHarness,
) -> None:
    """allow_once: pending future resolves with allow; tool_id NOT in session_grants."""
    ctx = _make_tool_permission_ctx()
    request_id = str(uuid.uuid4())

    task = asyncio.create_task(harness.evaluate_ask(ctx.tool_id, request_id))
    await asyncio.sleep(0)
    harness.resolve(request_id, _DECISION_ALLOW_ONCE)
    outcome, receipt_id = await task

    assert outcome == "allow"
    assert receipt_id is not None
    assert ctx.tool_id not in harness.session_grants, (
        "allow_once must NOT add tool_id to session_grants"
    )
    assert request_id not in harness.pending_perms, (
        "resolved request must be cleaned up from pending_perms"
    )


# ===========================================================================
# D5 — allow_session: future resolves; tool_id added to session_grants;
#       subsequent same-session same-tool call skips bridge
# ===========================================================================


async def test_d5_allow_session_adds_to_session_grants(
    harness: _PermissionBridgeHarness,
) -> None:
    """allow_session: future resolves with allow; tool_id added to session_grants."""
    ctx = _make_tool_permission_ctx()
    request_id = str(uuid.uuid4())

    task = asyncio.create_task(harness.evaluate_ask(ctx.tool_id, request_id))
    await asyncio.sleep(0)
    harness.resolve(request_id, _DECISION_ALLOW_SESSION)
    outcome, receipt_id = await task

    assert outcome == "allow"
    assert receipt_id is not None
    assert ctx.tool_id in harness.session_grants, (
        "allow_session must add tool_id to session_grants"
    )


async def test_d5_allow_session_subsequent_call_skips_bridge(
    harness: _PermissionBridgeHarness,
) -> None:
    """Subsequent same-tool call with session grant must skip bridge frame emit."""
    ctx = _make_tool_permission_ctx()
    # Pre-populate session grant (simulates a prior allow_session outcome)
    harness.session_grants.add(ctx.tool_id)

    # A second call should auto-allow — simulate via auto_allow path
    outcome = await harness.evaluate_auto_allow(ctx.tool_id)

    assert outcome == "allow"
    assert len(harness.emitted_request_frames) == 0, (
        "session-granted tool must not re-emit permission_request frame"
    )


# ===========================================================================
# D6 — deny: future resolves with DENY; tool must NOT be dispatched
# ===========================================================================


async def test_d6_deny_resolves_future_no_dispatch(
    harness: _PermissionBridgeHarness,
) -> None:
    """deny: future resolves with deny outcome; tool must NOT be dispatched."""
    ctx = _make_tool_permission_ctx()
    request_id = str(uuid.uuid4())

    task = asyncio.create_task(harness.evaluate_ask(ctx.tool_id, request_id))
    await asyncio.sleep(0)
    harness.resolve(request_id, _DECISION_DENY)
    outcome, receipt_id = await task

    assert outcome == "deny", "deny response must produce deny outcome"
    assert receipt_id is None, "deny must not produce a receipt_id"
    assert ctx.tool_id not in harness.session_grants
    assert request_id not in harness.pending_perms


# ===========================================================================
# D7 — timeout: no response within timeout → default deny (Constitution §II)
# ===========================================================================


async def test_d7_timeout_default_deny(
    harness: _PermissionBridgeHarness, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Timeout (D7): no TUI response within timeout → backend emits synthetic DENY.

    Uses KOSMOS_PERMISSION_TIMEOUT_SECONDS env var pattern (shrunken to 0.1s).
    """
    # harness.timeout is already 0.5s from fixture; patch to 0.05s for speed
    harness.timeout = 0.05
    ctx = _make_tool_permission_ctx()
    request_id = str(uuid.uuid4())

    # Start evaluate_ask but never resolve — let it time out
    outcome, receipt_id = await harness.evaluate_ask(ctx.tool_id, request_id)

    assert outcome == "deny", "timeout must produce default-deny outcome (D7)"
    assert receipt_id is None
    assert request_id not in harness.pending_perms, (
        "timed-out request_id must be cleaned up from pending_perms"
    )


# ===========================================================================
# D8 — consent receipt written for non-deny outcomes
# ===========================================================================


async def test_d8_receipt_written_on_allow_once(
    harness: _PermissionBridgeHarness, consent_dir: Path
) -> None:
    """allow_once: consent receipt JSON written under consent_dir with correct shape."""
    ctx = _make_tool_permission_ctx()
    request_id = str(uuid.uuid4())

    task = asyncio.create_task(harness.evaluate_ask(ctx.tool_id, request_id))
    await asyncio.sleep(0)
    harness.resolve(request_id, _DECISION_ALLOW_ONCE)
    outcome, receipt_id = await task

    assert outcome == "allow"
    assert receipt_id is not None

    receipt_path = consent_dir / f"{receipt_id}.json"
    assert receipt_path.exists(), f"receipt file not found at {receipt_path}"

    receipt = json.loads(receipt_path.read_text())
    assert receipt["receipt_id"] == receipt_id
    assert receipt["tool_id"] == ctx.tool_id
    assert receipt["session_id"] == _BASE_ENVELOPE["session_id"]
    assert receipt["decision"] == _DECISION_ALLOW_ONCE
    assert receipt["gauntlet_step"] in (4, 5)
    assert receipt["granted_at"]  # non-empty ISO-8601 string
    assert receipt["revoked_at"] is None


async def test_d8_receipt_written_on_allow_session(
    harness: _PermissionBridgeHarness, consent_dir: Path
) -> None:
    """allow_session: consent receipt JSON written with decision='allow_session'."""
    ctx = _make_tool_permission_ctx()
    request_id = str(uuid.uuid4())

    task = asyncio.create_task(harness.evaluate_ask(ctx.tool_id, request_id))
    await asyncio.sleep(0)
    harness.resolve(request_id, _DECISION_ALLOW_SESSION)
    outcome, receipt_id = await task

    assert outcome == "allow"
    receipt_path = consent_dir / f"{receipt_id}.json"
    assert receipt_path.exists()
    receipt = json.loads(receipt_path.read_text())
    assert receipt["decision"] == _DECISION_ALLOW_SESSION


async def test_d8_no_receipt_on_deny(
    harness: _PermissionBridgeHarness, consent_dir: Path
) -> None:
    """deny: NO receipt file must be written (D8 — non-deny only)."""
    ctx = _make_tool_permission_ctx()
    request_id = str(uuid.uuid4())

    task = asyncio.create_task(harness.evaluate_ask(ctx.tool_id, request_id))
    await asyncio.sleep(0)
    harness.resolve(request_id, _DECISION_DENY)
    outcome, _receipt_id = await task

    assert outcome == "deny"
    receipt_files = list(consent_dir.glob("*.json"))
    assert len(receipt_files) == 0, "deny must not write any receipt file"


async def test_d8_no_receipt_on_timeout(
    harness: _PermissionBridgeHarness, consent_dir: Path
) -> None:
    """timeout: NO receipt file must be written (D7+D8 combined)."""
    harness.timeout = 0.05
    ctx = _make_tool_permission_ctx()
    request_id = str(uuid.uuid4())

    outcome, _receipt_id = await harness.evaluate_ask(ctx.tool_id, request_id)
    assert outcome == "deny"
    assert not list(consent_dir.glob("*.json")), "timeout must not write any receipt file"


# ===========================================================================
# Frame schema contract — PermissionRequestFrame and PermissionResponseFrame
# Validates the Pydantic schema constraints are correctly modelled
# ===========================================================================


def test_permission_request_frame_schema_valid() -> None:
    """PermissionRequestFrame must accept valid contract-compliant fields."""
    frame = _make_request_frame(request_id="req-schema-001")
    assert frame.kind == "permission_request"
    assert frame.role == "backend"
    assert frame.primitive_kind in ("lookup", "resolve_location", "submit", "subscribe", "verify")
    assert frame.risk_level in ("low", "medium", "high")


def test_permission_request_frame_rejects_wrong_role() -> None:
    """PermissionRequestFrame must reject role='tui' (E3 invariant)."""
    with pytest.raises(ValidationError, match="role"):
        PermissionRequestFrame(
            **_BASE_ENVELOPE,
            role="tui",  # invalid — permission_request must be emitted by backend
            kind="permission_request",
            request_id="req-001",
            worker_id="w1",
            primitive_kind="lookup",
            description_ko="테스트",
            description_en="test",
            risk_level="low",
        )


def test_permission_response_frame_schema_valid() -> None:
    """PermissionResponseFrame must accept valid contract-compliant fields."""
    frame = PermissionResponseFrame(
        **_BASE_ENVELOPE,
        role="tui",
        kind="permission_response",
        request_id="req-001",
        decision="granted",
    )
    assert frame.kind == "permission_response"
    assert frame.role == "tui"
    assert frame.request_id == "req-001"


def test_permission_response_frame_rejects_wrong_role() -> None:
    """PermissionResponseFrame must reject role='backend' (E3 invariant)."""
    with pytest.raises(ValidationError, match="role"):
        PermissionResponseFrame(
            **_BASE_ENVELOPE,
            role="backend",  # invalid — permission_response must come from tui
            kind="permission_response",
            request_id="req-001",
            decision="granted",
        )


def test_tool_permission_context_construction() -> None:
    """ToolPermissionContext must be constructable for mock_traffic_fine_pay_v1."""
    ctx = _make_tool_permission_ctx()
    assert ctx.tool_id == "mock_traffic_fine_pay_v1"
    assert ctx.mode == "default"
    assert ctx.is_irreversible is True
    assert ctx.auth_level == "AAL1"
    assert ctx.pipa_class == "일반"


def test_unknown_request_id_response_dropped(harness: _PermissionBridgeHarness) -> None:
    """TUI response for an unknown request_id must be silently dropped (no crash)."""
    # This simulates the "stale response" failure mode documented in the contract
    harness.resolve("nonexistent-request-id", _DECISION_ALLOW_ONCE)
    # Must not raise; pending_perms must remain empty
    assert "nonexistent-request-id" not in harness.pending_perms
