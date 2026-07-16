"""``xgic payload env`` — product-aware env status and credential regenerate.

Nested under the ``payload`` domain group so it does not clash with the
generic ``xgic env`` command in ``xgic.cli.dev``.
"""

from __future__ import annotations

import json
from pathlib import Path

from xgic.cli.app import CommandContext
from xgic.cli.payload.config import (
    get_payload_project_name,
    make_payload_docker_controller,
)
from xgic.cli.payload.env_helpers import ENV_FILE, perform_env_regenerate
from xgic.cli.utils.output import print_info, print_success


def run_payload_env(ctx: CommandContext) -> int:
    """Inspect Payload CMS env status or regenerate credentials."""
    if getattr(ctx.args, "regenerate", False):
        return perform_env_regenerate(
            dry_run=bool(getattr(ctx.args, "dry_run", False)),
            yes=bool(getattr(ctx.args, "yes", False)),
            env_file=Path(getattr(ctx.args, "env_file", None) or ENV_FILE),
        )

    docker = make_payload_docker_controller(ctx.env)
    env_file_exists = ENV_FILE.exists()
    services_ok = docker.services_running()
    payload_project = get_payload_project_name()
    use_json = bool(getattr(ctx.args, "json", False))

    if use_json:
        print(
            json.dumps(
                {
                    "env_file_exists": env_file_exists,
                    "env_file": str(ENV_FILE),
                    "services_running": services_ok,
                    "payload_project": payload_project,
                    "environment": ctx.env.describe(),
                },
                indent=2,
            )
        )
        return 0

    print_info("Payload CMS development environment status:")
    if env_file_exists:
        print_success(f".env file exists at {ENV_FILE}")
    else:
        print_info(
            f".env file not found at {ENV_FILE} "
            "(use: xgic payload env --regenerate --yes)"
        )
    if services_ok:
        print_success("Compose services: appear to be running")
    else:
        print_info("Compose services: not detected as running")
    print_info(f"Configured Payload CMS project: {payload_project}")
    print_info("Environment context: " + ctx.env.describe())
    return 0
