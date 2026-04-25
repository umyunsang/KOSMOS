# SPDX-License-Identifier: Apache-2.0
"""End-to-end plugin install flow.

Implements the 8-phase install per
``specs/1636-plugin-dx-5tier/contracts/plugin-install.cli.md``:

1. 📡 카탈로그 조회 — fetch the catalog index, resolve ``<name>`` →
   ``CatalogVersion``.
2. 📦 번들 다운로드 — fetch the bundle, verify SHA-256.
3. 🔐 SLSA 서명 검증 — shell out to slsa-verifier; honour
   ``KOSMOS_PLUGIN_SLSA_SKIP``.
4. 🧪 매니페스트 검증 — extract ``manifest.yaml`` from the bundle and
   round-trip through :class:`PluginManifest`.
5. 📝 동의 확인 — render permission summary + wait for citizen
   confirmation (unless ``--yes`` or ``dry_run``).
6. 🔄 등록 + BM25 색인 — extract bundle into
   ``KOSMOS_PLUGIN_INSTALL_ROOT/<plugin_id>/`` and call
   :func:`kosmos.plugins.registry.register_plugin_adapter`.
7. 📜 동의 영수증 기록 — write
   :class:`PluginConsentReceipt` to ``memdir/user/consent/``.
8. ✓ 설치 완료.

Exit codes (mapped onto :class:`InstallResult.exit_code`):

| Code | Meaning |
|---|---|
| 0 | Success. |
| 1 | Catalog resolution failed. |
| 2 | Bundle SHA-256 mismatch. |
| 3 | SLSA verification failed. |
| 4 | Manifest validation failed. |
| 5 | Citizen rejected consent. |
| 6 | I/O error during bundle extraction or registry registration. |
| 7 | Backend prerequisite missing (e.g. slsa-verifier binary). |

The installer never raises — every failure is encoded into
:class:`InstallResult`. Network access lives behind two callable
seams (``catalog_fetcher`` / ``bundle_fetcher``) so tests can supply
local file:// or in-memory fixtures without monkeypatching httpx.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import tarfile
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from kosmos.plugins.canonical_acknowledgment import CANONICAL_ACKNOWLEDGMENT_SHA256
from kosmos.plugins.manifest_schema import PluginManifest
from kosmos.plugins.registry import register_plugin_adapter
from kosmos.plugins.slsa import (
    SLSAFailureKind,
    SLSAVerificationResult,
    verify_artifact,
)
from kosmos.settings import settings
from kosmos.tools.executor import ToolExecutor
from kosmos.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


_EXIT_OK = 0
_EXIT_CATALOG = 1
_EXIT_BUNDLE_SHA = 2
_EXIT_SLSA = 3
_EXIT_MANIFEST = 4
_EXIT_CONSENT = 5
_EXIT_IO = 6
_EXIT_PREREQ = 7


# ---------------------------------------------------------------------------
# Catalog models — mirror contracts/catalog-index.schema.json
# ---------------------------------------------------------------------------


class CatalogVersion(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    bundle_url: str = Field(pattern=r"^https?://.+\.tar\.gz$|^file://.+\.tar\.gz$")
    provenance_url: str = Field(
        pattern=r"^https?://.+\.intoto\.jsonl$|^file://.+\.intoto\.jsonl$"
    )
    bundle_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    published_iso: str


class CatalogEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(pattern=r"^[a-z][a-z0-9-]*$")
    plugin_id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    latest_version: str = Field(pattern=r"^\d+\.\d+\.\d+$")
    versions: list[CatalogVersion] = Field(min_length=1)
    tier: Literal["live", "mock"]
    permission_layer: Literal[1, 2, 3]
    processes_pii: bool
    trustee_org_name: str | None = None
    last_published_iso: str

    def resolve_version(self, requested: str | None) -> CatalogVersion:
        target = requested or self.latest_version
        for v in self.versions:
            if v.version == target:
                return v
        raise ValueError(
            f"version {target!r} not in catalog entry for {self.name!r}"
        )


class CatalogIndex(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["1.0.0"] = "1.0.0"
    generated_iso: str
    entries: list[CatalogEntry]

    def find(self, name: str) -> CatalogEntry | None:
        for entry in self.entries:
            if entry.name == name:
                return entry
        return None


# ---------------------------------------------------------------------------
# Result envelopes
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InstallResult:
    """Outcome record returned from :func:`install_plugin`."""

    exit_code: int
    plugin_id: str | None
    plugin_version: str | None
    receipt_id: str | None
    error_kind: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class PluginConsentReceipt:
    """Spec 035 ConsentRecord extension for plugin install/uninstall.

    Mirrors data-model.md § 5. Persisted as a JSON file under
    ``memdir/user/consent/``; append-only by spec 035 invariant — a
    revocation is a *new* receipt with ``action_type="plugin_uninstall"``.
    """

    receipt_id: str
    timestamp_iso: str
    action_type: Literal["plugin_install", "plugin_uninstall"]
    plugin_id: str
    plugin_version: str
    slsa_verification: Literal["passed", "failed", "skipped"]
    trustee_org_name: str | None
    consent_ledger_position: int

    def to_json(self) -> dict[str, object]:
        return {
            "receipt_id": self.receipt_id,
            "timestamp_iso": self.timestamp_iso,
            "action_type": self.action_type,
            "plugin_id": self.plugin_id,
            "plugin_version": self.plugin_version,
            "slsa_verification": self.slsa_verification,
            "trustee_org_name": self.trustee_org_name,
            "consent_ledger_position": self.consent_ledger_position,
        }


# ---------------------------------------------------------------------------
# Seams — overridable for tests
# ---------------------------------------------------------------------------


CatalogFetcher = Callable[[str], bytes]
BundleFetcher = Callable[[str, Path], None]
ConsentPrompt = Callable[[CatalogEntry, CatalogVersion, PluginManifest], bool]


def _default_catalog_fetcher(url: str) -> bytes:
    """Fetch the catalog index. Supports file:// for tests, https:// for prod."""
    if url.startswith("file://"):
        return Path(url[len("file://") :]).read_bytes()
    import httpx  # noqa: PLC0415

    response = httpx.get(url, timeout=30.0, follow_redirects=True)
    response.raise_for_status()
    return response.content


