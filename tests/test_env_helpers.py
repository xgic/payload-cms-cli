"""Tests for Payload CMS env generation helpers."""

from __future__ import annotations

import re
from pathlib import Path

from xgic.cli.payload.env_helpers import (
    DEFAULT_NEXT_PUBLIC_SERVER_URL,
    compute_synced_project_env_content,
    generate_fresh_env_content,
    load_live_env_from_devcontainer,
    looks_like_placeholder,
    parse_dotenv,
    perform_env_regenerate,
)


def _hex_secret(value: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-f]{64}", value))


def test_generate_fresh_env_content_postgres(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        '{"dbAdapter": "postgres", "dbName": "mydb", "dbUser": "me"}'
    )
    content = generate_fresh_env_content(config_file=cfg)
    assert "POSTGRES_USER=me" in content
    assert "POSTGRES_DB=mydb" in content
    assert "PAYLOAD_SECRET=" in content
    assert "DATABASE_URL=postgres://" in content
    assert "DATABASE_URI=" not in content


def test_generate_fresh_env_content_mongodb(tmp_path: Path) -> None:
    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        '{"dbAdapter": "mongodb", "dbName": "mdb", "dbUser": "mu"}'
    )
    content = generate_fresh_env_content(config_file=cfg)
    assert "MONGO_INITDB_ROOT_USERNAME=mu" in content
    assert "PAYLOAD_SECRET=" in content
    assert "DATABASE_URL=mongodb://" in content
    assert "DATABASE_URI=" not in content


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
    assert "DATABASE_URL=postgres://" in text
    assert "DATABASE_URI=" not in text


def test_compute_synced_migrates_database_uri_only() -> None:
    result = compute_synced_project_env_content(
        "DATABASE_URI=old\nPAYLOAD_SECRET=old\nNEXT_PUBLIC_SERVER_URL=http://localhost:3000\n",
        "postgres://new",
        "newsec",
        cron_secret="c" * 64,
        preview_secret="p" * 64,
    )
    assert "DATABASE_URL=postgres://new" in result
    assert "DATABASE_URI=" not in result
    assert "PAYLOAD_SECRET=newsec" in result


def test_compute_synced_drops_database_uri_when_url_present() -> None:
    result = compute_synced_project_env_content(
        "DATABASE_URL=old-url\nDATABASE_URI=old-uri\nPAYLOAD_SECRET=old\n",
        "postgres://new",
        "newsec",
        cron_secret="c" * 64,
        preview_secret="p" * 64,
    )
    assert "DATABASE_URL=postgres://new" in result
    assert "DATABASE_URI=" not in result


def test_compute_synced_replaces_placeholder_cron_and_preview() -> None:
    original = (
        "DATABASE_URL=old\n"
        "PAYLOAD_SECRET=old\n"
        "CRON_SECRET=YOUR_CRON_SECRET_HERE\n"
        "PREVIEW_SECRET=YOUR_SECRET_HERE\n"
        "NEXT_PUBLIC_SERVER_URL=http://localhost:3000\n"
    )
    result = compute_synced_project_env_content(original, "postgres://new", "newsec")
    parsed = parse_dotenv(result)
    assert parsed["CRON_SECRET"] != "YOUR_CRON_SECRET_HERE"
    assert parsed["PREVIEW_SECRET"] != "YOUR_SECRET_HERE"
    assert _hex_secret(parsed["CRON_SECRET"])
    assert _hex_secret(parsed["PREVIEW_SECRET"])
    assert looks_like_placeholder("YOUR_CRON_SECRET_HERE")
    assert not looks_like_placeholder(parsed["CRON_SECRET"])


def test_compute_synced_preserves_real_secrets_and_public_url() -> None:
    original = (
        "DATABASE_URL=old\n"
        "PAYLOAD_SECRET=old\n"
        "CRON_SECRET=already-real-cron\n"
        "PREVIEW_SECRET=already-real-preview\n"
        "NEXT_PUBLIC_SERVER_URL=http://example.com\n"
        "CUSTOM_KEEP=yes\n"
    )
    result = compute_synced_project_env_content(original, "postgres://new", "newsec")
    parsed = parse_dotenv(result)
    assert parsed["CRON_SECRET"] == "already-real-cron"
    assert parsed["PREVIEW_SECRET"] == "already-real-preview"
    assert parsed["NEXT_PUBLIC_SERVER_URL"] == "http://example.com"
    assert parsed["CUSTOM_KEEP"] == "yes"


def test_compute_synced_sets_default_next_public_server_url() -> None:
    result = compute_synced_project_env_content(
        "DATABASE_URL=old\nPAYLOAD_SECRET=old\n",
        "postgres://new",
        "newsec",
        cron_secret="c" * 64,
        preview_secret="p" * 64,
    )
    assert f"NEXT_PUBLIC_SERVER_URL={DEFAULT_NEXT_PUBLIC_SERVER_URL}" in result


