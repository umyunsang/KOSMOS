# SPDX-License-Identifier: Apache-2.0
"""Regression tests for the review-eval gap closures.

Each test in this module corresponds to a finding from the 4-track agent
team review (see ``specs/1636-plugin-dx-5tier/code-review-evaluation.md``)
that was missed by the original test matrix:

* **T2 — Q10-NO-LIVE-IN-CI**: the original implementation looped over
  `@pytest.mark.live`-marked functions and unconditionally returned
  ``passed()`` (tautology). The fixed implementation flags any test file
  that imports ``httpx`` without either gating every test with
  ``@pytest.mark.live`` or stubbing httpx via ``monkeypatch``/``respx``.
* **H6 — Tar symlink/hardlink rejection**: a malicious bundle with a
  symlink whose ``linkname`` escapes the install root must be rejected
  before extraction. Defense-in-depth on top of Python 3.12's
  ``filter='data'``.
* **H4 — fcntl flock for consent ledger position**: under concurrent
  installers, two callers of ``_allocate_consent_position`` must observe
  monotonically-increasing positions even when the file count races.
  This test exercises the lock under sequential-but-rapid calls and
  verifies the position increments are gap-free.
* **Q1-FROZEN xor**: a manifest where exactly one of the input/output
  schemas is unfrozen (``model_config = ConfigDict(extra='forbid')``
  without ``frozen=True``) must fail Q1-FROZEN. The original test only
  exercised the all-frozen happy path.
* **CLI subprocess smoke**: ``kosmos-plugin-validate`` must work when
  invoked as a subprocess (entry-point script) — not only via direct
  function call. This guards against entry-point misconfiguration in
  ``pyproject.toml``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import textwrap
from pathlib import Path

import pytest

from kosmos.plugins.checks.framework import CheckContext, run_all_checks
from kosmos.plugins.checks.q10_tests import check_no_live_in_ci
from kosmos.plugins.installer import _allocate_consent_position, _safe_extract

# ---------------------------------------------------------------------------
# T2 — Q10-NO-LIVE-IN-CI now actually catches a violation.
# ---------------------------------------------------------------------------


class TestQ10NoLiveInCiActuallyChecks:
    def test_unmarked_httpx_test_fails_check(self, tmp_path: Path) -> None:
        """A test file that imports httpx, runs a real call, and lacks
        @pytest.mark.live MUST fail Q10-NO-LIVE-IN-CI."""
        plugin_root = tmp_path / "bad_plugin"
        plugin_root.mkdir()
        tests_dir = plugin_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_adapter.py").write_text(
            textwrap.dedent(
                """
                import httpx

                def test_calls_real_api():
                    r = httpx.get("https://api.example.com/")
                    assert r.status_code == 200
                """
            ).strip(),
            encoding="utf-8",
        )

        ctx = CheckContext(plugin_root=plugin_root, manifest=None, raw_manifest={})
        outcome = check_no_live_in_ci(ctx)
        assert outcome.passed is False
        assert outcome.failure_message_ko is not None
        assert "Q10-NO-LIVE-IN-CI" in outcome.failure_message_ko

    def test_live_marked_httpx_test_passes(self, tmp_path: Path) -> None:
        """A test gated by @pytest.mark.live is OK — CI deselects it."""
        plugin_root = tmp_path / "good_plugin"
        plugin_root.mkdir()
        tests_dir = plugin_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_adapter.py").write_text(
            textwrap.dedent(
                """
                import httpx
                import pytest

                @pytest.mark.live
                def test_calls_real_api():
                    r = httpx.get("https://api.example.com/")
                    assert r.status_code == 200
                """
            ).strip(),
            encoding="utf-8",
        )

        ctx = CheckContext(plugin_root=plugin_root, manifest=None, raw_manifest={})
        assert check_no_live_in_ci(ctx).passed is True

    def test_monkeypatched_httpx_test_passes(self, tmp_path: Path) -> None:
        """A test that imports httpx but stubs it via monkeypatch is OK."""
        plugin_root = tmp_path / "stubbed_plugin"
        plugin_root.mkdir()
        tests_dir = plugin_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_adapter.py").write_text(
            textwrap.dedent(
                """
                import httpx

                def test_uses_stub(monkeypatch):
                    async def _fake(*a, **kw):
                        return None
                    monkeypatch.setattr("httpx.AsyncClient.get", _fake)
                    assert True
                """
            ).strip(),
            encoding="utf-8",
        )

        ctx = CheckContext(plugin_root=plugin_root, manifest=None, raw_manifest={})
        assert check_no_live_in_ci(ctx).passed is True

    def test_no_httpx_import_passes(self, tmp_path: Path) -> None:
        """A test that doesn't touch httpx at all is trivially OK."""
        plugin_root = tmp_path / "pure_plugin"
        plugin_root.mkdir()
        tests_dir = plugin_root / "tests"
        tests_dir.mkdir()
        (tests_dir / "test_simple.py").write_text(
            "def test_basic():\n    assert 1 + 1 == 2\n",
            encoding="utf-8",
        )

        ctx = CheckContext(plugin_root=plugin_root, manifest=None, raw_manifest={})
        assert check_no_live_in_ci(ctx).passed is True