def _default_bundle_fetcher(url: str, dest: Path) -> None:
    """Stream a bundle to disk. file:// → copy; https:// → httpx download."""
    if url.startswith("file://"):
        shutil.copy(url[len("file://") :], dest)
        return
    import httpx  # noqa: PLC0415

    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as response:
        response.raise_for_status()
        with dest.open("wb") as out:
            for chunk in response.iter_bytes():
                out.write(chunk)


def _default_consent_prompt(
    entry: CatalogEntry,
    version: CatalogVersion,
    manifest: PluginManifest,
) -> bool:
    """Default to deny when no UI is wired (TUI path overrides this in T053)."""
    logger.warning(
        "no consent_prompt provided for plugin %s; defaulting to deny",
        entry.name,
    )
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _safe_extract(tar: tarfile.TarFile, dest: Path) -> None:
    """Extract a tar archive while rejecting path-traversal entries.

    Pre-3.12 path-traversal check + Python 3.12+ ``filter='data'``
    member filter so the call is forward-compatible with the upcoming
    default behaviour change in Python 3.14.
    """
    dest_resolved = dest.resolve()
    for member in tar.getmembers():
        target = (dest / member.name).resolve()
        if not str(target).startswith(str(dest_resolved)):
            raise OSError(
                f"plugin bundle entry {member.name!r} escapes install root"
            )
    tar.extractall(dest, filter="data")  # noqa: S202 — checked above.


def _consent_ledger_next_position(consent_root: Path) -> int:
    if not consent_root.is_dir():
        return 0
    return sum(1 for _ in consent_root.glob("*.json"))


