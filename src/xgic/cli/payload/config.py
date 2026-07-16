"""Payload CMS product defaults and config readers.

Used with ``xgic.cli.dev.DockerComposeController`` for the public Payload CMS
Dev Containers template. Core and dev-cli stay free of these product names.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from xgic.cli.core.environment import EnvironmentContext
from xgic.cli.dev.docker import DockerComposeController

DEFAULT_COMPOSE_PROJECT = "xgic-payload-cms-dev-containers"
DEFAULT_PRIMARY_SERVICE = "xgic-payload-cms-dev-containers"
DEFAULT_CONFIG_FILE = Path(".devcontainer/create-payload-config.json")
DEFAULT_COMPOSE_FILE = ".devcontainer/docker-compose.yml"


def get_payload_project_name(
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> str:
    """Return the name of the generated Payload CMS project folder."""
    if config_file.exists():
        try:
            with open(config_file, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            if name := data.get("projectName"):
                return str(name)
        except (json.JSONDecodeError, OSError):
            pass
    return "my-payload-cms"


def get_db_config(
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> tuple[str, str]:
    """Return (db_name, db_user) from create-payload-config.json."""
    default_db = "payload_db"
    default_user = "payload"
    if not config_file.exists():
        return default_db, default_user
    try:
        with config_file.open(encoding="utf-8") as f:
            cfg: dict[str, Any] = json.load(f)
        db_name = cfg.get("dbName") or default_db
        db_user = cfg.get("dbUser") or default_user
        db_uri = cfg.get("dbUri") or ""
        if db_uri and (db_name == default_db or db_user == default_user):
            try:
                if "://" in db_uri:
                    after = db_uri.split("://", 1)[1]
                    if "@" in after and db_user == default_user:
                        creds = after.split("@", 1)[0]
                        if ":" in creds:
                            db_user = creds.split(":", 1)[0] or db_user
                    if "/" in after and db_name == default_db:
                        after_host = after.split("@", 1)[-1]
                        path = after_host.split("/", 1)[-1].split("?")[0]
                        if path:
                            db_name = path or db_name
            except Exception:
                pass
        return db_name, db_user
    except Exception:
        return default_db, default_user


def get_db_profile(config_file: Path = DEFAULT_CONFIG_FILE) -> str:
    """Return compose profile for the active DB adapter (postgres|mongodb)."""
    if not config_file.exists():
        return "postgres"
    try:
        with config_file.open(encoding="utf-8") as f:
            cfg: dict[str, Any] = json.load(f)
        adapter = str(cfg.get("dbAdapter", "postgres")).lower()
        if adapter == "mongodb":
            return "mongodb"
        return "postgres"
    except Exception:
        return "postgres"


def make_payload_docker_controller(
    env: EnvironmentContext,
) -> DockerComposeController:
    """Build a Compose controller with Payload CMS template defaults."""
    return DockerComposeController(
        env=env,
        compose_file=DEFAULT_COMPOSE_FILE,
        project_name=DEFAULT_COMPOSE_PROJECT,
        primary_service=DEFAULT_PRIMARY_SERVICE,
    )


def db_ready(
    docker: DockerComposeController,
    *,
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> bool:
    """Return True if the active DB service accepts connections."""
    service = get_db_profile(config_file)
    if service == "mongodb":
        try:
            result = docker._run_compose(  # noqa: SLF001 — intentional thin probe
                "exec",
                "-T",
                service,
                "mongosh",
                "--quiet",
                "--eval",
                "db.runCommand({ping: 1})",
                capture_output=True,
                check=False,
            )
            return result.returncode == 0
        except Exception:
            return False

    _, db_user = get_db_config(config_file)
    try:
        result = docker._run_compose(  # noqa: SLF001
            "exec",
            "-T",
            "postgres",
            "pg_isready",
            "-U",
            db_user,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False
