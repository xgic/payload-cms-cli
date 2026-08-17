"""``xgic payload dev`` — smart Payload CMS development server start."""

from __future__ import annotations

import subprocess
from pathlib import Path

from xgic.cli.app import CommandContext
from xgic.cli.core.environment import EnvironmentType
from xgic.cli.payload.config import (
    DEFAULT_PRIMARY_SERVICE,
    db_ready,
    get_compose_project_name,
    get_db_profile,
    make_payload_docker_controller,
)
from xgic.cli.payload.layout import display_project_location, resolve_project_dir
from xgic.cli.payload.project import (
    ensure_db_services,
    is_payload_project_complete,
    load_create_payload_config,
)
from xgic.cli.utils.output import print_info, print_success, print_warning


def _app_cwd(project_dir: Path) -> Path:
    if project_dir == Path("."):
        return Path.cwd()
    return (Path.cwd() / project_dir).resolve()


def run_dev(ctx: CommandContext) -> int:
    """Start DB if needed and launch the Payload CMS app dev server."""
    env = ctx.env
    cfg = load_create_payload_config()
    project_dir = resolve_project_dir(cfg)

    if not is_payload_project_complete(project_dir):
        print_warning(
            "Payload CMS app is not set up yet at "
            f"{display_project_location(project_dir)}."
        )
        print_info("Run first:  xgic payload env --regenerate --yes")
        print_info("Then:       xgic payload setup")
        print_info("Then:       xgic payload dev")
        return 1

    print_info("Starting Payload CMS development server...")
    print_info(f"App location: {display_project_location(project_dir)}")

    docker = make_payload_docker_controller(env)
    docker.project_name = get_compose_project_name()
    profile = get_db_profile()

    # Never recreate the primary Dev Container service; only ensure DB.
    if not db_ready(docker):
        print_warning(
            f"Database ({profile}) not ready. Starting DB service only..."
        )
        db_rc = ensure_db_services(quiet=False)
        if db_rc != 0:
            print_warning(
                "Could not start database. Fix Compose/DB, then re-run "
                "xgic payload dev."
            )
            return db_rc
    else:
        print_success("Database is ready")

    app_cwd = _app_cwd(project_dir)
    if not (app_cwd / "package.json").is_file():
        print_warning(f"No package.json under {app_cwd}")
        return 1

    if env.env_type in (
        EnvironmentType.DEV_CONTAINER,
        EnvironmentType.GENERIC_CONTAINER,
    ):
        try:
            print_info(f"Launching pnpm dev in {app_cwd}...")
            result = subprocess.run(
                ["sh", "-c", 'trap "exit 0" INT TERM; exec pnpm dev'],
                cwd=str(app_cwd),
                check=False,
            )
            if result.returncode in (130, -2, 2):
                print_info("Development server stopped by user (Ctrl+C).")
                return 0
            if result.returncode != 0:
                print_warning(f"pnpm dev exited with code {result.returncode}.")
                print_info(
                    f"Fallback: cd {display_project_location(project_dir)} "
                    "&& pnpm dev"
                )
                return result.returncode or 1
            print_info("Development server exited cleanly.")
            return 0
        except KeyboardInterrupt:
            print_info("Development server stopped by user (Ctrl+C).")
            return 0
        except FileNotFoundError:
            print_warning(
                "pnpm not found. Run inside the Dev Container image "
                "(or install pnpm on PATH)."
            )
            return 1

    # Host: try docker exec into primary service (optional path)
    rel = (
        "."
        if project_dir == Path(".")
        else project_dir.as_posix().strip("/")
    )
    try:
        print_info(
            f"Launching pnpm dev via container service "
            f"{DEFAULT_PRIMARY_SERVICE!r}..."
        )
        docker.exec(
            DEFAULT_PRIMARY_SERVICE,
            "sh",
            "-c",
            f"cd /workspace/{rel} && "
            "sh -c 'trap \"exit 0\" INT TERM; exec pnpm dev'",
            check=False,
        )
    except Exception as e:
        print_warning(f"Failed to launch pnpm dev from host: {e}")
        print_info(
            "Prefer: Dev Containers → Reopen in Container, then "
            "xgic payload dev"
        )
        return 1

    print_success("Environment ready for development.")
    print_info("Environment context: " + env.describe())
    return 0
