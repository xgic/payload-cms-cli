"""Tests for Payload CMS env generation helpers."""

from __future__ import annotations

from pathlib import Path

from xgic.cli.payload.env_helpers import (
    generate_fresh_env_content,
    perform_env_regenerate,
)


def test_generate_fresh_env_content_postgres(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        '{"dbAdapter": "postgres", "dbName": "mydb", "dbUser": "me"}'
    )
    content = generate_fresh_env_content(config_file=cfg)
    assert "POSTGRES_USER=me" in content
    assert "POSTGRES_DB=mydb" in content
    assert "PAYLOAD_SECRET=" in content
    assert "DATABASE_URI=postgres://" in content


def test_generate_fresh_env_content_mongodb(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        '{"dbAdapter": "mongodb", "dbName": "mdb", "dbUser": "mu"}'
    )
    content = generate_fresh_env_content(config_file=cfg)
    assert "MONGO_INITDB_ROOT_USERNAME=mu" in content
    assert "PAYLOAD_SECRET=" in content
    assert "mongodb://" in content


def test_perform_env_regenerate_requires_yes(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    assert perform_env_regenerate(yes=False, env_file=target) == 1
    assert not target.exists()


def test_perform_env_regenerate_dry_run(tmp_path: Path) -> None:
    target = tmp_path / ".env"
    assert perform_env_regenerate(dry_run=True, env_file=target) == 0
    assert not target.exists()


def test_perform_env_regenerate_writes(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text('{"dbAdapter": "postgres"}')
    target = tmp_path / "sub" / ".env"
    assert (
        perform_env_regenerate(yes=True, env_file=target, config_file=cfg) == 0
    )
    assert target.exists()
    text = target.read_text(encoding="utf-8")
    assert "POSTGRES_PASSWORD=" in text