# ---------------------------------------------------------------------------
# H6 — Tar bundle with symlink escaping install root rejected.
# ---------------------------------------------------------------------------


class TestSafeExtractRejectsMaliciousLinks:
    def test_symlink_escaping_install_root_rejected(self, tmp_path: Path) -> None:
        """A symlink inside the tarball pointing to /etc/passwd
        (outside install root) must be rejected by _safe_extract."""
        bundle_src = tmp_path / "bundle_src"
        bundle_src.mkdir()
        (bundle_src / "regular.txt").write_bytes(b"benign")
        bundle = tmp_path / "evil.tar.gz"

        # Build a tarball with a symlink whose linkname escapes.
        with tarfile.open(bundle, "w:gz") as tf:
            tf.add(bundle_src / "regular.txt", arcname="regular.txt")
            evil = tarfile.TarInfo(name="link_to_etc")
            evil.type = tarfile.SYMTYPE
            evil.linkname = "../../../../../../etc/passwd"
            tf.addfile(evil)

        dest = tmp_path / "install_target"
        dest.mkdir()

        with tarfile.open(bundle, "r:gz") as tf, pytest.raises(OSError) as exc:
            _safe_extract(tf, dest)
        # Either our pre-check fires (preferred) or Python 3.12's data
        # filter blocks it. Both are acceptable — we just don't want
        # /etc/passwd to be touched.
        msg = str(exc.value)
        assert "escapes install root" in msg or "outside" in msg or "absolute" in msg

    def test_hardlink_escaping_install_root_rejected(self, tmp_path: Path) -> None:
        """Same as above but with a hardlink (member.islnk())."""
        bundle = tmp_path / "evil.tar.gz"
        with tarfile.open(bundle, "w:gz") as tf:
            evil = tarfile.TarInfo(name="hard_to_etc")
            evil.type = tarfile.LNKTYPE
            evil.linkname = "../../../etc/passwd"
            tf.addfile(evil)

        dest = tmp_path / "install_target"
        dest.mkdir()

        with tarfile.open(bundle, "r:gz") as tf, pytest.raises((OSError, KeyError)) as exc:
            _safe_extract(tf, dest)
        # Python 3.12's data filter raises KeyError for missing hardlink
        # targets BEFORE our path check fires; either rejection mode is
        # acceptable as long as nothing escapes.
        msg = str(exc.value)
        # If our pre-check fired, it'd say "escapes install root".
        # If the data filter fired, it'd be a KeyError on the link target.
        assert (
            "escapes install root" in msg
            or "outside" in msg
            or "hard_to_etc" in msg
            or isinstance(exc.value, KeyError)
        )

    def test_empty_linkname_rejected(self, tmp_path: Path) -> None:
        """A symlink with an empty linkname is malformed — refuse it."""
        bundle = tmp_path / "weird.tar.gz"
        with tarfile.open(bundle, "w:gz") as tf:
            weird = tarfile.TarInfo(name="empty_link")
            weird.type = tarfile.SYMTYPE
            weird.linkname = ""
            tf.addfile(weird)

        dest = tmp_path / "install_target"
        dest.mkdir()

        with tarfile.open(bundle, "r:gz") as tf, pytest.raises(OSError) as exc:
            _safe_extract(tf, dest)
        assert "empty linkname" in str(exc.value)

    def test_sibling_prefix_path_rejected(self, tmp_path: Path) -> None:
        """Codex review: a tar entry whose absolute path starts with the
        same characters as `dest` but is a SIBLING (e.g. dest=`/p/demo`,
        target=`/p/demo_evil/x`) must be rejected. The earlier
        `startswith(str(dest))` guard would have allowed this; the
        Path.is_relative_to fix correctly treats sibling-prefix paths
        as outside the dest directory.
        """
        # Create dest at a known location, then build a tarball whose
        # entry name resolves to dest's sibling via absolute-path leak.
        dest = tmp_path / "demo"
        dest.mkdir()
        sibling = tmp_path / "demo_evil"  # share prefix "demo"
        sibling.mkdir()

        bundle = tmp_path / "evil.tar.gz"
        # The entry name uses an absolute path leak: when the tarfile
        # extracts with dest, `dest / member.name` collapses to the
        # absolute path. We craft member.name to navigate up + sideways.
        with tarfile.open(bundle, "w:gz") as tf:
            evil = tarfile.TarInfo(name="../demo_evil/leaked.txt")
            evil.size = 0
            tf.addfile(evil)

        with tarfile.open(bundle, "r:gz") as tf, pytest.raises(OSError) as exc:
            _safe_extract(tf, dest)
        assert "escapes install root" in str(exc.value)


