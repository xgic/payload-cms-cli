"""Payload CMS product env file generation (credentials + secrets)."""

from __future__ import annotations

import os
import re
import secrets
import subprocess
from pathlib import Path

from xgic.cli.payload.config import (
    DEFAULT_CONFIG_FILE,
    get_compose_project_name,
    get_db_config,
    get_db_profile,
)
from xgic.cli.utils.output import print_info, print_success, print_warning

ENV_FILE = Path(".devcontainer/.env")
DEFAULT_NEXT_PUBLIC_SERVER_URL = "http://localhost:3000"

_PLACEHOLDER_RE = re.compile(
    r"^(?:YOUR_[A-Z0-9_]*|CHANGE_?ME|CHANGEME|XXX|TODO)?$",
    re.IGNORECASE,
)
_STALE_VOLUME_WARNING = (
    "Regenerate rewrites credential files only — it does NOT delete "
    "Compose database volume data. It also does NOT update the password "
    "already stored inside that volume, so the app may fail auth until "
    "you either (1) recreate the volume (destructive: "
    "xgic payload reset --yes) or (2) update the database role password "
    "to match the new files (non-destructive; tracked as a separate "
    "rotate feature)."
)


def generate_fresh_env_content(
    *,
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> str:
    """Pure: return compose .env content with fresh secrets + db from config."""
    db_name, db_user = get_db_config(config_file)
    payload_secret = secrets.token_hex(32)
    adapter = get_db_profile(config_file)

    if adapter == "mongodb":
        mongo_pass = secrets.token_hex(16)
        return f"""MONGO_INITDB_ROOT_USERNAME={db_user}
MONGO_INITDB_ROOT_PASSWORD={mongo_pass}
MONGO_INITDB_DATABASE={db_name}
PAYLOAD_SECRET={payload_secret}
DATABASE_URL=mongodb://{db_user}:{mongo_pass}@mongodb:27017/{db_name}?authSource=admin
"""

    pg_pass = secrets.token_hex(16)
    # PGUSER/PGDATABASE are libpq defaults. Without them, `pg_isready -U payload`
    # and other clients open a database named after the user (`payload`) while
    # POSTGRES_DB is `payload_db`.
    return f"""POSTGRES_USER={db_user}
POSTGRES_PASSWORD={pg_pass}
POSTGRES_DB={db_name}
PGUSER={db_user}
PGDATABASE={db_name}
PAYLOAD_SECRET={payload_secret}
DATABASE_URL=postgres://{db_user}:{pg_pass}@postgres:5432/{db_name}
"""


def parse_dotenv(content: str) -> dict[str, str]:
    """Parse KEY=value assignments from .env text (last key wins)."""
    values: dict[str, str] = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        key = key.strip()
        if not key:
            continue
        values[key] = value.strip().strip('"').strip("'")
    return values


def looks_like_placeholder(value: str) -> bool:
    """Return True for empty values or YOUR_* / CHANGE_ME style placeholders."""
    return _PLACEHOLDER_RE.fullmatch(value.strip().strip('"').strip("'")) is not None


def _set_env_key(content: str, key: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(key)}=.*$", re.MULTILINE)
    replacement = f"{key}={value}"
    if pattern.search(content):
        return pattern.sub(replacement, content, count=1)
    if content and not content.endswith("\n"):
        content += "\n"
    return content + f"{replacement}\n"


def _remove_env_key(content: str, key: str) -> str:
    return re.sub(rf"^{re.escape(key)}=.*\r?\n?", "", content, flags=re.MULTILINE)


def compute_synced_project_env_content(
    original_content: str,
    live_db_uri: str,
    live_payload_secret: str,
    *,
    cron_secret: str | None = None,
    preview_secret: str | None = None,
    next_public_server_url: str | None = None,
) -> str:
    """Return app .env content with live DATABASE_URL / secrets.

    Writes Payload-canonical ``DATABASE_URL`` only (migrates a lone
    ``DATABASE_URI``). Generates ``CRON_SECRET`` / ``PREVIEW_SECRET`` when
    missing or still placeholders. Preserves other keys; sets
    ``NEXT_PUBLIC_SERVER_URL`` when absent.
    """
    content = original_content
    parsed = parse_dotenv(content)

    if live_db_uri:
        if "DATABASE_URL" in parsed:
            content = _set_env_key(content, "DATABASE_URL", live_db_uri)
            content = _remove_env_key(content, "DATABASE_URI")
        elif "DATABASE_URI" in parsed:
            content = re.sub(
                r"^DATABASE_URI=.*$",
                f"DATABASE_URL={live_db_uri}",
                content,
                count=1,
                flags=re.MULTILINE,
            )
            content = _remove_env_key(content, "DATABASE_URI")
        else:
            content = _set_env_key(content, "DATABASE_URL", live_db_uri)

    if live_payload_secret:
        content = _set_env_key(content, "PAYLOAD_SECRET", live_payload_secret)

    cron_val = parsed.get("CRON_SECRET")
    if cron_val is None or looks_like_placeholder(cron_val):
        content = _set_env_key(
            content, "CRON_SECRET", cron_secret or secrets.token_hex(32)
        )

    preview_val = parsed.get("PREVIEW_SECRET")
    if preview_val is None or looks_like_placeholder(preview_val):
        content = _set_env_key(
            content, "PREVIEW_SECRET", preview_secret or secrets.token_hex(32)
        )

    if "NEXT_PUBLIC_SERVER_URL" not in parsed:
        content = _set_env_key(
            content,
            "NEXT_PUBLIC_SERVER_URL",
            next_public_server_url or DEFAULT_NEXT_PUBLIC_SERVER_URL,
        )

    return content


def load_live_env_from_devcontainer(
    env_file: Path = Path(".devcontainer/.env"),
) -> tuple[str, str]:
    """Load DATABASE_URL and PAYLOAD_SECRET from process env or compose .env."""
    db_url = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE_URI", "")
    secret = os.environ.get("PAYLOAD_SECRET", "")
    if (db_url and secret) or not env_file.is_file():
        return db_url, secret
    try:
        parsed = parse_dotenv(env_file.read_text(encoding="utf-8"))
    except OSError:
        return db_url, secret
    if not db_url:
        db_url = parsed.get("DATABASE_URL") or parsed.get("DATABASE_URI", "")
    if not secret:
        secret = parsed.get("PAYLOAD_SECRET", "")
    return db_url, secret


def sync_live_env_into_project(
    project_dir: Path,
    live_db_uri: str,
    live_payload_secret: str,
    *,
    env_path: Path | None = None,
    create_if_missing: bool = False,
) -> Path | None:
    """Best-effort sync of live credentials into the generated project's .env.

    Returns the path written (or already matching), or None when skipped.
    """
    if env_path is None:
        base = Path.cwd() if project_dir == Path(".") else project_dir
        env_path = base / ".env"
    if not env_path.is_file() and not create_if_missing:
        return None

    try:
        content = env_path.read_text(encoding="utf-8") if env_path.is_file() else ""
        new_content = compute_synced_project_env_content(
            content, live_db_uri, live_payload_secret
        )
        if new_content != content:
            env_path.parent.mkdir(parents=True, exist_ok=True)
            env_path.write_text(new_content, encoding="utf-8")
        return env_path
    except Exception:
        return None


def compose_db_volume_name(*, config_file: Path = DEFAULT_CONFIG_FILE) -> str:
    """Return the conventional Compose DB volume name for this workspace."""
    return f"{get_compose_project_name(config_file)}-{get_db_profile(config_file)}-data"


def compose_db_volume_exists(*, config_file: Path = DEFAULT_CONFIG_FILE) -> bool:
    """Return True when ``docker volume inspect`` finds the Compose DB volume."""
    name = compose_db_volume_name(config_file=config_file)
    try:
        result = subprocess.run(
            ["docker", "volume", "inspect", name],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


def _infer_workspace_root(config_file: Path, env_file: Path) -> Path:
    for candidate in (config_file, env_file):
        path = candidate if candidate.is_absolute() else Path.cwd() / candidate
        if path.parent.name == ".devcontainer":
            return path.parent.parent
    return Path.cwd()


def _resolve_app_env_path(config_file: Path, env_file: Path) -> Path:
    from xgic.cli.payload.layout import resolve_project_dir
    from xgic.cli.payload.project import load_create_payload_config

    root = _infer_workspace_root(config_file, env_file)
    rel = resolve_project_dir(load_create_payload_config(config_file), root=root)
    if rel == Path(".") or str(rel) in (".", ""):
        return root / ".env"
    return root / rel / ".env"


def _warn_stale_compose_db_volume(
    *,
    config_file: Path,
    env_existed: bool,
    planned: bool = False,
) -> None:
    """Warn when file rewrite cannot fix a volume initialized with the old password."""
    exists = compose_db_volume_exists(config_file=config_file)
    if not exists and not env_existed:
        return
    prefix = "Dry run: " if planned else ""
    if exists:
        name = compose_db_volume_name(config_file=config_file)
        print_warning(
            f"{prefix}Detected existing Compose DB volume {name!r}. "
            "Data in that volume is kept, but it may still hold the "
            "previous password (connectivity can break until reset or "
            "an in-place role password update)."
        )
    print_warning(f"{prefix}{_STALE_VOLUME_WARNING}")


def perform_env_regenerate(
    *,
    dry_run: bool = False,
    yes: bool = False,
    env_file: Path = ENV_FILE,
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> int:
    """Regenerate compose .env and sync the Payload app .env (guarded)."""
    from xgic.cli.payload.project import is_payload_project_complete

    content = generate_fresh_env_content(config_file=config_file)
    env_existed = env_file.is_file()
    app_env = _resolve_app_env_path(config_file, env_file)
    would_sync = app_env.is_file() or is_payload_project_complete(app_env.parent)

    if dry_run:
        print_info("Dry run: would write fresh credentials to .env")
        print_info(f"  (content length: {len(content)} chars)")
        print_info(f"  compose env: {env_file}")
        if would_sync:
            print_info(f"  would sync app env: {app_env}")
        _warn_stale_compose_db_volume(
            config_file=config_file,
            env_existed=env_existed,
            planned=True,
        )
        return 0

    if not yes:
        print_warning("This will overwrite .env with new random credentials.")
        print_warning("Re-run with --yes to proceed.")
        return 1

    try:
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text(content, encoding="utf-8")
    except Exception as e:
        print_warning(f"Failed to write {env_file}: {e}")
        return 1

    parsed = parse_dotenv(content)
    live_db = parsed.get("DATABASE_URL") or parsed.get("DATABASE_URI", "")
    live_secret = parsed.get("PAYLOAD_SECRET", "")
    written = sync_live_env_into_project(
        app_env.parent,
        live_db,
        live_secret,
        env_path=app_env,
        create_if_missing=is_payload_project_complete(app_env.parent),
    )

    db_name, db_user = get_db_config(config_file)
    adapter = get_db_profile(config_file)
    print_success(f"Generated fresh credentials in {env_file}")
    if adapter == "mongodb":
        print_info(f"  (MONGO DB for {db_name})")
    else:
        print_info(f"  (POSTGRES_DB={db_name}, POSTGRES_USER={db_user})")
    if written is not None:
        print_success(f"Synced credentials into {written}")
    _warn_stale_compose_db_volume(
        config_file=config_file,
        env_existed=env_existed,
        planned=False,
    )
    return 0
