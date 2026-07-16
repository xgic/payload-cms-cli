"""Tests for Payload CMS product config helpers."""

from __future__ import annotations

from pathlib import Path

from xgic.cli.payload.config import (
    get_db_config,
    get_db_profile,
    get_payload_project_name,
)


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
