# SPDX-License-Identifier: Apache-2.0
"""Central registry for KOSMOS government API tools."""

from __future__ import annotations

import logging
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from kosmos.security.audit import TOOL_MIN_AAL
from kosmos.tools.bm25_index import BM25Index
from kosmos.tools.errors import (
    AdapterIdCollisionError,
    RegistrationError,
    ToolNotFoundError,
)
from kosmos.tools.models import _AUTH_TYPE_LEVEL_MAPPING, GovAPITool, ToolSearchResult
from kosmos.tools.rate_limiter import RateLimiter
from kosmos.tools.retrieval.backend import Retriever, build_retriever_from_env
from kosmos.tools.retrieval.bm25_backend import BM25Backend
from kosmos.tools.retrieval.degrade import DegradationRecord
from kosmos.tools.retrieval.dense_backend import DenseBackendLoadError
from kosmos.tools.search import search_tools

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Spec 031 Phase 2 — Five-primitive registry metadata (T007–T009).
# ---------------------------------------------------------------------------


class AdapterPrimitive(StrEnum):
    """T007 — the five primitive surfaces every registered adapter binds to.

    Matches data-model.md § 4 verbatim.
    """

    lookup = "lookup"
    resolve_location = "resolve_location"
    submit = "submit"
    subscribe = "subscribe"
    verify = "verify"


class AdapterSourceMode(StrEnum):
    """T009 — how faithfully the adapter mirrors its external source.

    OPENAPI: byte-mirrored from a public OpenAPI spec.
    OOS: shape-mirrored from an open-source SDK / reference implementation.
    HARNESS_ONLY: net-new; no external byte- or shape-mirror exists (per FR-026).
    """

    OPENAPI = "OPENAPI"
    OOS = "OOS"
    HARNESS_ONLY = "harness-only"


# T008 — 18-label closed enum of Korea-published auth tiers (primary axis).
PublishedTier = Literal[
    # gongdong_injeungseo — 3 labels
    "gongdong_injeungseo_personal_aal3",
    "gongdong_injeungseo_corporate_aal3",
    "gongdong_injeungseo_bank_only_aal2",
    # geumyung_injeungseo — 2 labels
    "geumyung_injeungseo_personal_aal2",
    "geumyung_injeungseo_business_aal3",
    # ganpyeon_injeung — 7 labels
    "ganpyeon_injeung_pass_aal2",
    "ganpyeon_injeung_kakao_aal2",
    "ganpyeon_injeung_naver_aal2",
    "ganpyeon_injeung_toss_aal2",
    "ganpyeon_injeung_bank_aal2",
    "ganpyeon_injeung_samsung_aal2",
    "ganpyeon_injeung_payco_aal2",
    # digital_onepass — 3 labels
    "digital_onepass_level1_aal1",
    "digital_onepass_level2_aal2",
    "digital_onepass_level3_aal3",
    # mobile_id — 2 labels
    "mobile_id_mdl_aal2",
    "mobile_id_resident_aal2",
    # mydata — 1 label
    "mydata_individual_aal2",
]

# T008 — advisory secondary axis; hint for external consumers only.
NistAalHint = Literal["AAL1", "AAL2", "AAL3"]


