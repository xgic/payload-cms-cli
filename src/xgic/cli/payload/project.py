"""Payload CMS project setup / ensure helpers."""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from xgic.cli.payload.config import (
    DEFAULT_COMPOSE_FILE,
    DEFAULT_CONFIG_FILE,
    db_ready,
    get_compose_project_name,
    get_db_profile,
    make_payload_docker_controller,
)
from xgic.cli.payload.layout import (
    create_payload_target_arg,
    display_project_location,
    resolve_project_dir,
)
from xgic.cli.utils.output import print_info, print_success, print_warning


def load_create_payload_config(
    config_path: Path = DEFAULT_CONFIG_FILE,
) -> dict[str, Any]:
    """Load create-payload-config.json (or sensible defaults)."""
    defaults: dict[str, Any] = {
        "projectName": "my-payload-cms",
        "projectDir": None,
        "layout": "auto",
        "composeProjectName": None,
        "template": "website",
        "dbAdapter": "postgres",
        "agent": "none",
        "dbUri": "",
    }
    if not config_path.exists():
        return defaults
    try:
        with config_path.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        for k, v in data.items():
            if v is not None:
                defaults[k] = v
        return defaults
    except (json.JSONDecodeError, OSError):
        return defaults


def get_project_name(config: dict[str, Any]) -> str:
    """Extract projectName with safe default (identity, not necessarily path)."""
    name = config.get("projectName")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return "my-payload-cms"


def is_payload_project_complete(project_dir: Path) -> bool:
    """Return True if project_dir looks like a finished Payload CMS app."""
    base = Path.cwd() if project_dir == Path(".") else project_dir
    if not base.is_dir():
        return False
    candidates = [
        base / "payload.config.ts",
        base / "payload.config.js",
        base / "src" / "payload.config.ts",
        base / "src" / "payload.config.js",
    ]
    return any(p.exists() for p in candidates)


def build_create_payload_command(
    target: str,
    *,
    template: str = "website",
    db_adapter: str = "postgres",
    db_connection_string: str | None = None,
    agent: str = "none",
) -> list[str]:
    """Return the argv list for a non-interactive create-payload-app run."""
    cmd = [
        "pnpx",
        "create-payload-app@latest",
        target,
        "-t",
        template,
        "--use-pnpm",
    ]

    if db_connection_string:
        cmd.extend(
            ["--db", db_adapter, "--db-connection-string", db_connection_string]
        )
    else:
        cmd.extend(["--db", db_adapter, "--db-accept-recommended"])

    if agent and str(agent).lower() not in ("", "none"):
        cmd.extend(["--agent", str(agent)])
    else:
        cmd.append("--no-agent")

    return cmd


def resolve_db_connection_string(
    json_db_uri: str, live_db_uri: str
) -> str | None:
    """Prefer live env DB URI over config JSON."""
    return live_db_uri or json_db_uri or None


def load_live_env_from_devcontainer(
    env_file: Path = Path(".devcontainer/.env"),
) -> tuple[str, str]:
    """Load DATABASE_URI and PAYLOAD_SECRET from .devcontainer/.env if present."""
    db_uri = os.environ.get("DATABASE_URI", "")
    secret = os.environ.get("PAYLOAD_SECRET", "")
    if (db_uri and secret) or not env_file.is_file():
        return db_uri, secret
    try:
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key == "DATABASE_URI" and not db_uri:
                db_uri = value
            elif key == "PAYLOAD_SECRET" and not secret:
                secret = value
    except OSError:
        pass
    return db_uri, secret


def compute_synced_project_env_content(
    original_content: str, live_db_uri: str, live_payload_secret: str
) -> str:
    """Return .env content with live DATABASE_URL / PAYLOAD_SECRET."""
    content = original_content
    if live_db_uri:
        content = re.sub(
            r"^DATABASE_URL=.*$",
            f"DATABASE_URL={live_db_uri}",
            content,
            flags=re.MULTILINE,
        )
        # Some templates use DATABASE_URI
        content = re.sub(
            r"^DATABASE_URI=.*$",
            f"DATABASE_URI={live_db_uri}",
            content,
            flags=re.MULTILINE,
        )
    if live_payload_secret:
        content = re.sub(
            r"^PAYLOAD_SECRET=.*$",
            f"PAYLOAD_SECRET={live_payload_secret}",
            content,
            flags=re.MULTILINE,
        )
    return content


