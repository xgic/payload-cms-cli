"""Tests for Payload CMS product config helpers."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from xgic.cli.payload.config import (
    DEFAULT_COMPOSE_FILE,
    DEFAULT_COMPOSE_PROJECT,
    DEFAULT_CONFIG_FILE,
    DEFAULT_PRIMARY_SERVICE,
    db_ready,
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
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XGIC_COMPOSE_PROJECT", raising=False)
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "create-payload-config.json").write_text(
        '{"composeProjectName": "xgic-website-pri-dev"}'
    )
    assert get_compose_project_name() == "xgic-website-pri-dev"


def test_get_compose_project_name_from_env(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("XGIC_COMPOSE_PROJECT", "xgic-website-pri-dev")
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "create-payload-config.json").write_text("{}")
    assert get_compose_project_name() == "xgic-website-pri-dev"


def test_get_compose_project_name_from_compose_file(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("XGIC_COMPOSE_PROJECT", raising=False)
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "docker-compose.yml").write_text(
        "name: xgic-website-pri-dev\nservices: {}\n"
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


def test_db_ready_pg_isready_uses_configured_database(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        '{"dbName": "payload_db", "dbUser": "payload", "dbAdapter": "postgres"}'
    )
    docker = MagicMock()
    docker._run_compose.return_value = MagicMock(returncode=0)
    assert db_ready(docker, config_file=cfg) is True
    args = docker._run_compose.call_args[0]
    assert args[:4] == ("exec", "-T", "postgres", "pg_isready")
    assert args[args.index("-U") + 1] == "payload"
    assert args[args.index("-d") + 1] == "payload_db"


def test_db_ready_pg_isready_uses_custom_db_name(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"dbName": "site_db", "dbUser": "site", "dbAdapter": "postgres"}')
    docker = MagicMock()
    docker._run_compose.return_value = MagicMock(returncode=0)
    assert db_ready(docker, config_file=cfg) is True
    args = docker._run_compose.call_args[0]
    assert args[args.index("-U") + 1] == "site"
    assert args[args.index("-d") + 1] == "site_db"
