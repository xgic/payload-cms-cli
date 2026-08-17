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

# Match producer + thin template Compose service names (not legacy *-dev-containers).
DEFAULT_COMPOSE_PROJECT = "xgic-payload-cms-dev"
DEFAULT_PRIMARY_SERVICE = "xgic-payload-cms-dev"
DEFAULT_CONFIG_FILE = Path(".devcontainer/create-payload-config.json")
DEFAULT_COMPOSE_FILE = ".devcontainer/docker-compose.yml"


def get_payload_project_name(
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> str:
    """Return projectName identity (npm/display; not always the filesystem path)."""
    if config_file.exists():
        try:
            with open(config_file, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            if name := data.get("projectName"):
                return str(name)
        except (json.JSONDecodeError, OSError):
            pass
    return "my-payload-cms"


def _is_compose_safe_name(name: str) -> bool:
    """Return True if *name* looks safe for Docker Compose project names."""
    if not name or not name[0].isalnum():
        return False
    return all(c.isalnum() or c in "_-" for c in name) and len(name) <= 63


def _compose_name_from_file(
    compose_path: Path = Path(DEFAULT_COMPOSE_FILE),
) -> str | None:
    """Parse top-level ``name:`` from a Compose file (best-effort)."""
    if not compose_path.is_file():
        return None
    try:
        for line in compose_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("#") or not stripped.startswith("name:"):
                continue
            raw = stripped.split(":", 1)[1].strip().strip("\"'")
            if raw and _is_compose_safe_name(raw.lower()):
                return raw.lower()
    except OSError:
        return None
    return None


def get_compose_project_name(
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> str:
    """Return Docker Compose project name for this workspace.

    Precedence:
    1. ``XGIC_COMPOSE_PROJECT`` environment variable
    2. ``composeProjectName`` in create-payload-config.json
    3. Top-level ``name:`` in ``.devcontainer/docker-compose.yml``
    4. ``DEFAULT_COMPOSE_PROJECT`` (producer template default)
    """
    import os

    env_name = os.environ.get("XGIC_COMPOSE_PROJECT", "").strip().lower()
    if env_name and _is_compose_safe_name(env_name):
        return env_name

    if config_file.exists():
        try:
            with open(config_file, encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
            raw = data.get("composeProjectName")
            if isinstance(raw, str) and raw.strip():
                name = raw.strip().lower()
                if _is_compose_safe_name(name):
                    return name
        except (json.JSONDecodeError, OSError):
            pass

    from_file = _compose_name_from_file()
    if from_file:
        return from_file

    return DEFAULT_COMPOSE_PROJECT

def get_payload_project_dir(
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> Path:
    """Return resolved app directory Path (see layout.resolve_project_dir)."""
    from xgic.cli.payload.layout import resolve_project_dir
    from xgic.cli.payload.project import load_create_payload_config

    return resolve_project_dir(load_create_payload_config(config_file))


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
    """Build a Docker Compose controller with Payload CMS template defaults."""
    return DockerComposeController(
        env=env,
        compose_file=DEFAULT_COMPOSE_FILE,
        project_name=get_compose_project_name(),
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