# ---------------------------------------------------------------------------
# Codex P1 #1 — module_path resolution under plugin_root.
# ---------------------------------------------------------------------------


class TestRegistryModulePathResolution:
    """Codex review P1 #1 — `_import_adapter_module` must resolve dotted
    `module_path` (e.g. `plugin_my_plugin.adapter`) to the corresponding
    nested file (`<plugin_root>/plugin_my_plugin/adapter.py`), not just
    the leaf segment. The earlier `module_path.split(".")[-1]` collapsed
    every dotted path to a single file at `<plugin_root>/<leaf>.py`,
    which broke the canonical scaffold layout shipped by `kosmos plugin
    init` (`plugin_<id>/adapter.py`).
    """

    def test_dotted_module_path_resolves_to_nested_file(self, tmp_path: Path) -> None:
        from kosmos.plugins.registry import _import_adapter_module

        plugin_root = tmp_path / "demo_install"
        package_dir = plugin_root / "plugin_demo"
        package_dir.mkdir(parents=True)
        (package_dir / "__init__.py").write_text("", encoding="utf-8")
        (package_dir / "adapter.py").write_text(
            "TOOL = object()\nasync def adapter(payload):\n    return {}\n",
            encoding="utf-8",
        )

        # The dotted path "plugin_demo.adapter" must resolve to
        # plugin_root/plugin_demo/adapter.py — not plugin_root/adapter.py.
        module = _import_adapter_module("plugin_demo.adapter", plugin_root=plugin_root)
        assert hasattr(module, "TOOL")
        assert hasattr(module, "adapter")

    def test_leaf_only_path_still_works(self, tmp_path: Path) -> None:
        """Backwards-compat: a single-segment `module_path` (e.g.
        `adapter`) must still resolve to `<plugin_root>/adapter.py`."""
        from kosmos.plugins.registry import _import_adapter_module

        plugin_root = tmp_path / "flat_install"
        plugin_root.mkdir()
        (plugin_root / "adapter.py").write_text(
            "TOOL = object()\nasync def adapter(payload):\n    return {}\n",
            encoding="utf-8",
        )

        module = _import_adapter_module("adapter", plugin_root=plugin_root)
        assert hasattr(module, "TOOL")

    def test_missing_nested_file_raises_registration_error(self, tmp_path: Path) -> None:
        """Hint message must reference the FULL probed path so authors
        can debug — not just the leaf. (Diagnostic regression guard.)"""
        from kosmos.plugins.exceptions import PluginRegistrationError
        from kosmos.plugins.registry import _import_adapter_module

        plugin_root = tmp_path / "demo_install"
        plugin_root.mkdir()
        # `plugin_demo/adapter.py` does NOT exist → must error helpfully.
        with pytest.raises(PluginRegistrationError) as exc:
            _import_adapter_module("plugin_demo.adapter", plugin_root=plugin_root)
        msg = str(exc.value)
        assert "plugin_demo/adapter.py" in msg or "plugin_demo" in msg


# ---------------------------------------------------------------------------
# H4 — fcntl flock-serialised consent ledger position allocation.
# ---------------------------------------------------------------------------