def test_load_live_env_prefers_database_url(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URI", raising=False)
    monkeypatch.delenv("PAYLOAD_SECRET", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URI=postgres://legacy\n"
        "DATABASE_URL=postgres://canonical\n"
        "PAYLOAD_SECRET=sec\n",
        encoding="utf-8",
    )
    db_url, secret = load_live_env_from_devcontainer(env_file)
    assert db_url == "postgres://canonical"
    assert secret == "sec"


def test_load_live_env_falls_back_to_database_uri(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_URI", raising=False)
    monkeypatch.delenv("PAYLOAD_SECRET", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "DATABASE_URI=postgres://legacy\nPAYLOAD_SECRET=sec\n",
        encoding="utf-8",
    )
    db_url, secret = load_live_env_from_devcontainer(env_file)
    assert db_url == "postgres://legacy"
    assert secret == "sec"


def _workspace_with_app_env(
    tmp_path: Path,
    *,
    app_env: str,
    project_dir: str = "app",
) -> tuple[Path, Path, Path]:
    devcontainer = tmp_path / ".devcontainer"
    devcontainer.mkdir()
    cfg = devcontainer / "create-payload-config.json"
    cfg.write_text(
        f'{{"dbAdapter": "postgres", "projectDir": "{project_dir}"}}'
    )
    compose_env = devcontainer / ".env"
    app = tmp_path / project_dir
    app.mkdir()
    app_env_path = app / ".env"
    app_env_path.write_text(app_env, encoding="utf-8")
    return cfg, compose_env, app_env_path


def test_perform_env_regenerate_syncs_app_env(tmp_path: Path) -> None:
    cfg, compose_env, app_env = _workspace_with_app_env(
        tmp_path,
        app_env=(
            "DATABASE_URL=postgres://old:old@postgres:5432/payload_db\n"
            "PAYLOAD_SECRET=old-secret\n"
            "CRON_SECRET=already-real-cron\n"
            "PREVIEW_SECRET=already-real-preview\n"
            "NEXT_PUBLIC_SERVER_URL=http://example.com\n"
            "CUSTOM_KEEP=yes\n"
        ),
    )
    assert (
        perform_env_regenerate(yes=True, env_file=compose_env, config_file=cfg)
        == 0
    )
    compose = parse_dotenv(compose_env.read_text(encoding="utf-8"))
    app = parse_dotenv(app_env.read_text(encoding="utf-8"))
    assert compose["DATABASE_URL"].startswith("postgres://")
    assert app["DATABASE_URL"] == compose["DATABASE_URL"]
    assert app["PAYLOAD_SECRET"] == compose["PAYLOAD_SECRET"]
    assert app["CRON_SECRET"] == "already-real-cron"
    assert app["PREVIEW_SECRET"] == "already-real-preview"
    assert app["NEXT_PUBLIC_SERVER_URL"] == "http://example.com"
    assert app["CUSTOM_KEEP"] == "yes"
    assert "DATABASE_URI" not in app


def test_perform_env_regenerate_replaces_placeholder_cron_preview(
    tmp_path: Path,
) -> None:
    cfg, compose_env, app_env = _workspace_with_app_env(
        tmp_path,
        app_env=(
            "DATABASE_URI=postgres://old:old@postgres:5432/payload_db\n"
            "PAYLOAD_SECRET=old-secret\n"
            "CRON_SECRET=YOUR_CRON_SECRET_HERE\n"
            "PREVIEW_SECRET=YOUR_SECRET_HERE\n"
        ),
    )
    assert (
        perform_env_regenerate(yes=True, env_file=compose_env, config_file=cfg)
        == 0
    )
    app = parse_dotenv(app_env.read_text(encoding="utf-8"))
    assert "DATABASE_URI" not in app
    assert app["DATABASE_URL"].startswith("postgres://")
    assert _hex_secret(app["CRON_SECRET"])
    assert _hex_secret(app["PREVIEW_SECRET"])
    assert app["NEXT_PUBLIC_SERVER_URL"] == DEFAULT_NEXT_PUBLIC_SERVER_URL


def test_perform_env_regenerate_dry_run_does_not_write(tmp_path: Path) -> None:
    original_app = (
        "DATABASE_URL=postgres://old:old@postgres:5432/payload_db\n"
        "PAYLOAD_SECRET=old-secret\n"
        "CRON_SECRET=YOUR_CRON_SECRET_HERE\n"
        "PREVIEW_SECRET=YOUR_SECRET_HERE\n"
    )
    cfg, compose_env, app_env = _workspace_with_app_env(
        tmp_path, app_env=original_app
    )
    compose_env.write_text("PAYLOAD_SECRET=keep-me\n", encoding="utf-8")
    before_compose = compose_env.read_text(encoding="utf-8")
    before_app = app_env.read_text(encoding="utf-8")
    assert (
        perform_env_regenerate(
            dry_run=True, env_file=compose_env, config_file=cfg
        )
        == 0
    )
    assert compose_env.read_text(encoding="utf-8") == before_compose
    assert app_env.read_text(encoding="utf-8") == before_app


def test_perform_env_regenerate_warns_when_volume_exists(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    cfg, compose_env, _app_env = _workspace_with_app_env(
        tmp_path,
        app_env="DATABASE_URL=postgres://old\nPAYLOAD_SECRET=old\n",
    )
    monkeypatch.setattr(
        "xgic.cli.payload.env_helpers.compose_db_volume_exists",
        lambda **_k: True,
    )
    monkeypatch.setattr(
        "xgic.cli.payload.env_helpers.compose_db_volume_name",
        lambda **_k: "example-postgres-data",
    )
    assert (
        perform_env_regenerate(yes=True, env_file=compose_env, config_file=cfg)
        == 0
    )
    captured = capsys.readouterr()
    combined = f"{captured.out}\n{captured.err}"
    assert "example-postgres-data" in combined
    assert "previous password" in combined
    assert "does not change the password" in combined
