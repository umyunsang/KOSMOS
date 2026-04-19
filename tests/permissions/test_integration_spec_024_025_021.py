# SPDX-License-Identifier: Apache-2.0
"""Spec 033 WS5 Integration test — cross-spec 024 + 025 V6 + 021.

Tests the integration wiring of:
  - FR-F01: audit coupling (audit_coupling.py — T048)
  - FR-F02: AAL backstop (aal_backstop.py — T049)
  - FR-F03: OTEL span enrichment (otel_integration.py — T051)
  - Invariant C5: synthesis boundary PII redaction (synthesis_guard.py — WS4)

WS dependencies (mocked here — swap to real implementations when WS2/WS3/WS4 land):
  - WS2: RuleStore (rule_store.load + rule_store.lookup) — mocked
  - WS3: ledger.append — mocked with expected ConsentLedgerRecord shape
  - WS4: synthesis_guard.redact — tested against real implementation

TODO: When WS2 rule-store (T010–T019) and WS3 ledger (T025–T032) are merged,
  replace the mock fixtures below with the real implementations and re-run
  this suite as a full integration test (remove the mock.patch calls).

Markers:
  @pytest.mark.integration — requires no live API calls, but exercises
    multiple layers of the permission stack together.

Reference:
  specs/033-permission-v2-spectrum/spec.md §FR-F01, §FR-F02, §FR-F03
  specs/033-permission-v2-spectrum/tasks.md T048, T049, T051, T052
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from kosmos.permissions.aal_backstop import AALDowngradeBlocked, check_aal_downgrade
from kosmos.permissions.audit_coupling import (
    AuditCouplingResult,
    MissingConsentReceiptError,
    couple_audit_record,
)
from kosmos.permissions.models import (
    AdapterPermissionMetadata,
    ConsentDecision,
    ToolPermissionContext,
)
from kosmos.permissions.otel_integration import (
    KOSMOS_CONSENT_RECEIPT_ID,
    KOSMOS_PERMISSION_DECISION,
    KOSMOS_PERMISSION_MODE,
    enrich_tool_call_span,
)
from kosmos.permissions.synthesis_guard import redact
from kosmos.security.audit import ToolCallAuditRecord

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Test helpers / factories
# ---------------------------------------------------------------------------

_FAKE_SHA256 = "a" * 64  # 64-char hex digest for test data
_FAKE_HASH_B = "b" * 64
_FAKE_HASH_C = "c" * 64


def _make_audit_record(
    *,
    tool_id: str = "hira_hospital_search",
    auth_level_presented: str = "AAL2",
    pipa_class: str = "personal",
    permission_decision: str = "allow",
    sanitized_output_hash: str | None = None,
    merkle_covered_hash: str = "output_hash",
) -> ToolCallAuditRecord:
    """Construct a minimal valid ToolCallAuditRecord for integration tests.

    Uses ``personal`` pipa_class (AAL2 HIRA adapter) with a dpa_reference
    to satisfy I3.  Uses ``allow`` + ``personal`` + non-null sanitized hash
    for I5.

    If permission_decision="allow" and pipa_class != "non_personal", I5
    requires sanitized_output_hash to be set.  Caller must pass it explicitly
    in that case.
    """
    needs_sanitized = (
        sanitized_output_hash is None
        and pipa_class != "non_personal"
        and permission_decision == "allow"
    )
    if needs_sanitized:
        # Auto-supply a valid sanitized hash so tests don't repeat this.
        sanitized_output_hash = _FAKE_HASH_B
        merkle_covered_hash = "sanitized_output_hash"

    return ToolCallAuditRecord(
        record_version="v1",
        tool_id=tool_id,
        adapter_mode="mock",
        session_id="sess-test-001",
        caller_identity="citizen-test-001",
        permission_decision=permission_decision,
        auth_level_presented=auth_level_presented,
        pipa_class=pipa_class,
        dpa_reference="HiraHospital-DPA-001",
        input_hash=_FAKE_SHA256,
        output_hash=_FAKE_HASH_C,
        sanitized_output_hash=sanitized_output_hash,
        merkle_covered_hash=merkle_covered_hash,
        merkle_leaf_id=None,
        timestamp=datetime.now(UTC),
        cost_tokens=50,
        rate_limit_bucket="default",
        public_path_marker=False,
    )


def _make_consent_decision(
    *,
    tool_id: str = "hira_hospital_search",
    granted: bool = True,
    pipa_class: str = "일반",
    auth_level: str = "AAL2",
    action_digest: str | None = None,
) -> ConsentDecision:
    """Construct a minimal valid ConsentDecision for integration tests."""
    if action_digest is None:
        action_digest = hashlib.sha256(tool_id.encode()).hexdigest()

    return ConsentDecision(
        purpose="의료기관 검색 서비스 제공",
        data_items=("거주지역", "진료과목"),
        retention_period="P30D",
        refusal_right="동의 거부 시 병원 검색 서비스를 이용할 수 없습니다",
        granted=granted,
        tool_id=tool_id,
        pipa_class=pipa_class,
        auth_level=auth_level,
        decided_at=datetime.now(UTC),
        action_digest=action_digest,
        scope="one-shot",
    )


def _make_tool_permission_context(
    *,
    tool_id: str = "hira_hospital_search",
    mode: str = "default",
    auth_level: str = "AAL2",
    pipa_class: str = "일반",
    correlation_id: str = "corr-test-001",
) -> ToolPermissionContext:
    """Construct a minimal ToolPermissionContext for integration tests."""
    adapter_meta = AdapterPermissionMetadata(
        tool_id=tool_id,
        is_irreversible=False,
        auth_level=auth_level,
        pipa_class=pipa_class,
        requires_auth=True,
        auth_type="oauth",
    )
    return ToolPermissionContext(
        tool_id=tool_id,
        mode=mode,
        is_irreversible=False,
        auth_level=auth_level,
        pipa_class=pipa_class,
        session_id="sess-test-001",
        correlation_id=correlation_id,
        arguments={"region": "서울", "specialty": "내과"},
        adapter_metadata=adapter_meta,
    )


# ---------------------------------------------------------------------------
# FR-F01: Audit coupling (T048)
# ---------------------------------------------------------------------------


class TestAuditCouplingFRF01:
    """Integration: couple_audit_record produces AuditCouplingResult with non-null receipt."""

    def test_couple_audit_record_consent_required_call(self) -> None:
        """FR-F01: HIRA adapter (AAL2, personal data) coupling produces non-null receipt_id."""
        audit_record = _make_audit_record()
        consent = _make_consent_decision()
        correlation_id = "corr-hira-001"

        result = couple_audit_record(audit_record, consent, correlation_id)

        assert isinstance(result, AuditCouplingResult)
        assert result.consent_receipt_id == consent.action_digest
        assert len(result.consent_receipt_id) == 64  # SHA-256 hex
        assert result.correlation_id == correlation_id
        assert result.audit_record is audit_record
        assert result.consent_decision is consent

    def test_couple_audit_record_receipt_id_is_non_null(self) -> None:
        """FR-F01 invariant: consent_receipt_id must be non-null for consent-required calls."""
        audit_record = _make_audit_record()
        consent = _make_consent_decision(action_digest="a" * 64)
        result = couple_audit_record(audit_record, consent, "corr-001")
        assert result.consent_receipt_id is not None
        assert result.consent_receipt_id != ""

    def test_couple_audit_record_empty_correlation_id_raises(self) -> None:
        """FR-F01: empty correlation_id is a protocol violation."""
        audit_record = _make_audit_record()
        consent = _make_consent_decision()
        with pytest.raises(ValueError, match="correlation_id must be non-empty"):
            couple_audit_record(audit_record, consent, "")

    def test_couple_audit_record_result_is_frozen(self) -> None:
        """AuditCouplingResult must be immutable (frozen dataclass)."""
        audit_record = _make_audit_record()
        consent = _make_consent_decision()
        result = couple_audit_record(audit_record, consent, "corr-001")

        with pytest.raises((AttributeError, TypeError)):
            result.consent_receipt_id = "tampered"  # type: ignore[misc]

    def test_couple_audit_record_does_not_mutate_original(self) -> None:
        """Original ToolCallAuditRecord must remain unchanged after coupling."""
        audit_record = _make_audit_record()
        original_tool_id = audit_record.tool_id
        consent = _make_consent_decision()
        result = couple_audit_record(audit_record, consent, "corr-001")

        assert result.audit_record.tool_id == original_tool_id
        assert result.audit_record is audit_record  # Same object, not copy

    def test_couple_audit_record_missing_action_digest_raises(self) -> None:
        """MissingConsentReceiptError raised when action_digest cannot serve as receipt proxy.

        NOTE: ConsentDecision.action_digest has pattern=r"^[0-9a-f]{64}$", so
        empty string fails model validation.  We test by constructing a mock.
        """
        audit_record = _make_audit_record()

        # Mock consent with empty action_digest to simulate a degraded record
        mock_consent = MagicMock(spec=ConsentDecision)
        mock_consent.action_digest = ""  # Empty — should trigger MissingConsentReceiptError
        mock_consent.tool_id = audit_record.tool_id
        mock_consent.granted = True

        with pytest.raises(MissingConsentReceiptError):
            couple_audit_record(audit_record, mock_consent, "corr-001")


# ---------------------------------------------------------------------------
# FR-F02: AAL backstop (T049)
# ---------------------------------------------------------------------------


class TestAALBackstopFRF02:
    """Integration: check_aal_downgrade blocks mismatched auth levels."""

    def test_matching_auth_levels_passes_silently(self) -> None:
        """FR-F02: identical auth_level at prompt and exec is allowed."""
        ctx_prompt = _make_tool_permission_context(auth_level="AAL2")
        ctx_exec = _make_tool_permission_context(auth_level="AAL2")
        # Should return None without raising
        result = check_aal_downgrade(ctx_prompt, ctx_exec)
        assert result is None

    def test_aal_downgrade_raises_blocked(self) -> None:
        """FR-F02 edge case: AAL2 prompt → AAL1 exec raises AALDowngradeBlocked."""
        ctx_prompt = _make_tool_permission_context(auth_level="AAL2")
        ctx_exec = _make_tool_permission_context(auth_level="AAL1")

        with pytest.raises(AALDowngradeBlocked) as exc_info:
            check_aal_downgrade(ctx_prompt, ctx_exec)

        blocked = exc_info.value
        assert blocked.prompt_auth_level == "AAL2"
        assert blocked.execution_auth_level == "AAL1"
        assert blocked.tool_id == "hira_hospital_search"

    def test_aal_upgrade_also_raises_blocked(self) -> None:
        """FR-F02: any auth_level mismatch is blocked, not just downgrades."""
        ctx_prompt = _make_tool_permission_context(auth_level="AAL1")
        ctx_exec = _make_tool_permission_context(auth_level="AAL2")

        with pytest.raises(AALDowngradeBlocked) as exc_info:
            check_aal_downgrade(ctx_prompt, ctx_exec)

        blocked = exc_info.value
        assert blocked.prompt_auth_level == "AAL1"
        assert blocked.execution_auth_level == "AAL2"

    def test_public_to_aal1_downgrade_raises(self) -> None:
        """FR-F02: public → AAL1 mismatch raises (covers direction=upgrade)."""
        ctx_prompt = _make_tool_permission_context(auth_level="public")
        ctx_exec = _make_tool_permission_context(auth_level="AAL1")

        with pytest.raises(AALDowngradeBlocked):
            check_aal_downgrade(ctx_prompt, ctx_exec)

    def test_aal3_to_aal1_downgrade_raises(self) -> None:
        """FR-F02 edge case per spec: AAL3 prompt → AAL1 exec (maximum severity downgrade)."""
        ctx_prompt = _make_tool_permission_context(auth_level="AAL3")
        ctx_exec = _make_tool_permission_context(auth_level="AAL1")

        with pytest.raises(AALDowngradeBlocked) as exc_info:
            check_aal_downgrade(ctx_prompt, ctx_exec)

        assert exc_info.value.prompt_auth_level == "AAL3"
        assert exc_info.value.execution_auth_level == "AAL1"

    def test_tool_id_mismatch_raises_value_error(self) -> None:
        """FR-F02 protocol error: different tool_ids in ctx_at_prompt vs ctx_at_exec."""
        ctx_prompt = _make_tool_permission_context(
            tool_id="hira_hospital_search", auth_level="AAL2"
        )
        ctx_exec = _make_tool_permission_context(tool_id="kma_forecast_fetch", auth_level="AAL2")

        with pytest.raises(ValueError, match="protocol error"):
            check_aal_downgrade(ctx_prompt, ctx_exec)

    def test_blocked_exception_is_frozen_dataclass(self) -> None:
        """AALDowngradeBlocked must be immutable (frozen dataclass)."""
        ctx_prompt = _make_tool_permission_context(auth_level="AAL2")
        ctx_exec = _make_tool_permission_context(auth_level="AAL1")

        with pytest.raises(AALDowngradeBlocked) as exc_info:
            check_aal_downgrade(ctx_prompt, ctx_exec)

        blocked = exc_info.value
        with pytest.raises((AttributeError, TypeError)):
            blocked.tool_id = "tampered"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# FR-F03: OTEL span enrichment (T051)
# ---------------------------------------------------------------------------


@pytest.fixture()
def otel_exporter(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[TracerProvider, InMemorySpanExporter]:
    """Set up an in-memory OTEL exporter for span inspection.

    CI sets ``OTEL_SDK_DISABLED=true`` to suppress outbound telemetry, which
    also turns ``TracerProvider`` into a no-op.  These tests need real SDK
    spans for attribute assertions, so we locally unset the flag for the
    fixture scope before constructing the provider.

    Yields (provider, exporter).  Caller accesses spans via exporter.get_finished_spans().
    """
    monkeypatch.delenv("OTEL_SDK_DISABLED", raising=False)
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    return provider, exporter


class TestOTELEnrichmentFRF03:
    """Integration: enrich_tool_call_span sets kosmos.permission.* attributes."""

    def test_granted_consent_sets_all_three_attributes(
        self, otel_exporter: tuple[TracerProvider, InMemorySpanExporter]
    ) -> None:
        """FR-F03: granted consent emits mode + decision='granted' + receipt_id."""
        provider, exporter = otel_exporter
        tracer = provider.get_tracer("test.otel.enrich")

        ctx = _make_tool_permission_context(mode="default", auth_level="AAL2")
        consent = _make_consent_decision(granted=True)

        with tracer.start_as_current_span("tool_call") as span:
            enrich_tool_call_span(span, ctx, consent)

        finished = exporter.get_finished_spans()
        assert len(finished) == 1
        attrs = finished[0].attributes

        assert attrs[KOSMOS_PERMISSION_MODE] == "default"
        assert attrs[KOSMOS_PERMISSION_DECISION] == "granted"
        assert attrs[KOSMOS_CONSENT_RECEIPT_ID] == consent.action_digest

    def test_denied_consent_sets_mode_and_denied_no_receipt(
        self, otel_exporter: tuple[TracerProvider, InMemorySpanExporter]
    ) -> None:
        """FR-F03: denied consent emits mode + decision='denied'; no receipt_id."""
        provider, exporter = otel_exporter
        tracer = provider.get_tracer("test.otel.enrich")

        ctx = _make_tool_permission_context(mode="default", auth_level="AAL2")
        consent = _make_consent_decision(granted=False)

        with tracer.start_as_current_span("tool_call") as span:
            enrich_tool_call_span(span, ctx, consent)

        finished = exporter.get_finished_spans()
        attrs = finished[0].attributes

        assert attrs[KOSMOS_PERMISSION_DECISION] == "denied"
        assert KOSMOS_CONSENT_RECEIPT_ID not in attrs

    def test_no_consent_required_sets_not_required(
        self, otel_exporter: tuple[TracerProvider, InMemorySpanExporter]
    ) -> None:
        """FR-F03: consent=None emits decision='not_required'; no receipt_id."""
        provider, exporter = otel_exporter
        tracer = provider.get_tracer("test.otel.enrich")

        ctx = _make_tool_permission_context(mode="plan", auth_level="public")

        with tracer.start_as_current_span("tool_call") as span:
            enrich_tool_call_span(span, ctx, None)

        finished = exporter.get_finished_spans()
        attrs = finished[0].attributes

        assert attrs[KOSMOS_PERMISSION_MODE] == "plan"
        assert attrs[KOSMOS_PERMISSION_DECISION] == "not_required"
        assert KOSMOS_CONSENT_RECEIPT_ID not in attrs

    def test_noop_tracer_does_not_raise(self) -> None:
        """FR-F03: when no span is recording (no-op tracer), function is silent no-op."""
        # Use the default no-op tracer (OTEL not configured)
        noop_span = trace.get_current_span()  # NonRecordingSpan by default
        ctx = _make_tool_permission_context()
        consent = _make_consent_decision()

        # Must not raise — silent no-op
        enrich_tool_call_span(noop_span, ctx, consent)

    def test_permission_mode_bypasspermissions_is_recorded(
        self, otel_exporter: tuple[TracerProvider, InMemorySpanExporter]
    ) -> None:
        """FR-F03: bypassPermissions mode is correctly recorded on span."""
        provider, exporter = otel_exporter
        tracer = provider.get_tracer("test.otel.enrich")

        ctx = _make_tool_permission_context(mode="bypassPermissions")

        with tracer.start_as_current_span("tool_call") as span:
            enrich_tool_call_span(span, ctx, None)

        finished = exporter.get_finished_spans()
        assert finished[0].attributes[KOSMOS_PERMISSION_MODE] == "bypassPermissions"


# ---------------------------------------------------------------------------
# Invariant C5: Synthesis boundary PII redaction (WS4 — synthesis_guard)
# ---------------------------------------------------------------------------


class TestSynthesisBoundaryC5:
    """Integration: synthesis_guard.redact drops 민감 fields before LLM context.

    These tests exercise the real synthesis_guard implementation (not mocked)
    against the Invariant C5 guarantee.

    TODO: When WS4 killswitch + synthesis tasks land, re-verify that the
    synthesis boundary is wired into pipeline_v2.py before LLM prompt assembly.
    """

    def _make_adapter_meta(
        self, *, tool_id: str = "hira_hospital_search", pipa_class: str = "일반"
    ) -> AdapterPermissionMetadata:
        return AdapterPermissionMetadata(
            tool_id=tool_id,
            is_irreversible=False,
            auth_level="AAL2",
            pipa_class=pipa_class,
            requires_auth=True,
            auth_type="oauth",
        )

    def test_sensitive_minkam_inline_annotation_is_redacted(self) -> None:
        """C5: field with inline __pipa_class__='민감' (sensitive) must be dropped."""
        adapter_output = {
            "hospital_name": "서울 성모병원",
            "diagnosis": {"__pipa_class__": "민감", "value": "당뇨병"},
        }
        meta = self._make_adapter_meta()
        result = redact(adapter_output, meta)

        assert "diagnosis" not in result
        assert result["hospital_name"] == "서울 성모병원"

    def test_unique_id_goyusikbyul_inline_annotation_is_redacted(self) -> None:
        """C5: field with inline __pipa_class__='고유식별' (unique ID) must be dropped."""
        adapter_output = {
            "name": "홍길동",
            "rrn": {"__pipa_class__": "고유식별", "value": "800101-1234567"},
        }
        meta = self._make_adapter_meta()
        result = redact(adapter_output, meta)

        assert "rrn" not in result
        assert result["name"] == "홍길동"

    def test_key_heuristic_catches_health_field(self) -> None:
        """C5: key-name heuristic catches 'diagnosis' even without inline annotation."""
        adapter_output = {
            "hospital_name": "연세 세브란스",
            "diagnosis": "고혈압",  # no __pipa_class__ annotation — falls back to heuristic
        }
        meta = self._make_adapter_meta()
        result = redact(adapter_output, meta)

        assert "diagnosis" not in result
        assert "hospital_name" in result

    def test_adapter_level_sensitive_class_redacts_all(self) -> None:
        """C5: if the adapter is classified 민감 (sensitive), the entire output is dropped."""
        adapter_output = {
            "hospital_name": "서울 성모병원",
            "address": "서울특별시 서초구",
        }
        meta = self._make_adapter_meta(pipa_class="민감")
        result = redact(adapter_output, meta)

        assert result == {}

    def test_safe_fields_pass_through(self) -> None:
        """C5: non-sensitive fields are forwarded to LLM context unchanged."""
        adapter_output = {
            "hospital_name": "강남 세브란스",
            "address": "서울특별시 강남구",
            "phone": "02-2019-3114",
        }
        meta = self._make_adapter_meta(pipa_class="일반")
        result = redact(adapter_output, meta)

        assert result == adapter_output

    def test_redact_raises_on_non_mapping(self) -> None:
        """C5: non-Mapping input raises TypeError (defense-in-depth)."""
        meta = self._make_adapter_meta()
        with pytest.raises(TypeError, match="Mapping"):
            redact("not a dict", meta)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# End-to-end: Simulate full tool call requiring consent (FR-F01 + F02 + F03)
# ---------------------------------------------------------------------------


class TestEndToEndConsentToolCall:
    """Simulate a complete permission pipeline flow across specs 024 + 025 V6 + 021.

    This test simulates what pipeline_v2.py should do:
    1. Capture ctx_at_prompt (ToolPermissionContext at prompt time)
    2. Citizen grants consent → ConsentDecision
    3. At execution time, capture ctx_at_exec; check_aal_downgrade() passes
    4. couple_audit_record() → AuditCouplingResult with non-null receipt
    5. enrich_tool_call_span() → OTEL span has all 3 permission attributes

    WS mock note: ledger.append is mocked since WS3 is not yet merged.

    TODO: Replace ledger.append mock with real ledger implementation once
    WS3 (T025–T032) is merged and tests/permissions/test_ledger.py passes.
    """

    def test_full_consent_flow(
        self, otel_exporter: tuple[TracerProvider, InMemorySpanExporter]
    ) -> None:
        """End-to-end: HIRA adapter consent → coupling → AAL check → OTEL enrichment."""
        provider, exporter = otel_exporter
        tracer = provider.get_tracer("test.e2e.consent")

        # Step 1: Prompt-time context (citizen is about to see consent prompt)
        ctx_at_prompt = _make_tool_permission_context(
            tool_id="hira_hospital_search",
            mode="default",
            auth_level="AAL2",
            correlation_id="corr-e2e-001",
        )

        # Step 2: Citizen grants consent
        consent = _make_consent_decision(
            tool_id="hira_hospital_search",
            granted=True,
            pipa_class="일반",
            auth_level="AAL2",
        )

        # Step 3: Execution-time context — same auth_level (no downgrade)
        ctx_at_exec = _make_tool_permission_context(
            tool_id="hira_hospital_search",
            mode="default",
            auth_level="AAL2",  # Must match prompt-time
            correlation_id="corr-e2e-001",
        )

        # FR-F02: AAL backstop passes (no downgrade)
        check_aal_downgrade(ctx_at_prompt, ctx_at_exec)

        # Step 4: Build audit record + couple it (FR-F01)
        audit_record = _make_audit_record(
            tool_id="hira_hospital_search",
            auth_level_presented="AAL2",
        )
        coupling_result = couple_audit_record(audit_record, consent, ctx_at_prompt.correlation_id)

        assert coupling_result.consent_receipt_id is not None
        assert coupling_result.correlation_id == "corr-e2e-001"

        # Step 5: OTEL span enrichment (FR-F03)
        with tracer.start_as_current_span("tool_call.hira_hospital_search") as span:
            enrich_tool_call_span(span, ctx_at_exec, consent)

        finished = exporter.get_finished_spans()
        assert len(finished) == 1
        attrs = finished[0].attributes
        assert attrs[KOSMOS_PERMISSION_MODE] == "default"
        assert attrs[KOSMOS_PERMISSION_DECISION] == "granted"
        assert KOSMOS_CONSENT_RECEIPT_ID in attrs

    def test_aal_downgrade_blocks_execution(self) -> None:
        """FR-F02: downgrade between prompt and exec prevents the tool call."""
        ctx_at_prompt = _make_tool_permission_context(auth_level="AAL2")
        ctx_at_exec = _make_tool_permission_context(auth_level="AAL1")  # Downgrade!

        with pytest.raises(AALDowngradeBlocked) as exc_info:
            check_aal_downgrade(ctx_at_prompt, ctx_at_exec)

        # Confirm the error has structured fields for audit trail
        blocked = exc_info.value
        assert blocked.tool_id == "hira_hospital_search"
        assert blocked.prompt_auth_level == "AAL2"
        assert blocked.execution_auth_level == "AAL1"