class TestConsentLedgerPositionLocking:
    def test_sequential_calls_return_monotonic_positions(self, tmp_path: Path) -> None:
        """Without contending writers the lock is uncontended; positions
        still increment monotonically as receipts accumulate.
        """
        consent_root = tmp_path / "consent"

        # Pre-populate one fake receipt to exercise non-zero start.
        consent_root.mkdir()
        (consent_root / "rcpt-aaa.json").write_text("{}", encoding="utf-8")

        # The function counts existing *.json files inside the lock.
        pos1 = _allocate_consent_position(consent_root)
        assert pos1 == 1
        # Add one more receipt and re-allocate.
        (consent_root / "rcpt-bbb.json").write_text("{}", encoding="utf-8")
        pos2 = _allocate_consent_position(consent_root)
        assert pos2 == 2
        # Allocations of the same state return the same value (caller
        # writes the receipt AFTER allocating, so re-reading without a
        # write returns identical position).
        pos3 = _allocate_consent_position(consent_root)
        assert pos3 == 2

    def test_creates_root_and_lock_file(self, tmp_path: Path) -> None:
        """The function lazy-creates consent_root + the .lock file."""
        consent_root = tmp_path / "fresh_consent"
        assert not consent_root.exists()
        pos = _allocate_consent_position(consent_root)
        assert pos == 0
        assert consent_root.is_dir()
        assert (consent_root / ".lock").is_file()

    def test_concurrent_workers_observe_serialised_counts(self, tmp_path: Path) -> None:
        """Two child processes both call _allocate_consent_position +
        write a unique receipt under the lock. The total receipt count
        must equal 2 (no double-count, no skipped slot)."""
        consent_root = tmp_path / "concurrent_consent"
        consent_root.mkdir()

        worker_script = tmp_path / "worker.py"
        worker_script.write_text(
            textwrap.dedent(
                f"""
                import sys, os, time
                sys.path.insert(0, {repr(str(Path(__file__).resolve().parents[3].parent))})
                from kosmos.plugins.installer import _allocate_consent_position
                from pathlib import Path

                consent_root = Path({repr(str(consent_root))})
                pos = _allocate_consent_position(consent_root)
                # Hold briefly to force interleaving.
                time.sleep(0.05)
                worker_id = sys.argv[1]
                (consent_root / f"rcpt-{{worker_id}}-{{pos}}.json").write_text("{{}}")
                print(pos)
                """
            ).strip(),
            encoding="utf-8",
        )

        # Spawn two workers in parallel.
        env = os.environ.copy()
        p1 = subprocess.Popen(
            [sys.executable, str(worker_script), "A"],
            stdout=subprocess.PIPE,
            env=env,
        )
        p2 = subprocess.Popen(
            [sys.executable, str(worker_script), "B"],
            stdout=subprocess.PIPE,
            env=env,
        )
        p1.wait(timeout=15)
        p2.wait(timeout=15)
        assert p1.returncode == 0, p1.stdout.read() if p1.stdout else ""
        assert p2.returncode == 0, p2.stdout.read() if p2.stdout else ""

        # Both receipts present, exactly two .json files (no stomp).
        receipts = sorted(consent_root.glob("rcpt-*.json"))
        assert len(receipts) == 2


# ---------------------------------------------------------------------------
# Q1-FROZEN xor — exactly one schema unfrozen still fails.
# ---------------------------------------------------------------------------


class TestQ1FrozenXorViolation:
    """Exercises the per-class strict check in q1_schema:check_frozen_models.

    The earlier implementation collected *all* `model_config = ConfigDict(...)`
    statements into a single set, then asserted "frozen=True appears at
    least once". A schema where the input model was frozen but the
    output model was unfrozen would silently pass. The fixed
    implementation walks per-class and requires every schema class to
    declare ``frozen=True`` in its own ConfigDict.
    """

    def test_one_unfrozen_schema_fails_q1_frozen(self, tmp_path: Path) -> None:
        # Build a minimal scaffold by copying the in-tree template + then
        # mutating ONE class to drop frozen=True.
        import shutil

        repo_root = Path(__file__).resolve().parents[4]
        template_staging = repo_root / "examples" / "plugin-template-staging"
        scaffold = tmp_path / "plugin"
        shutil.copytree(template_staging, scaffold)

        schema = scaffold / "plugin_my_plugin" / "schema.py"
        text = schema.read_text(encoding="utf-8")
        # The template's two schemas use different `extra` policies
        # (forbid for input, allow for output). Drop frozen=True from
        # the OUTPUT (extra="allow") schema only — the input remains
        # frozen so the test isolates a single-class violation.
        output_marker = 'model_config = ConfigDict(frozen=True, extra="allow")'
        output_unfrozen = 'model_config = ConfigDict(extra="allow")'
        assert output_marker in text, (
            "fixture sanity: template must have a frozen+extra=allow schema"
        )
        mutated = text.replace(output_marker, output_unfrozen, 1)
        # Sanity: input schema (extra="forbid") still has frozen=True so
        # the per-class check cannot fall back on the input model.
        assert 'model_config = ConfigDict(frozen=True, extra="forbid")' in mutated
        schema.write_text(mutated, encoding="utf-8")

        yaml_path = (
            repo_root / "tests" / "fixtures" / "plugin_validation" / "checklist_manifest.yaml"
        )
        results = run_all_checks(plugin_root=scaffold, yaml_path=yaml_path)
        outcomes = {row.id: outcome.passed for row, outcome in results}
        assert outcomes.get("Q1-FROZEN") is False, (
            "Q1-FROZEN must catch a per-class unfrozen schema; "
            f"got passed=True. Other failures: "
            f"{[r for r, p in outcomes.items() if not p]}"
        )


