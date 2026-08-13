"""Payload CMS project setup / ensure helpers."""

from __future__ import annotations

import contextlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

from xgic.cli.payload.config import DEFAULT_CONFIG_FILE
from xgic.cli.utils.output import print_info, print_success, print_warning


def load_create_payload_config(
    config_path: Path = DEFAULT_CONFIG_FILE,
) -> dict[str, Any]:
    """Load create-payload-config.json (or sensible defaults)."""
    defaults: dict[str, Any] = {
        "projectName": "my-payload-cms",
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
    """Extract projectName with safe default."""
    name = config.get("projectName")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return "my-payload-cms"


def is_payload_project_complete(project_dir: Path) -> bool:
    """Return True if project_dir looks like a finished Payload CMS app."""
    if not project_dir.is_dir():
        return False
    candidates = [
        project_dir / "payload.config.ts",
        project_dir / "payload.config.js",
        project_dir / "src" / "payload.config.ts",
        project_dir / "src" / "payload.config.js",
    ]
    return any(p.exists() for p in candidates)


def build_create_payload_command(
    project_name: str,
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
        project_name,
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
    gen_env = project_dir / ".env"
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
    compose_path: Path = Path(".devcontainer/docker-compose.yml"),
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


def ensure_payload_project(*, quiet: bool = False) -> int:
    """Ensure the Payload CMS project directory exists and is usable."""
    cfg = load_create_payload_config()
    project_name = get_project_name(cfg)
    try:
        project_name = validate_compose_project_name(project_name)
    except ValueError as e:
        print_warning(str(e))
        return 1

    env_rc = ensure_devcontainer_env(quiet=quiet)
    if env_rc != 0:
        return env_rc

    if sync_compose_project_name(project_name) and not quiet:
        print_info(
            f"Docker Compose project name set to {project_name!r} "
            "in .devcontainer/docker-compose.yml"
        )

    project_dir = Path(project_name)

    if is_payload_project_complete(project_dir):
        if not quiet:
            print_success(
                f"Payload CMS project already complete at '{project_name}/'."
            )
        return 0

    if project_dir.exists() and not quiet:
        print_warning(
            f"Directory '{project_name}' exists but does not appear to be "
            "a complete Payload CMS project. Creation may overwrite or fail."
        )

    template = str(cfg.get("template") or "website")
    db_adapter = str(cfg.get("dbAdapter") or "postgres")
    json_db_uri = str(cfg.get("dbUri") or "")
    agent = str(cfg.get("agent") or "none")

    live_db_uri = os.environ.get("DATABASE_URI", "")
    live_secret = os.environ.get("PAYLOAD_SECRET", "")

    db_uri_for_cli: str | None = resolve_db_connection_string(
        json_db_uri, live_db_uri
    )

    with contextlib.suppress(Exception):
        subprocess.run(
            ["corepack", "pnpm", "approve-builds", "@swc/core"],
            check=False,
            capture_output=True,
        )

    cmd = build_create_payload_command(
        project_name,
        template=template,
        db_adapter=db_adapter,
        db_connection_string=db_uri_for_cli,
        agent=agent,
    )

    if not quiet:
        print_info(
            f"Starting Payload CMS project creation for '{project_name}' "
            f"(template: {template}, db: {db_adapter})..."
        )
        print_info("Command: " + " ".join(cmd))

    try:
        result = subprocess.run(cmd, check=False)
    except FileNotFoundError as e:
        print_warning(f"Required tool not found for project creation: {e}")
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
                f"create-payload-app reported success but '{project_name}/' "
                "does not look like a complete Payload project "
                "(missing payload.config)."
            )
        return 1

    if not quiet:
        print_success("Payload CMS project created successfully.")
    if project_dir.is_dir():
        _sync_live_env_into_project(project_dir, live_db_uri, live_secret)
    return 0
