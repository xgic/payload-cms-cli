"""``xgic payload dev`` — smart Payload CMS development server start."""

from __future__ import annotations

import subprocess

from xgic.cli.app import CommandContext
from xgic.cli.core.environment import EnvironmentType
from xgic.cli.payload.config import (
    DEFAULT_PRIMARY_SERVICE,
    db_ready,
    get_db_profile,
    get_payload_project_name,
    make_payload_docker_controller,
)
from xgic.cli.utils.output import print_info, print_success, print_warning


def run_dev(ctx: CommandContext) -> int:
    """Start services if needed and launch the Payload CMS app dev server."""
    env = ctx.env
    docker = make_payload_docker_controller(env)
    print_info("Starting Payload CMS development server...")

    profile = get_db_profile()
    if not docker.services_running():
        print_warning("Services not running. Attempting to bring them up...")
        docker.up(profile=profile)
        print_success("Services started. Proceeding...")

    payload_project = get_payload_project_name()

    if db_ready(docker):
        print_success("Database is ready")
    else:
        print_warning(
            "Database not ready yet. You may need a reset / wait for DB startup."
        )

    print_info(f"Target Payload CMS project: {payload_project}")

    if env.env_type == EnvironmentType.DEV_CONTAINER:
        try:
            print_info(f"Launching pnpm dev inside {payload_project}...")
            project_dir = f"/workspace/{payload_project}"
            result = subprocess.run(
                ["sh", "-c", 'trap "exit 0" INT TERM; exec pnpm dev'],
                cwd=project_dir,
                check=False,
            )
            if result.returncode in (130, -2, 2):
                print_info("Development server stopped by user (Ctrl+C).")
                return 0
            if result.returncode != 0:
                print_warning(f"pnpm dev exited with code {result.returncode}.")
                print_info(
                    f"Fallback: cd {payload_project} && pnpm dev "
                    "(or xgic shell --service …)."
                )
                return result.returncode or 1
            print_info("Development server exited cleanly.")
            return 0
        except KeyboardInterrupt:
            print_info("Development server stopped by user (Ctrl+C).")
            return 0

    try:
        print_info(
            f"Launching pnpm dev inside {payload_project} (via container)..."
        )
        docker.exec(
            DEFAULT_PRIMARY_SERVICE,
            "sh",
            "-c",
            f"cd /workspace/{payload_project} && "
            "sh -c 'trap \"exit 0\" INT TERM; exec pnpm dev'",
            check=False,
        )
    except Exception as e:
        print_warning(f"Failed to launch pnpm dev: {e}")
        print_info(
            f"Fallback: cd {payload_project} && pnpm dev (or xgic shell)."
        )

    print_success("Environment ready for development.")
    print_info("Environment context: " + env.describe())
    return 0
