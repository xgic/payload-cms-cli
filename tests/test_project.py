"""Unit tests for Payload CMS project helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from xgic.cli.payload.env_helpers import compute_synced_project_env_content
from xgic.cli.payload.project import (
    NATIVE_PNPM_BUILDS,
    build_create_payload_command,
    ensure_payload_project,
    get_project_name,
    is_payload_project_complete,
    load_create_payload_config,
    merge_package_json_only_built,
    merge_workspace_allow_builds,
    parse_yaml_map_key,
    pnpx_allow_build_args,
    resolve_db_connection_string,
    sync_compose_project_name,
    validate_compose_project_name,
    yaml_map_key,
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
        assert cfg["layout"] == "auto"

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
        assert "DATABASE_URI=" not in result

    def test_build_create_payload_command_basic(self) -> None:
        cmd = build_create_payload_command("app")
        assert "create-payload-app@latest" in cmd
        assert "app" in cmd
        assert "--use-pnpm" in cmd
        assert "--no-agent" in cmd
        assert "--allow-build=@swc/core" in cmd
        pkg = cmd.index("create-payload-app@latest")
        assert cmd[0] == "pnpx"
        assert cmd[pkg + 1] == "app"

    def test_build_create_payload_command_root(self) -> None:
        cmd = build_create_payload_command(".")
        pkg = cmd.index("create-payload-app@latest")
        assert cmd[pkg + 1] == "."

    def test_pnpx_allow_build_args(self) -> None:
        flags = pnpx_allow_build_args()
        assert flags[0] == "--allow-build=@swc/core"
        assert set(flags) == {f"--allow-build={n}" for n in NATIVE_PNPM_BUILDS}

    def test_merge_package_json_only_built_adds_missing(self) -> None:
        old = json.dumps(
            {"name": "app", "pnpm": {"onlyBuiltDependencies": ["sharp"]}}
        )
        new = json.loads(merge_package_json_only_built(old))
        deps = new["pnpm"]["onlyBuiltDependencies"]
        assert "sharp" in deps
        assert "@swc/core" in deps
        assert deps.index("sharp") == 0

    def test_merge_package_json_only_built_noop(self) -> None:
        old = json.dumps(
            {"pnpm": {"onlyBuiltDependencies": list(NATIVE_PNPM_BUILDS)}}
        )
        assert merge_package_json_only_built(old) == old

    def test_yaml_map_key_quotes_scoped_names(self) -> None:
        assert yaml_map_key("esbuild") == "esbuild"
        assert yaml_map_key("@swc/core") == '"@swc/core"'
        assert parse_yaml_map_key('"@swc/core"') == "@swc/core"
        assert parse_yaml_map_key("esbuild") == "esbuild"

    def test_merge_workspace_allow_builds_appends(self) -> None:
        old = (
            "allowBuilds:\n"
            "  esbuild: true\n"
            "  sharp: true\n"
            "  unrs-resolver: true\n"
            "  workerd: true\n"
        )
        new = merge_workspace_allow_builds(old)
        assert '  "@swc/core": true\n' in new
        assert '  "@parcel/watcher": true\n' in new
        assert "  @swc/core: true\n" not in new
        assert "  esbuild: true\n" in new

    def test_merge_workspace_allow_builds_repairs_unquoted_at_keys(
        self,
    ) -> None:
        old = (
            "allowBuilds:\n"
            "  esbuild: true\n"
            "  @swc/core: true\n"
        )
        new = merge_workspace_allow_builds(old)
        assert '  "@swc/core": true\n' in new
        assert "  @swc/core: true\n" not in new

    def test_merge_workspace_allow_builds_creates_block(self) -> None:
        new = merge_workspace_allow_builds("packages:\n  - .\n")
        assert new.startswith("packages:\n  - .\nallowBuilds:\n")
        assert '  "@swc/core": true\n' in new

    def test_ensure_idempotent_on_complete(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        proj = tmp_path / "app"
        proj.mkdir()
        (proj / "src").mkdir()
        (proj / "src" / "payload.config.ts").write_text("// ok")
        (tmp_path / ".devcontainer").mkdir()
        (tmp_path / ".devcontainer" / ".env").write_text("PAYLOAD_SECRET=test\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "xgic.cli.payload.project.load_create_payload_config",
            lambda *a, **k: {
                "projectName": "my-payload-cms",
                "projectDir": "app",
                "layout": "subdir",
            },
        )
        monkeypatch.setattr(
            "xgic.cli.payload.project.ensure_db_services",
            lambda **k: 0,
        )
        assert ensure_payload_project() == 0

    def test_validate_compose_project_name(self) -> None:
        assert validate_compose_project_name("Website") == "website"
        with pytest.raises(ValueError):
            validate_compose_project_name("-bad")

    def test_sync_compose_project_name(self, tmp_path: Path) -> None:
        compose = tmp_path / "docker-compose.yml"
        compose.write_text("name: old-name\nservices: {}\n")
        assert sync_compose_project_name("my-app", compose_path=compose) is True
        assert "name: my-app" in compose.read_text()

    def test_ensure_fails_when_create_payload_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / ".devcontainer").mkdir()
        (tmp_path / ".devcontainer" / ".env").write_text("PAYLOAD_SECRET=test\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "xgic.cli.payload.project.load_create_payload_config",
            lambda *a, **k: {
                "projectName": "fail-app",
                "projectDir": "app",
                "layout": "subdir",
                "template": "website",
                "dbAdapter": "postgres",
                "agent": "none",
                "dbUri": "",
            },
        )
        monkeypatch.setattr(
            "xgic.cli.payload.project.ensure_db_services",
            lambda **k: 0,
        )

        class FakeResult:
            returncode = 7

        monkeypatch.setattr(
            "xgic.cli.payload.project.subprocess.run",
            lambda *a, **k: FakeResult(),
        )
        assert ensure_payload_project(quiet=True) == 7

    def test_ensure_missing_tool_message(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / ".devcontainer").mkdir()
        (tmp_path / ".devcontainer" / ".env").write_text("PAYLOAD_SECRET=test\n")
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(
            "xgic.cli.payload.project.load_create_payload_config",
            lambda *a, **k: {
                "projectName": "x",
                "projectDir": "app",
                "layout": "subdir",
                "template": "website",
                "dbAdapter": "postgres",
                "agent": "none",
                "dbUri": "",
            },
        )
        monkeypatch.setattr(
            "xgic.cli.payload.project.ensure_db_services",
            lambda **k: 0,
        )

        def boom(*a, **k):
            raise FileNotFoundError("pnpx")

        monkeypatch.setattr(
            "xgic.cli.payload.project.subprocess.run",
            boom,
        )
        assert ensure_payload_project(quiet=True) == 1