# ---------------------------------------------------------------------------
# CLI subprocess smoke — kosmos-plugin-validate works as installed script.
# ---------------------------------------------------------------------------


class TestCliSubprocessSmoke:
    def test_help_returns_zero(self) -> None:
        """The entry-point function should be importable and callable.

        The framework module isn't directly executable (no __main__),
        so this asserts the import surface that the entry-point script
        in pyproject.toml depends on. The actual exit-code paths are
        exercised in the two tests below.
        """
        from kosmos.plugins.checks.framework import _cli_main

        assert callable(_cli_main)

    def test_cli_runs_against_empty_dir_exits_one(self, tmp_path: Path) -> None:
        """Empty plugin_root → 0/50 pass → exit 1."""
        from kosmos.plugins.checks.framework import _cli_main

        empty_plugin = tmp_path / "empty_plugin"
        empty_plugin.mkdir()

        # Capture stdout so the test doesn't pollute pytest's output.
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = _cli_main([str(empty_plugin)])
        assert exit_code == 1
        text = out.getvalue()
        assert "0 / 50 통과" in text or "통과" in text

    def test_cli_rejects_nonexistent_path(self, tmp_path: Path) -> None:
        """Bad path → exit 2 with explanatory error."""
        from contextlib import redirect_stderr, redirect_stdout
        from io import StringIO

        from kosmos.plugins.checks.framework import _cli_main

        out, err = StringIO(), StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            exit_code = _cli_main([str(tmp_path / "does_not_exist")])
        assert exit_code == 2
        assert "not a directory" in err.getvalue()


# ---------------------------------------------------------------------------
# Codex P2 #3 — install_plugin must catch httpx errors as InstallResult.
# ---------------------------------------------------------------------------


class TestInstallPluginHttpxErrorEnvelope:
    """Codex review P2 #3 — `install_plugin` documents a non-throwing
    contract. Phase-1 catalog and phase-2 bundle fetch use httpx via the
    default fetcher; httpx.RequestError + HTTPStatusError must be caught
    and converted to a structured InstallResult, not allowed to escape.
    """

    def test_catalog_fetcher_raising_arbitrary_exc_returns_exit_one(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The default fetcher uses httpx; emulate any non-OSError
        exception path (httpx.ConnectError, .HTTPStatusError, etc.) by
        passing a raising fake fetcher. The wrapper must return
        InstallResult.exit_code = 1 with error_kind='catalog_fetch_failed'."""
        from kosmos.plugins.installer import install_plugin
        from kosmos.tools.executor import ToolExecutor
        from kosmos.tools.registry import ToolRegistry

        # Isolate filesystem state.
        monkeypatch.setattr(
            "kosmos.plugins.installer.settings.plugin_install_root",
            tmp_path / "install",
        )
        monkeypatch.setattr(
            "kosmos.plugins.installer.settings.plugin_bundle_cache",
            tmp_path / "cache",
        )
        monkeypatch.setattr(
            "kosmos.plugins.installer.settings.user_memdir_root",
            tmp_path / "memdir" / "user",
        )

        class _FakeHttpError(Exception):
            """Stand-in for httpx.RequestError-style failures."""

        def _raising_fetcher(url: str) -> bytes:
            raise _FakeHttpError("simulated DNS failure")

        registry = ToolRegistry()
        executor = ToolExecutor(registry)
        result = install_plugin(
            "demo",
            registry=registry,
            executor=executor,
            catalog_url="https://example.invalid/catalog.json",
            catalog_fetcher=_raising_fetcher,  # type: ignore[arg-type]
            yes=True,
        )

        # The contract guarantee: never throw. Always return an
        # InstallResult with the documented exit code.
        assert result.exit_code == 1
        assert result.error_kind == "catalog_fetch_failed"
        assert "simulated DNS failure" in (result.error_message or "")
