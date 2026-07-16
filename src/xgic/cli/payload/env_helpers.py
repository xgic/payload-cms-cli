"""Payload CMS product env file generation (credentials + secrets)."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from xgic.cli.payload.config import DEFAULT_CONFIG_FILE, get_db_config
from xgic.cli.utils.output import print_info, print_success, print_warning

ENV_FILE = Path(".devcontainer/.env")


def generate_fresh_env_content(
    *,
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> str:
    """Pure: return .env content with fresh secrets + db from config."""
    db_name, db_user = get_db_config(config_file)
    payload_secret = secrets.token_hex(32)

    adapter = "postgres"
    if config_file.exists():
        try:
            with config_file.open(encoding="utf-8") as f:
                cfg = json.load(f)
            adapter = str(cfg.get("dbAdapter", "postgres")).lower()
        except Exception:
            pass

    if adapter == "mongodb":
        mongo_pass = secrets.token_hex(16)
        return f"""MONGO_INITDB_ROOT_USERNAME={db_user}
MONGO_INITDB_ROOT_PASSWORD={mongo_pass}
MONGO_INITDB_DATABASE={db_name}
PAYLOAD_SECRET={payload_secret}
DATABASE_URI=mongodb://{db_user}:{mongo_pass}@mongodb:27017/{db_name}?authSource=admin
"""

    pg_pass = secrets.token_hex(16)
    return f"""POSTGRES_USER={db_user}
POSTGRES_PASSWORD={pg_pass}
POSTGRES_DB={db_name}
PAYLOAD_SECRET={payload_secret}
DATABASE_URI=postgres://{db_user}:{pg_pass}@postgres:5432/{db_name}
"""


def perform_env_regenerate(
    *,
    dry_run: bool = False,
    yes: bool = False,
    env_file: Path = ENV_FILE,
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> int:
    """Regenerate .env with fresh credentials (guarded by --yes / dry-run)."""
    if dry_run:
        content = generate_fresh_env_content(config_file=config_file)
        print_info("Dry run: would write fresh credentials to .env")
        print_info(f"  (content length: {len(content)} chars)")
        return 0

    if not yes:
        print_warning("This will overwrite .env with new random credentials.")
        print_warning("Re-run with --yes to proceed.")
        return 1

    content = generate_fresh_env_content(config_file=config_file)
    try:
        env_file.parent.mkdir(parents=True, exist_ok=True)
        with env_file.open("w", encoding="utf-8") as f:
            f.write(content)
        db_name, db_user = get_db_config(config_file)
        adapter = "postgres"
        if config_file.exists():
            try:
                with config_file.open(encoding="utf-8") as f:
                    cfg = json.load(f)
                adapter = str(cfg.get("dbAdapter", "postgres")).lower()
            except Exception:
                pass
        print_success(f"Generated fresh credentials in {env_file}")
        if adapter == "mongodb":
            print_info(f"  (MONGO DB for {db_name})")
        else:
            print_info(f"  (POSTGRES_DB={db_name}, POSTGRES_USER={db_user})")
        return 0
    except Exception as e:
        print_warning(f"Failed to write {env_file}: {e}")
        return 1
