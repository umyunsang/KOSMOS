# SPDX-License-Identifier: Apache-2.0
"""Fail-fast startup guard for required KOSMOS_* environment variables.

Mirrors Claude Code's permissions gauntlet: boundary check runs **before** the
tool loop (or in our case, before setup_tracing/app bootstrap) and exits the
process with EX_CONFIG (78) after aggregating **all** missing required
variables for the active environment into a single-line remediation message.

Contract: specs/026-secrets-infisical-oidc/contracts/guard.md
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Final, Literal

Env = Literal["dev", "ci", "prod"]


_DOC_URL: Final[str] = "https://github.com/umyunsang/KOSMOS/blob/main/docs/configuration.md"
_VALID_ENVS: Final[frozenset[str]] = frozenset({"dev", "ci", "prod"})


@dataclass(frozen=True, slots=True)
class RequiredVar:
    name: str
    consumer: str
    required_in: frozenset[Env]
    doc_anchor: str


@dataclass(frozen=True, slots=True)
class GuardDiagnostic:
    missing: tuple[str, ...]
    env: Env
    doc_url: str


_REQUIRED_VARS: Final[tuple[RequiredVar, ...]] = (
    RequiredVar(
        name="KOSMOS_KAKAO_API_KEY",
        consumer="kosmos.settings.KosmosSettings.kakao_api_key",
        required_in=frozenset({"dev", "ci", "prod"}),
        doc_anchor="#kosmos_kakao_api_key",
    ),
    RequiredVar(
        name="KOSMOS_FRIENDLI_TOKEN",
        consumer="kosmos.llm.config.LLMClientConfig.token",
        required_in=frozenset({"dev", "ci", "prod"}),
        doc_anchor="#kosmos_friendli_token",
    ),
    RequiredVar(
        name="KOSMOS_DATA_GO_KR_API_KEY",
        consumer="kosmos.settings.KosmosSettings.data_go_kr_api_key",
        required_in=frozenset({"dev", "ci", "prod"}),
        doc_anchor="#kosmos_data_go_kr_api_key",
    ),
    # Observability vars are required in `prod` only — matches the
    # `docs/configuration.md` registry ("Yes (prod only)") and contract
    # test T-G06. CI runs pull these via Infisical when live-suite tests
    # execute, but the guard treats them as optional there so unit CI
    # jobs do not need to seed them.
    RequiredVar(
        name="LANGFUSE_PUBLIC_KEY",
        consumer="kosmos.observability.langfuse (#501)",
        required_in=frozenset({"prod"}),
        doc_anchor="#langfuse_public_key",
    ),
    RequiredVar(
        name="LANGFUSE_SECRET_KEY",
        consumer="kosmos.observability.langfuse (#501)",
        required_in=frozenset({"prod"}),
        doc_anchor="#langfuse_secret_key",
    ),
    RequiredVar(
        name="KOSMOS_OTEL_ENDPOINT",
        consumer="kosmos.observability.otel (#501)",
        required_in=frozenset({"prod"}),
        doc_anchor="#kosmos_otel_endpoint",
    ),
)


def current_env() -> Env:
    """Read KOSMOS_ENV from os.environ; unknown values fall through to 'dev'."""
    raw = os.environ.get("KOSMOS_ENV", "")
    if raw in _VALID_ENVS:
        return raw  # type: ignore[return-value]
    return "dev"


def check_required(env: Env | None = None) -> GuardDiagnostic | None:
    """Pure function. Returns GuardDiagnostic if any required vars missing, else None.

    Library-safe: no I/O, no logging, no sys.exit. Suitable for unit tests.
    """
    active_env: Env = env if env is not None else current_env()
    missing: list[str] = []
    for var in _REQUIRED_VARS:
        if active_env not in var.required_in:
            continue
        if os.environ.get(var.name, "").strip() == "":
            missing.append(var.name)
    if not missing:
        return None
    return GuardDiagnostic(
        missing=tuple(sorted(missing)),
        env=active_env,
        doc_url=_DOC_URL,
    )


def verify_startup() -> None:
    """CLI-layer wrapper. Exit 78 with single-line stderr on missing vars.

    No-op on success. MUST NOT touch .env, emit OTel, or init network clients.
    """
    diag = check_required()
    if diag is None:
        return
    message = (
        f"KOSMOS config error [env={diag.env}]: "
        f"missing required variables: {', '.join(diag.missing)}. "
        f"See {diag.doc_url}"
    )
    sys.stderr.write(message + "\n")
    sys.exit(78)