def _sync_live_env_into_project(
    project_dir: Path, live_db_uri: str, live_payload_secret: str
) -> None:
    """Best-effort sync of live credentials into the generated project's .env."""
    base = Path.cwd() if project_dir == Path(".") else project_dir
    gen_env = base / ".env"
    if not gen_env.is_file():
        return

    try:
        content = gen_env.read_text(encoding="utf-8")
        new_content = compute_synced_project_env_content(
            content, live_db_uri, live_payload_secret
        )
        if new_content != content:
            gen_env.write_text(new_content, encoding="utf-8")
    except Exception:
        pass


def validate_compose_project_name(name: str) -> str:
    """Return a Docker Compose–safe project name or raise ValueError."""
    cleaned = name.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", cleaned):
        raise ValueError(
            f"Invalid projectName for Docker Compose: {name!r}. "
            "Use 1–63 chars: start with a letter or digit; then [a-z0-9_-]."
        )
    return cleaned


def sync_compose_project_name(
    project_name: str,
    *,
    compose_path: Path = Path(DEFAULT_COMPOSE_FILE),
) -> bool:
    """Set the top-level Compose ``name:`` field to *project_name*.

    Returns True when the file was updated, False when unchanged/skipped.
    """
    try:
        safe = validate_compose_project_name(project_name)
    except ValueError as e:
        print_warning(str(e))
        return False
    if not compose_path.is_file():
        return False
    try:
        text = compose_path.read_text(encoding="utf-8")
    except OSError as e:
        print_warning(f"Could not read {compose_path}: {e}")
        return False
    if re.search(r"(?m)^name:\s*", text):
        new_text, n = re.subn(
            r"(?m)^name:\s*.*$",
            f"name: {safe}",
            text,
            count=1,
        )
        if n == 0:
            return False
    else:
        new_text = f"name: {safe}\n{text}"
    if new_text == text:
        return False
    try:
        compose_path.write_text(new_text, encoding="utf-8")
    except OSError as e:
        print_warning(f"Could not write {compose_path}: {e}")
        return False
    return True


def ensure_devcontainer_env(*, quiet: bool = False) -> int:
    """Ensure ``.devcontainer/.env`` exists (create with fresh credentials if missing)."""
    from xgic.cli.payload.env_helpers import ENV_FILE, perform_env_regenerate

    if ENV_FILE.is_file():
        return 0
    if not quiet:
        print_info(
            f"{ENV_FILE} not found — generating credentials "
            "(same as: xgic payload env --regenerate --yes)"
        )
    return perform_env_regenerate(yes=True, env_file=ENV_FILE)


def ensure_db_services(*, quiet: bool = False, wait_seconds: float = 45.0) -> int:
    """Start only the DB Compose profile service (never recreate the IDE primary)."""
    from xgic.cli.core.environment import EnvironmentContext

    if not Path(DEFAULT_COMPOSE_FILE).is_file():
        if not quiet:
            print_info(
                f"No {DEFAULT_COMPOSE_FILE}; skipping Compose DB bring-up."
            )
        return 0

    env = EnvironmentContext.detect()
    docker = make_payload_docker_controller(env)
    compose_project = get_compose_project_name()
    docker.project_name = compose_project
    profile = get_db_profile()

    if db_ready(docker):
        if not quiet:
            print_success(f"Database service ({profile}) already ready.")
        return 0

    if not quiet:
        print_info(
            f"Starting database service only: profile={profile!r}, "
            f"service={profile!r} (project {compose_project!r})"
        )
    try:
        docker.up(profile=profile, services=[profile])
    except FileNotFoundError:
        print_warning(
            "docker not found. Run setup inside the Dev Container "
            "(or ensure Docker CLI is on PATH)."
        )
        return 1
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to start database service: {e}")
        print_info(
            "Tip: from inside the Dev Container, try: "
            f"xgic up --profile {profile}"
        )
        return 1

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if db_ready(docker):
            if not quiet:
                print_success(f"Database service ({profile}) is ready.")
            return 0
        time.sleep(1.0)

    print_warning(
        f"Database service ({profile}) did not become ready within "
        f"{int(wait_seconds)}s. Continuing with scaffold; "
        "re-check with: xgic payload env"
    )
    return 0