class AdapterRegistration(BaseModel):
    """T009 — registry metadata for Spec 031 five-primitive adapters.

    Mirrors data-model.md § 4 verbatim. Spec 024 V1–V4 (applied via pydantic
    ``@model_validator`` on :class:`GovAPITool`) and Spec 025 V6 + the Spec 031
    v1.2 dual-axis invariant (applied via ``@model_validator`` on this class at
    construction time; see :mod:`kosmos.security.v12_dual_axis`) remain the
    authoritative enforcement points; :meth:`ToolRegistry.register` only
    additionally validates :class:`GovAPITool` instances passed to it.
    ``published_tier_minimum`` / ``nist_aal_hint`` are optional during the
    pre-v1.2 compatibility window (FR-028) and become mandatory when the
    :mod:`kosmos.security.v12_dual_axis` backstop flips ``V12_GA_ACTIVE = True``.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    tool_id: str = Field(
        min_length=1,
        max_length=128,
        # Spec 1636 P5 ADR-007: tool_id may be either snake_case (built-in
        # adapters from Spec 022/031) OR plugin-namespaced
        # `plugin.<plugin_id>.<verb>` (Migration tree § L1-C C7) where <verb>
        # is one of the 4 root primitives. Backward-compatible alternation.
        pattern=r"^([a-z][a-z0-9_]*|plugin\.[a-z][a-z0-9_]*\.(lookup|submit|verify|subscribe|resolve_location))$",
    )
    primitive: AdapterPrimitive
    module_path: str
    input_model_ref: str
    source_mode: AdapterSourceMode

    # Dual-axis auth (Spec 031 § 6). Pre-v1.2 may ship None on either field;
    # v1.2 GA enforces both non-None via v12_dual_axis.enforce().
    published_tier_minimum: PublishedTier | None = None
    nist_aal_hint: NistAalHint | None = None

    # Spec 024 / 025 invariants preserved (FR-028)
    requires_auth: bool = True
    is_personal_data: bool = True
    is_concurrency_safe: bool = False
    cache_ttl_seconds: int = 0
    rate_limit_per_minute: int = 10
    search_hint: dict[Literal["ko", "en"], list[str]] = Field(default_factory=dict)

    # Spec 024 security extensions
    auth_type: Literal["public", "api_key", "oauth"]
    auth_level: Literal["public", "AAL1", "AAL2", "AAL3"]
    pipa_class: Literal[
        "non_personal",
        "personal_standard",
        "personal_sensitive",
        "personal_unique_id",
    ]
    is_irreversible: bool = False
    dpa_reference: str | None = None

    # Spec 031 T023 — optional per-adapter nonce used to namespace the
    # deterministic ``transaction_id`` emitted by the ``submit`` dispatcher
    # (see :func:`kosmos.primitives.submit.derive_transaction_id`). Adapters
    # that participate in the ``submit`` primitive declare a stable nonce
    # string so the dispatcher and the adapter body compute byte-identical
    # transaction ids (FR-004). ``None`` is valid for non-submit primitives
    # and for submit adapters that explicitly opt out of nonce namespacing.
    nonce: str | None = Field(default=None, max_length=128)

    @model_validator(mode="after")
    def _enforce_v12_dual_axis(self) -> AdapterRegistration:
        """Spec 031 FR-030 v1.2 GA backstop.

        Delegates to :func:`kosmos.security.v12_dual_axis.enforce`. No-op while
        ``V12_GA_ACTIVE`` is ``False`` (pre-v1.2 compatibility window, FR-028).
        Once flipped, raises ``DualAxisMissingError`` if either dual-axis field
        is ``None``. Imported inline to avoid a circular import at module load.
        """
        from kosmos.security.v12_dual_axis import enforce as _enforce_v12

        _enforce_v12(self)
        return self


class ToolRegistry:
    """Central registry for government API tools."""

    def __init__(self) -> None:
        self._tools: dict[str, GovAPITool] = {}
        self._rate_limiters: dict[str, RateLimiter] = {}

        # Spec 026: dependency-injection seam. The registry no longer
        # depends on a concrete BM25Index; it depends on the Retriever
        # protocol and lets the environment (via KOSMOS_RETRIEVAL_BACKEND)
        # pick the implementation. Default path is bm25 — byte-identical
        # to pre-#585 behaviour (FR-009, SC-04).
        default_bm25_index = BM25Index({})
        self._degradation_record = DegradationRecord()
        self._retriever: Retriever = build_retriever_from_env(
            bm25_index_factory=lambda: default_bm25_index,
            degradation_record=self._degradation_record,
        )

        # FR-009 compatibility alias: external call sites that read the
        # legacy ``bm25_index`` attribute (e.g., kosmos.tools.search) keep
        # working while we migrate them. The alias is retired in a
        # follow-on spec; during #585 it always references the BM25Index
        # owned by the active retriever when the active backend is BM25.
        if isinstance(self._retriever, BM25Backend):
            self.bm25_index: BM25Index = self._retriever._index
        else:
            self.bm25_index = default_bm25_index

    def register(self, tool: GovAPITool) -> None:
        """Register a tool.

        Raises:
            AdapterIdCollisionError: If ``tool.id`` is already registered
                (Spec 031 FR-020 — first-wins semantics). Subclasses
                :class:`DuplicateToolError`, so existing call sites that catch
                the parent keep working.
            RegistrationError: If ``is_personal_data=True`` without ``requires_auth=True``
                (FR-038 — fail-closed PII invariant), or if ``tool.auth_level`` disagrees
                with ``TOOL_MIN_AAL`` (V3 drift backstop for callers that bypass pydantic
                validation via ``model_construct``), or if the ``(auth_type, auth_level)``
                pair is outside the canonical ``_AUTH_TYPE_LEVEL_MAPPING`` (V6 backstop —
                FR-042/FR-048 — defense against ``model_construct`` / ``object.__setattr__``
                bypass of the pydantic V6 model validator).
        """
        if tool.id in self._tools:
            existing = self._tools[tool.id]
            raise AdapterIdCollisionError(
                tool.id,
                existing_module=type(existing).__module__,
            )

        # FR-038 (auth_level backstop): PII-flagged adapters MUST NOT declare
        # auth_level='public' regardless of the requires_auth flag. Pydantic V1
        # already rejects this at construction time; re-check here because a
        # caller that bypassed validation via model_construct could otherwise
        # reach the registry with an inconsistent pair.
        if tool.is_personal_data and tool.auth_level == "public":
            raise RegistrationError(
                tool.id,
                "is_personal_data=True is incompatible with auth_level='public' "
                "(Constitution §II / FR-038 / Spec-024 V1)",
            )

        # FR-038 (requires_auth backstop): PII-flagged adapters MUST also
        # require authentication. Kept as a second independent check so that a
        # tool constructed with auth_level='public' AND requires_auth=True
        # (V5 violation that slipped past validation) still fails closed.
        if tool.is_personal_data and not tool.requires_auth:
            raise RegistrationError(
                tool.id,
                "is_personal_data=True requires requires_auth=True (Constitution §II / FR-038)",
            )

        # Security spec v1 (specs/024-tool-security-v1) — validator V3.
        # GovAPITool's @model_validator already enforces V3 at construction time;
        # we re-check here so registration emits a structured log if an out-of-tree
        # caller bypassed pydantic validation (e.g., model_construct) and re-raises
        # as RegistrationError for consistency with the other FR-038 backstops above.
        expected_aal = TOOL_MIN_AAL.get(tool.id)
        if expected_aal is not None and tool.auth_level != expected_aal:
            logger.error(
                "V3 violation at registry.register: tool_id=%s declared_aal=%s "
                "expected_aal=%s (TOOL_MIN_AAL single-source-of-truth)",
                tool.id,
                tool.auth_level,
                expected_aal,
            )
            raise RegistrationError(
                tool.id,
                f"V3 violation (FR-001/FR-005): declares auth_level={tool.auth_level!r} "
                f"but TOOL_MIN_AAL requires {expected_aal!r}.",
            )

        # Security spec v1 v1.1 (specs/025-tool-security-v6) — validator V6.
        # GovAPITool's @model_validator appends a V6 block at construction time;
        # we re-check here as a second independent layer so that a caller who
        # bypassed pydantic via model_construct or mutated a frozen field with
        # object.__setattr__ cannot land a (auth_type, auth_level) pair outside
        # the canonical _AUTH_TYPE_LEVEL_MAPPING.  Mirrors the V3 FR-038 pattern.
        if tool.auth_type not in _AUTH_TYPE_LEVEL_MAPPING:
            logger.error(
                "V6 violation at registry.register: tool_id=%s auth_type=%s (unknown) "
                "— fail-closed",
                tool.id,
                tool.auth_type,
            )
            raise RegistrationError(
                tool.id,
                f"V6 violation (FR-048): unknown auth_type={tool.auth_type!r} at "
                "registry.register; refusing to allow ambiguous registration.",
            )
        allowed = _AUTH_TYPE_LEVEL_MAPPING[tool.auth_type]
        if tool.auth_level not in allowed:
            logger.error(
                "V6 violation at registry.register: tool_id=%s auth_type=%s "
                "auth_level=%s allowed=%s",
                tool.id,
                tool.auth_type,
                tool.auth_level,
                sorted(allowed),
            )
            raise RegistrationError(
                tool.id,
                f"V6 violation (FR-042): tool {tool.id!r} declares "
                f"auth_type={tool.auth_type!r} with auth_level={tool.auth_level!r}; "
                f"permitted auth_levels are {sorted(allowed)}. "
                "(registry backstop — bypass of pydantic V6 detected)",
            )

        self._tools[tool.id] = tool
        self._rate_limiters[tool.id] = RateLimiter(
            limit=tool.rate_limit_per_minute,
        )

        # Spec 026: rebuild via the injected Retriever. The BM25 default
        # path delegates straight to BM25Index.rebuild, preserving the
        # legacy behaviour; Dense / Hybrid backends recompute embeddings
        # here. Using the instance-owned retriever keeps cross-registry
        # isolation intact (parallel pytest workers see independent
        # state).
        corpus = {tid: t.search_hint for tid, t in self._tools.items()}
        try:
            self._retriever.rebuild(corpus)
        except (DenseBackendLoadError, ImportError, RuntimeError, OSError) as exc:
            # FR-002 fail-open: dense/hybrid model load failed at first real
            # rebuild. Degrade to pure BM25 and emit exactly one WARN via the
            # registry-scoped DegradationRecord latch.
            #
            # The retriever may be a wrapper (``_DenseFailOpenWrapper``)
            # whose type name does not match the user-facing backend
            # label. Prefer the wrapper's declared ``_requested_backend_label``
            # when present, otherwise fall back to the class name heuristic.
            requested = getattr(
                self._retriever,
                "_requested_backend_label",
                type(self._retriever).__name__.lower().replace("backend", ""),
            )
            self._degradation_record.emit_if_needed(
                logger,
                requested_backend=requested,
                effective_backend="bm25",
                reason=f"dense load failed: {type(exc).__name__}: {exc}",
            )
            fallback = BM25Backend(BM25Index({}))
            fallback.rebuild(corpus)
            self._retriever = fallback
            self.bm25_index = fallback._index

        logger.info("Registered tool: %s", tool.id)

    def lookup(self, tool_id: str) -> GovAPITool:
        """Look up tool by id. Raises ToolNotFoundError if not found."""
        try:
            return self._tools[tool_id]
        except KeyError:
            raise ToolNotFoundError(tool_id) from None

    def all_tools(self) -> list[GovAPITool]:
        """Return all registered tools."""
        return list(self._tools.values())

    def search(self, query: str, max_results: int = 5) -> list[ToolSearchResult]:
        """Search tools by Korean or English keywords in search_hint."""
        return search_tools(self.all_tools(), query, max_results)

    def core_tools(self) -> list[GovAPITool]:
        """Return core tools sorted by id (deterministic for prompt caching)."""
        return sorted(
            [t for t in self._tools.values() if t.is_core],
            key=lambda t: t.id,
        )

    def situational_tools(self) -> list[GovAPITool]:
        """Return non-core tools."""
        return [t for t in self._tools.values() if not t.is_core]

    def export_core_tools_openai(self) -> list[dict[str, object]]:
        """Export core tools as OpenAI function-calling definitions.

        Output is deterministic (sorted by id) for prompt cache stability.
        """
        return [t.to_openai_tool() for t in self.core_tools()]

    def get_rate_limiter(self, tool_id: str) -> RateLimiter:
        """Get the rate limiter for a tool.

        Raises ToolNotFoundError if tool_id is not registered.
        """
        if tool_id not in self._rate_limiters:
            raise ToolNotFoundError(tool_id)
        return self._rate_limiters[tool_id]

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, tool_id: str) -> bool:
        return tool_id in self._tools
