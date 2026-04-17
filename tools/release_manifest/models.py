# SPDX-License-Identifier: Apache-2.0
"""ReleaseManifest Pydantic v2 model for docs/release-manifests/<sha>.yaml.

Implements the data-model.md § 3 contract and enforces invariants RM1–RM4.
Intentionally decoupled from the kosmos namespace so the tools/ package
has no runtime dependency on src/.
"""

from __future__ import annotations

import logging
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Typed aliases (locally redeclared; keeps tools/ decoupled from src/)
# ---------------------------------------------------------------------------

# 40-char lowercase hex git SHA-1 (RM2).
CommitSha = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{40}$", min_length=40, max_length=40),
]

# sha256:<64-hex> prefixed digest (RM3).
Sha256Prefixed = Annotated[
    str,
    StringConstraints(pattern=r"^sha256:[0-9a-f]{64}$", min_length=71, max_length=71),
]

# FriendliAI / HuggingFace model identifier: "<org>/<repo>".
FriendliModelId = Annotated[
    str,
    StringConstraints(
        pattern=r"^[A-Za-z0-9_.\-]+/[A-Za-z0-9_.\-]+$",
        min_length=3,
        max_length=128,
    ),
]

# Semver or the "unknown" placeholder until Epic #465 ships.
LiteLlmProxyVersion = Annotated[
    str,
    StringConstraints(
        pattern=r"^(unknown|[0-9]+\.[0-9]+\.[0-9]+)$",
        min_length=3,
        max_length=32,
    ),
]

# Locally redeclared aliases mirroring kosmos.context.prompt_models.
# 64-char lowercase hex SHA-256 digest.
Sha256Hex = Annotated[
    str,
    StringConstraints(pattern=r"^[0-9a-f]{64}$", min_length=64, max_length=64),
]

# snake_case prompt identifier with mandatory _v{N} suffix.
PromptId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z][a-z0-9_]*_v[0-9]+$", min_length=3, max_length=64),
]

# ---------------------------------------------------------------------------
# ReleaseManifest
# ---------------------------------------------------------------------------

_REQUIRED_PROMPT_KEYS: frozenset[str] = frozenset(
    {"system_v1", "session_guidance_v1", "compact_v1"}
)


class ReleaseManifest(BaseModel):
    """docs/release-manifests/<commit_sha>.yaml — one per release tag push.

    Invariants:
    - RM1: prompt_hashes includes at minimum system_v1, session_guidance_v1, compact_v1.
    - RM2: commit_sha is a 40-char lowercase hex string (enforced by CommitSha alias).
    - RM3: uv_lock_hash and docker_digest are sha256:-prefixed 64-hex (Sha256Prefixed alias).
    - RM4: extra="forbid" blocks accidental addition of credential-bearing fields (NFR-03).
    """

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    commit_sha: CommitSha = Field(
        description="40-char lowercase hex git commit sha this release was built from.",
    )
    uv_lock_hash: Sha256Prefixed = Field(
        description="sha256:<hex> of uv.lock bytes at commit_sha.",
    )
    docker_digest: Sha256Prefixed = Field(
        description="sha256:<hex> of the published Docker image manifest.",
    )
    prompt_hashes: dict[PromptId, Sha256Hex] = Field(
        min_length=1,
        description=(
            "Mapping from prompt_id to sha256 hex for every prompt in "
            "prompts/manifest.yaml at commit_sha."
        ),
    )
    friendli_model_id: FriendliModelId = Field(
        description="FriendliAI-hosted model identifier in use at release time.",
    )
    litellm_proxy_version: LiteLlmProxyVersion = Field(
        description='Gateway proxy version. Placeholder "unknown" until Epic #465 ships.',
    )

    @model_validator(mode="after")
    def _check_rm1_required_prompt_keys(self) -> ReleaseManifest:
        """RM1: prompt_hashes must include system_v1, session_guidance_v1, compact_v1."""
        missing = _REQUIRED_PROMPT_KEYS - set(self.prompt_hashes.keys())
        if missing:
            raise ValueError(
                f"RM1 violation: prompt_hashes is missing required entries: {sorted(missing)!r}"
            )
        logger.debug("RM1 passed: all required prompt_hashes keys present.")
        return self