def ensure_payload_project(*, quiet: bool = False) -> int:
    """Ensure the Payload CMS project exists and is usable."""
    cfg = load_create_payload_config()
    project_name = get_project_name(cfg)
    try:
        project_name = validate_compose_project_name(project_name)
    except ValueError as e:
        print_warning(str(e))
        return 1

    project_dir = resolve_project_dir(cfg)
    target = create_payload_target_arg(project_dir)

    # First-run: create .devcontainer/.env when missing (no separate
    # `xgic payload env --regenerate --yes` step required).
    env_rc = ensure_devcontainer_env(quiet=quiet)
    if env_rc != 0:
        return env_rc

    # Compose project name from config (composeProjectName), not npm projectName.
    compose_project = get_compose_project_name()
    if sync_compose_project_name(compose_project) and not quiet:
        print_info(
            f"Docker Compose project name set to {compose_project!r} "
            f"in {DEFAULT_COMPOSE_FILE}"
        )

    if is_payload_project_complete(project_dir):
        if not quiet:
            print_success(
                "Payload CMS project already complete at "
                f"{display_project_location(project_dir)}."
            )
        db_rc = ensure_db_services(quiet=quiet)
        return db_rc if db_rc != 0 else 0

    if project_dir != Path(".") and project_dir.exists() and not quiet:
        print_warning(
            f"Directory '{project_dir.as_posix()}' exists but does not appear "
            "to be a complete Payload CMS project. Creation may overwrite or fail."
        )

    db_rc = ensure_db_services(quiet=quiet)
    if db_rc != 0 and not quiet:
        print_warning(
            "Database bring-up had issues; create-payload-app may still run."
        )

    template = str(cfg.get("template") or "website")
    db_adapter = str(cfg.get("dbAdapter") or "postgres")
    json_db_uri = str(cfg.get("dbUri") or "")
    agent = str(cfg.get("agent") or "none")

    live_db_uri, live_secret = load_live_env_from_devcontainer()
    db_uri_for_cli: str | None = resolve_db_connection_string(
        json_db_uri, live_db_uri
    )

    with contextlib.suppress(Exception):
        subprocess.run(
            ["corepack", "enable"],
            check=False,
            capture_output=True,
        )
    with contextlib.suppress(Exception):
        subprocess.run(
            ["corepack", "pnpm", "approve-builds", "@swc/core"],
            check=False,
            capture_output=True,
        )

    cmd = build_create_payload_command(
        target,
        template=template,
        db_adapter=db_adapter,
        db_connection_string=db_uri_for_cli,
        agent=agent,
    )

    if not quiet:
        print_info(
            f"Starting Payload CMS project creation at "
            f"{display_project_location(project_dir)} "
            f"(projectName={project_name!r}, template={template}, db={db_adapter})..."
        )
        print_info("Command: " + " ".join(cmd))

    try:
        result = subprocess.run(cmd, check=False)
    except FileNotFoundError as e:
        print_warning(f"Required tool not found for project creation: {e}")
        print_info(
            "Run `xgic payload setup` inside the VS Code Dev Container "
            "(Node/pnpm/pnpx are provided by the image). "
            "Host Windows without Node is not supported for setup yet."
        )
        return 1

    if result.returncode != 0:
        if not quiet:
            print_warning(
                f"create-payload-app exited with status {result.returncode}."
            )
            print_info(
                "Setup failed. Fix the error above, then re-run: "
                "xgic payload setup"
            )
        return result.returncode if result.returncode != 0 else 1

    if not is_payload_project_complete(project_dir):
        if not quiet:
            print_warning(
                "create-payload-app reported success but "
                f"{display_project_location(project_dir)} does not look like a "
                "complete Payload project (missing payload.config)."
            )
        return 1

    if not quiet:
        print_success(
            "Payload CMS project created successfully at "
            f"{display_project_location(project_dir)}."
        )
    _sync_live_env_into_project(project_dir, live_db_uri, live_secret)
    return 0
