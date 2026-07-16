"""Unit tests for Payload CMS project helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from xgic.cli.payload.project import (
    build_create_payload_command,
    compute_synced_project_env_content,
    ensure_payload_project,
    get_project_name,
    is_payload_project_complete,
    load_create_payload_config,
    resolve_db_connection_string,
)


class TestProjectPureHelpers:
    @pytest.mark.parametrize(
        "config_data, expected_name",
        [
            ({"projectName": "my-app"}, "my-app"),
            ({"projectName": "  spaced  "}, "spaced"),
            ({"projectName": ""}, "my-payload-cms"),
            ({}, "my-payload-cms"),
        ],
    )
    def test_get_project_name_variants(
        self, tmp_path: Path, config_data: dict, expected_name: str
    ) -> None:
        cfg_path = tmp_path / "cfg.json"
        cfg_path.write_text(json.dumps(config_data))
        cfg = load_create_payload_config(cfg_path)
        assert get_project_name(cfg) == expected_name

    @pytest.mark.parametrize(
        "files_present, expected_complete",
        [
            (["payload.config.ts"], True),
            (["src/payload.config.js"], True),
            ([], False),
            (["README.md"], False),
        ],
    )
    def test_is_payload_project_complete_layouts(
        self,
        tmp_path: Path,
        files_present: list[str],
        expected_complete: bool,
    ) -> None:
        proj = tmp_path / "layout-test"
        proj.mkdir()
        for f in files_present:
            p = proj / f
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text("// payload config")
        assert is_payload_project_complete(proj) is expected_complete

    def test_load_defaults_when_missing(self, tmp_path: Path) -> None:
        cfg = load_create_payload_config(tmp_path / "no-config.json")
        assert cfg["projectName"] == "my-payload-cms"
        assert cfg["dbAdapter"] == "postgres"

    def test_resolve_db_connection_string(self) -> None:
        assert (
            resolve_db_connection_string("postgres://json", "postgres://live")
            == "postgres://live"
        )
        assert resolve_db_connection_string("postgres://json", "") == "postgres://json"
        assert resolve_db_connection_string("", "") is None

    def test_compute_synced_project_env_content(self) -> None:
        result = compute_synced_project_env_content(
            "DATABASE_URL=old\nPAYLOAD_SECRET=old", "newdb", "newsec"
        )
        assert "DATABASE_URL=newdb" in result
        assert "PAYLOAD_SECRET=newsec" in result

    def test_build_create_payload_command_basic(self) -> None:
        cmd = build_create_payload_command("website")
        assert "create-payload-app@latest" in cmd
        assert "--use-pnpm" in cmd
        assert "--no-agent" in cmd

    def test_ensure_idempotent_on_complete(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        proj = tmp_path / "complete-site"
        proj.mkdir()
        (proj / "src").mkdir()
        (proj / "src" / "payload.config.ts").write_text("// ok")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "xgic.cli.payload.project.load_create_payload_config",
            lambda *a, **k: {"projectName": "complete-site"},
        )
        assert ensure_payload_project() == 0