def _write_consent_receipt(
    receipt: PluginConsentReceipt,
    *,
    consent_root: Path,
) -> Path:
    consent_root.mkdir(parents=True, exist_ok=True)
    out = consent_root / f"{receipt.receipt_id}.json"
    payload = json.dumps(receipt.to_json(), indent=2, ensure_ascii=False)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(payload, encoding="utf-8")
    import os  # noqa: PLC0415

    fd = os.open(tmp, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    tmp.replace(out)
    return out


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def install_plugin(  # noqa: C901, PLR0911, PLR0915 — phased flow.
    name: str,
    *,
    registry: ToolRegistry,
    executor: ToolExecutor,
    requested_version: str | None = None,
    catalog_url: str | None = None,
    catalog_fetcher: CatalogFetcher = _default_catalog_fetcher,
    bundle_fetcher: BundleFetcher = _default_bundle_fetcher,
    consent_prompt: ConsentPrompt = _default_consent_prompt,
    yes: bool = False,
    dry_run: bool = False,
) -> InstallResult:
    """Run the 8-phase plugin install flow.

    Args:
        name: Catalog ``name`` (matches ``CatalogEntry.name``).
        registry: Central :class:`ToolRegistry` to register the adapter into.
        executor: :class:`ToolExecutor` for adapter binding.
        requested_version: Optional SemVer pin; defaults to ``latest_version``.
        catalog_url: Override the catalog index URL.
        catalog_fetcher / bundle_fetcher / consent_prompt: Test seams.
        yes: When True, skip the consent prompt (CI / unattended).
        dry_run: When True, run all phases except phase 6/7 — verify but
            never write to disk under ``KOSMOS_PLUGIN_INSTALL_ROOT`` and
            never append a consent receipt.

    Returns:
        :class:`InstallResult` with the exit code per the contract.
    """
    catalog_url = catalog_url or settings.plugin_catalog_url

    # --- Phase 1: catalog --------------------------------------------------
    try:
        raw = catalog_fetcher(catalog_url)
        catalog = CatalogIndex.model_validate(json.loads(raw))
    except (ValidationError, OSError, ValueError, json.JSONDecodeError) as exc:
        return InstallResult(
            exit_code=_EXIT_CATALOG,
            plugin_id=None,
            plugin_version=None,
            receipt_id=None,
            error_kind="catalog_fetch_failed",
            error_message=(
                f"could not fetch / parse catalog at {catalog_url}: {exc}"
            ),
        )

    entry = catalog.find(name)
    if entry is None:
        return InstallResult(
            exit_code=_EXIT_CATALOG,
            plugin_id=None,
            plugin_version=None,
            receipt_id=None,
            error_kind="catalog_miss",
            error_message=(
                f"plugin {name!r} not found in catalog at {catalog_url}"
            ),
        )

    try:
        version = entry.resolve_version(requested_version)
    except ValueError as exc:
        return InstallResult(
            exit_code=_EXIT_CATALOG,
            plugin_id=entry.plugin_id,
            plugin_version=requested_version,
            receipt_id=None,
            error_kind="catalog_version_miss",
            error_message=str(exc),
        )

    plugin_id = entry.plugin_id

    # --- Phase 2: bundle download ------------------------------------------
    bundle_cache = settings.plugin_bundle_cache
    bundle_cache.mkdir(parents=True, exist_ok=True)
    bundle_path = bundle_cache / f"{plugin_id}-{version.bundle_sha256[:12]}.tar.gz"
    try:
        bundle_fetcher(version.bundle_url, bundle_path)
    except (OSError, RuntimeError) as exc:
        return InstallResult(
            exit_code=_EXIT_IO,
            plugin_id=plugin_id,
            plugin_version=version.version,
            receipt_id=None,
            error_kind="bundle_fetch_failed",
            error_message=str(exc),
        )

    actual_sha = _sha256_of(bundle_path)
    if actual_sha != version.bundle_sha256:
        return InstallResult(
            exit_code=_EXIT_BUNDLE_SHA,
            plugin_id=plugin_id,
            plugin_version=version.version,
            receipt_id=None,
            error_kind="bundle_sha_mismatch",
            error_message=(
                f"bundle SHA-256 {actual_sha} != expected {version.bundle_sha256}"
            ),
        )

    # --- Phase 3: SLSA verification ----------------------------------------
    slsa_state: Literal["passed", "failed", "skipped"]
    if settings.plugin_slsa_skip:
        slsa_state = "skipped"
        logger.warning(
            "KOSMOS_PLUGIN_SLSA_SKIP=true — bypassing SLSA verification for %s",
            plugin_id,
        )
    else:
        provenance_path = bundle_cache / f"{plugin_id}-{version.bundle_sha256[:12]}.intoto.jsonl"
        try:
            bundle_fetcher(version.provenance_url, provenance_path)
        except (OSError, RuntimeError) as exc:
            return InstallResult(
                exit_code=_EXIT_IO,
                plugin_id=plugin_id,
                plugin_version=version.version,
                receipt_id=None,
                error_kind="provenance_fetch_failed",
                error_message=str(exc),
            )

        slsa_result: SLSAVerificationResult = verify_artifact(
            bundle_path=bundle_path,
            provenance_path=provenance_path,
            source_uri=f"github.com/kosmos-plugin-store/kosmos-plugin-{name}",
        )
        if not slsa_result.passed:
            exit_code = (
                _EXIT_PREREQ
                if slsa_result.failure_kind is SLSAFailureKind.BINARY_NOT_FOUND
                else _EXIT_SLSA
            )
            return InstallResult(
                exit_code=exit_code,
                plugin_id=plugin_id,
                plugin_version=version.version,
                receipt_id=None,
                error_kind=str(slsa_result.failure_kind),
                error_message=slsa_result.stderr_tail,
            )
        slsa_state = "passed"

    # --- Phase 4: manifest validation --------------------------------------
    try:
        with tarfile.open(bundle_path, "r:gz") as tf:
            manifest_member = tf.getmember("manifest.yaml")
            extracted = tf.extractfile(manifest_member)
            if extracted is None:
                raise OSError("manifest.yaml not extractable from bundle")
            raw_manifest = yaml.safe_load(extracted.read().decode("utf-8"))
        manifest = PluginManifest.model_validate(raw_manifest)
    except (KeyError, OSError, tarfile.TarError, yaml.YAMLError, ValidationError) as exc:
        return InstallResult(
            exit_code=_EXIT_MANIFEST,
            plugin_id=plugin_id,
            plugin_version=version.version,
            receipt_id=None,
            error_kind="manifest_invalid",
            error_message=str(exc),
        )

    # Cross-check: catalog tier ↔ manifest tier; catalog plugin_id ↔ manifest plugin_id.
    if manifest.plugin_id != plugin_id:
        return InstallResult(
            exit_code=_EXIT_MANIFEST,
            plugin_id=plugin_id,
            plugin_version=version.version,
            receipt_id=None,
            error_kind="manifest_plugin_id_mismatch",
            error_message=(
                f"catalog plugin_id={plugin_id!r} != manifest plugin_id="
                f"{manifest.plugin_id!r}"
            ),
        )
    if manifest.tier != entry.tier:
        return InstallResult(
            exit_code=_EXIT_MANIFEST,
            plugin_id=plugin_id,
            plugin_version=version.version,
            receipt_id=None,
            error_kind="manifest_tier_mismatch",
            error_message=(
                f"catalog tier={entry.tier!r} != manifest tier={manifest.tier!r}"
            ),
        )

    # The PluginManifest validators already enforce:
    # - canonical PIPA hash equality (R-1 Q6-PIPA-HASH)
    # - kosmos.plugin.id OTEL attribute = plugin_id (FR-021)
    # - plugin namespace + verb suffix (ADR-007)
    # We assert one extra invariant for paranoia: PIPA hash drift between
    # the manifest and the in-tree canonical constant.
    if manifest.pipa_trustee_acknowledgment is not None:
        ack_hash = manifest.pipa_trustee_acknowledgment.acknowledgment_sha256
        if ack_hash != CANONICAL_ACKNOWLEDGMENT_SHA256:  # pragma: no cover
            return InstallResult(
                exit_code=_EXIT_MANIFEST,
                plugin_id=plugin_id,
                plugin_version=version.version,
                receipt_id=None,
                error_kind="pipa_hash_drift",
                error_message=(
                    "manifest PIPA acknowledgment_sha256 does not match "
                    "canonical hash — refusing to install"
                ),
            )

    # --- Phase 5: consent --------------------------------------------------
    if not yes and not dry_run:
        try:
            granted = consent_prompt(entry, version, manifest)
        except Exception as exc:  # noqa: BLE001 — broad catch on UI hook.
            return InstallResult(
                exit_code=_EXIT_CONSENT,
                plugin_id=plugin_id,
                plugin_version=version.version,
                receipt_id=None,
                error_kind="consent_prompt_failed",
                error_message=str(exc),
            )
        if not granted:
            return InstallResult(
                exit_code=_EXIT_CONSENT,
                plugin_id=plugin_id,
                plugin_version=version.version,
                receipt_id=None,
                error_kind="consent_rejected",
                error_message="citizen declined consent prompt",
            )

    # --- Dry-run short-circuit ---------------------------------------------
    if dry_run:
        logger.info(
            "dry_run=True; verified plugin %s v%s but not writing to disk",
            plugin_id,
            version.version,
        )
        return InstallResult(
            exit_code=_EXIT_OK,
            plugin_id=plugin_id,
            plugin_version=version.version,
            receipt_id=None,
            error_kind=None,
            error_message=None,
        )

    # --- Phase 6: extract bundle + register --------------------------------
    install_root = settings.plugin_install_root
    plugin_dir = install_root / plugin_id
    if plugin_dir.exists():
        shutil.rmtree(plugin_dir)
    plugin_dir.mkdir(parents=True, exist_ok=True)
    try:
        with tarfile.open(bundle_path, "r:gz") as tf:
            _safe_extract(tf, plugin_dir)
        register_plugin_adapter(
            manifest,
            registry=registry,
            executor=executor,
            plugin_root=plugin_dir,
        )
    except OSError as exc:
        shutil.rmtree(plugin_dir, ignore_errors=True)
        return InstallResult(
            exit_code=_EXIT_IO,
            plugin_id=plugin_id,
            plugin_version=version.version,
            receipt_id=None,
            error_kind="extract_or_register_failed",
            error_message=str(exc),
        )
    except Exception as exc:  # noqa: BLE001 — registry surfaces PluginRegistrationError.
        shutil.rmtree(plugin_dir, ignore_errors=True)
        return InstallResult(
            exit_code=_EXIT_IO,
            plugin_id=plugin_id,
            plugin_version=version.version,
            receipt_id=None,
            error_kind="register_failed",
            error_message=str(exc),
        )

    # --- Phase 7: consent receipt ------------------------------------------
    receipt_id = f"rcpt-{uuid.uuid4().hex[:16]}"
    consent_root = settings.permission_ledger_path.parent / "consent"
    receipt = PluginConsentReceipt(
        receipt_id=receipt_id,
        timestamp_iso=datetime.now(UTC).isoformat(),
        action_type="plugin_install",
        plugin_id=plugin_id,
        plugin_version=version.version,
        slsa_verification=slsa_state,
        trustee_org_name=(
            manifest.pipa_trustee_acknowledgment.trustee_org_name
            if manifest.pipa_trustee_acknowledgment is not None
            else None
        ),
        consent_ledger_position=_consent_ledger_next_position(consent_root),
    )
    try:
        _write_consent_receipt(receipt, consent_root=consent_root)
    except OSError as exc:
        return InstallResult(
            exit_code=_EXIT_IO,
            plugin_id=plugin_id,
            plugin_version=version.version,
            receipt_id=None,
            error_kind="receipt_write_failed",
            error_message=str(exc),
        )

    # --- Phase 8: done -----------------------------------------------------
    logger.info(
        "Installed plugin %s v%s (slsa=%s, receipt=%s)",
        plugin_id,
        version.version,
        slsa_state,
        receipt_id,
    )
    return InstallResult(
        exit_code=_EXIT_OK,
        plugin_id=plugin_id,
        plugin_version=version.version,
        receipt_id=receipt_id,
        error_kind=None,
        error_message=None,
    )


__all__ = [
    "CatalogEntry",
    "CatalogIndex",
    "CatalogVersion",
    "InstallResult",
    "PluginConsentReceipt",
    "install_plugin",
]
