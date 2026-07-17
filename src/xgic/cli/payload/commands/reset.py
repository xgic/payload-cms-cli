"""``xgic payload reset`` — fast targeted project + DB volume reset."""

from __future__ import annotations

import shutil
from pathlib import Path

from xgic.cli.app import CommandContext
from xgic.cli.payload.config import (
    get_db_config,
    get_db_profile,
    get_payload_project_name,
    make_payload_docker_controller,
)
from xgic.cli.payload.env_helpers import perform_env_regenerate
from xgic.cli.payload.project import ensure_payload_project
from xgic.cli.utils.output import print_info, print_success, print_warning


def run_reset(ctx: CommandContext) -> int:
    """Delete generated project folder and reset the active DB volume.

    Credentials in ``.env`` are left alone unless ``--rotate-credentials``.
    """
    dry_run = bool(getattr(ctx.args, "dry_run", False))
    yes = bool(getattr(ctx.args, "yes", False))
    rotate = bool(getattr(ctx.args, "rotate_credentials", False))

    docker = make_payload_docker_controller(ctx.env)
    payload_project = get_payload_project_name()
    project_path = Path(payload_project)
    db_service = get_db_profile()
    db_volume = docker.db_volume_name(db_service)

    print_info("Planned actions for reset:")
    print_info(f"  - Delete directory: {project_path}")
    print_info(f"  - Remove Docker volume: {db_volume}")
    if rotate:
        print_warning("  - ALSO rotate database credentials (DANGEROUS)")

    if dry_run:
        print_success("Dry run complete. No changes were made.")
        return 0

    if not yes:
        print_warning(
            "This operation is destructive. Re-run with --yes to proceed."
        )
        return 1

    print_info("Performing reset...")

    if project_path.exists():
        shutil.rmtree(project_path)
        print_success(f"Deleted project directory: {project_path}")
    else:
        print_info(f"Project directory {project_path} did not exist.")

    docker.rm_service(db_service, force=True, stop=True, remove_volumes=False)

    if docker.remove_volume(db_volume):
        print_success(f"Removed volume: {db_volume}")
    else:
        print_warning(
            f"Could not remove volume {db_volume} (may not exist or in use)"
        )

    db_name, db_user = get_db_config()
    try:
        docker.up(services=[db_service], profile=db_service)
        print_info(f"{db_service.capitalize()} service recreated.")

        if db_service == "postgres":
            sql = f"CREATE DATABASE IF NOT EXISTS {db_name} OWNER {db_user};"
            docker.exec(
                "postgres",
                "sh",
                "-c",
                f'psql -U {db_user} -d postgres -c "{sql}" 2>/dev/null || true',
                check=False,
            )
            print_success(f"Ensured database '{db_name}' exists.")
        else:
            print_info(
                "MongoDB service recreated. DB will be initialized by the app "
                "on first use."
            )

        ensure_payload_project()
    except Exception as e:
        print_warning(
            f"Issue recreating {db_service} or DB: {e}. "
            "Manual `xgic up --profile …` may be needed."
        )

    if rotate:
        print_info("Rotating credentials (--rotate-credentials)...")
        rc = perform_env_regenerate(yes=True)
        if rc == 0:
            print_success("Credentials rotated in .env.")
        else:
            print_warning("Credential rotation had issues (check .env).")

    print_success(
        "Reset complete. Project ensured. Next: `xgic payload dev` "
        "(or `xgic up --profile …`)."
    )
    return 0
