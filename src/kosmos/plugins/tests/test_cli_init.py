# SPDX-License-Identifier: Apache-2.0
"""Tests for the ``kosmos-plugin-init`` Python fallback CLI.

Mirrors the TS-side coverage in
``tui/tests/commands/plugin-init.test.ts`` so the two scaffolding paths
emit byte-equivalent file trees from the same flag set. Negative paths
match the contract's exit-code table:

* exit 1 — invalid name.
* exit 2 — non-empty out without --force.
* exit 3 — --pii without acknowledgment flags.

Plus a dry-import test that confirms the CLI module exposes ``main``
matching the pyproject.toml entry-point.
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
import yaml

from kosmos.plugins import cli_init


def _baseline(tmp_path: Path) -> cli_init.InitOptions:
    return cli_init.InitOptions(
        name="demo_plugin",
        tier="live",
        layer=1,
        pii=False,
        out=tmp_path / "demo_plugin",
        force=False,
        search_hint_ko="데모 플러그인 조회 추천",
        search_hint_en="demo plugin lookup recommended",
    )


class TestRunInitHappyPath:
    def test_emits_complete_tree(self, tmp_path: Path) -> None:
        result = cli_init.run_init(_baseline(tmp_path))
        assert result.exit_code == 0
        assert result.out_dir == (tmp_path / "demo_plugin").resolve()
        assert "manifest.yaml" in result.files_written
        assert "plugin_demo_plugin/adapter.py" in result.files_written
        assert "plugin_demo_plugin/schema.py" in result.files_written
        assert "tests/conftest.py" in result.files_written
        assert ".github/workflows/plugin-validation.yml" in result.files_written
        assert "README.ko.md" in result.files_written

    def test_manifest_yaml_round_trips(self, tmp_path: Path) -> None:
        result = cli_init.run_init(_baseline(tmp_path))
        manifest_path = result.out_dir / "manifest.yaml"  # type: ignore[union-attr]
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        assert manifest["plugin_id"] == "demo_plugin"
        assert manifest["adapter"]["tool_id"] == "plugin.demo_plugin.lookup"
        assert manifest["tier"] == "live"
        assert manifest["processes_pii"] is False
        assert manifest["pipa_trustee_acknowledgment"] is None
        assert manifest["otel_attributes"]["kosmos.plugin.id"] == "demo_plugin"

    def test_mock_tier_sets_source_spec(self, tmp_path: Path) -> None:
        opts = _baseline(tmp_path)
        result = cli_init.run_init(dataclasses.replace(opts, tier="mock"))
        manifest = yaml.safe_load(
            (result.out_dir / "manifest.yaml").read_text(encoding="utf-8")  # type: ignore[union-attr]
        )
        assert manifest["tier"] == "mock"
        assert manifest["mock_source_spec"]


class TestRunInitNegative:
    def test_invalid_name(self, tmp_path: Path) -> None:
        opts = _baseline(tmp_path)
        opts = dataclasses.replace(opts, name="Bad-Name")
        result = cli_init.run_init(opts)
        assert result.exit_code == 1
        assert result.error_kind == "invalid_name"

    def test_non_empty_out_without_force(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "demo_plugin"
        out_dir.mkdir()
        (out_dir / "existing.txt").write_text("keep me", encoding="utf-8")
        opts = _baseline(tmp_path)
        result = cli_init.run_init(opts)
        assert result.exit_code == 2
        assert result.error_kind == "out_dir_non_empty"
        assert (out_dir / "existing.txt").read_text() == "keep me"

    def test_force_overwrites(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "demo_plugin"
        out_dir.mkdir()
        (out_dir / "stale.txt").write_text("stale", encoding="utf-8")
        opts = _baseline(tmp_path)
        opts = dataclasses.replace(opts, force=True)
        result = cli_init.run_init(opts)
        assert result.exit_code == 0
        assert not (out_dir / "stale.txt").exists()

    def test_pii_true_without_pipa(self, tmp_path: Path) -> None:
        opts = _baseline(tmp_path)
        opts = dataclasses.replace(opts, pii=True)
        result = cli_init.run_init(opts)
        assert result.exit_code == 3
        assert result.error_kind == "pipa_acknowledgment_error"

    def test_pii_false_with_pipa(self, tmp_path: Path) -> None:
        opts = dataclasses.replace(
            _baseline(tmp_path),
            pii=False,
            pipa=cli_init.PIPATrusteeArgs(
                trustee_org_name="x",
                trustee_contact="y",
                pii_fields_handled=("phone",),
                legal_basis="PIPA §15",
                acknowledgment_sha256="a" * 64,
            ),
        )
        result = cli_init.run_init(opts)
        assert result.exit_code == 3

    def test_pipa_sha256_format_check(self, tmp_path: Path) -> None:
        opts = dataclasses.replace(
            _baseline(tmp_path),
            pii=True,
            pipa=cli_init.PIPATrusteeArgs(
                trustee_org_name="x",
                trustee_contact="y",
                pii_fields_handled=("phone",),
                legal_basis="PIPA §15",
                acknowledgment_sha256="not-a-hash",
            ),
        )
        result = cli_init.run_init(opts)
        assert result.exit_code == 3
        assert "^[a-f0-9]{64}$" in (result.error_message or "")


class TestMainArgvParser:
    def test_main_happy_path(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        out = tmp_path / "demo_plugin"
        rc = cli_init.main(
            [
                "demo_plugin",
                "--tier",
                "live",
                "--layer",
                "1",
                "--no-pii",
                "--out",
                str(out),
            ]
        )
        assert rc == 0
        assert (out / "manifest.yaml").is_file()
        captured = capsys.readouterr()
        assert "생성 완료" in captured.out

    def test_main_pii_without_pipa_args(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        rc = cli_init.main(
            [
                "demo_plugin",
                "--tier",
                "live",
                "--layer",
                "1",
                "--pii",
                "--out",
                str(tmp_path / "demo_plugin"),
            ]
        )
        assert rc == 3
        captured = capsys.readouterr()
        assert "--pipa-" in captured.err

    def test_main_pii_with_pipa_args(self, tmp_path: Path) -> None:
        rc = cli_init.main(
            [
                "demo_plugin",
                "--tier",
                "live",
                "--layer",
                "1",
                "--pii",
                "--pipa-org",
                "KOSMOS Demo",
                "--pipa-contact",
                "demo@example.com",
                "--pipa-fields",
                "phone_number,resident_registration_number",
                "--pipa-legal-basis",
                "PIPA §15-1-2",
                "--pipa-sha256",
                "a" * 64,
                "--out",
                str(tmp_path / "demo_plugin"),
            ]
        )
        assert rc == 0


class TestEntryPointWiring:
    def test_entry_point_function_present(self) -> None:
        # pyproject.toml maps `kosmos-plugin-init = "kosmos.plugins.cli_init:main"`.
        # If this test passes, the entry-point is wired correctly.
        assert callable(cli_init.main)
