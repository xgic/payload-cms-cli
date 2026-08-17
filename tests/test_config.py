"""Tests for Payload CMS product config helpers."""

from __future__ import annotations

from pathlib import Path

from xgic.cli.payload.config import (
    DEFAULT_COMPOSE_FILE,
    DEFAULT_COMPOSE_PROJECT,
    DEFAULT_CONFIG_FILE,
    DEFAULT_PRIMARY_SERVICE,
    get_compose_project_name,
    get_db_config,
    get_db_profile,
    get_payload_project_name,
)


def test_compose_defaults_match_template_contract() -> None:
    """Defaults must match producer/template service names (not legacy *-dev-containers)."""
    assert DEFAULT_COMPOSE_PROJECT == "xgic-payload-cms-dev"
    assert DEFAULT_PRIMARY_SERVICE == "xgic-payload-cms-dev"
    assert DEFAULT_COMPOSE_FILE == ".devcontainer/docker-compose.yml"
    assert DEFAULT_CONFIG_FILE.as_posix() == ".devcontainer/create-payload-config.json"


def test_get_compose_project_name_from_config(tmp_path, monkeypatch) -> None:
    cfg = tmp_path / "create-payload-config.json"
    cfg.write_text('{"composeProjectName": "xgic-website-pri-dev"}')
    monkeypatch.chdir(tmp_path)
    # Function reads DEFAULT_CONFIG_FILE relative path under .devcontainer/
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "create-payload-config.json").write_text(
        '{"composeProjectName": "xgic-website-pri-dev"}'
    )
    assert get_compose_project_name() == "xgic-website-pri-dev"


def test_get_payload_project_name_fallback(tmp_path: Path) -> None:
    assert get_payload_project_name(tmp_path / "missing.json") == "my-payload-cms"


def test_get_payload_project_name_from_config(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"projectName": "site-a"}')
    assert get_payload_project_name(cfg) == "site-a"


def test_get_db_config(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"dbName": "mydb", "dbUser": "me"}')
    assert get_db_config(cfg) == ("mydb", "me")
    assert get_db_config(tmp_path / "no.json") == ("payload_db", "payload")


def test_get_db_profile(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"dbAdapter": "mongodb"}')
    assert get_db_profile(cfg) == "mongodb"
    cfg.write_text('{"dbAdapter": "postgres"}')
    assert get_db_profile(cfg) == "postgres"
    assert get_db_profile(tmp_path / "no.json") == "postgres"
