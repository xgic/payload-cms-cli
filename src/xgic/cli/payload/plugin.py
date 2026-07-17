"""Register ``xgic.cli.payload`` subcommands on the core ``xgic`` CLI.

All product commands live under the ``payload`` group for domain ownership::

    xgic payload dev
    xgic payload setup
    xgic payload env
    xgic payload schema
    xgic payload reset
"""

from __future__ import annotations

import argparse

from xgic.cli.payload.commands.dev import run_dev
from xgic.cli.payload.commands.payload_env import run_payload_env
from xgic.cli.payload.commands.reset import run_reset
from xgic.cli.payload.commands.schema import run_schema
from xgic.cli.payload.commands.setup import run_setup_payloadcms


def register(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Entry point: ``xgic.cli.commands`` → Payload CMS product commands."""
    payload = subparsers.add_parser(
        "payload",
        help="Payload CMS product commands",
    )
    payload_sub = payload.add_subparsers(
        dest="payload_command",
        help="Payload CMS action",
        metavar="ACTION",
        required=True,
    )

    # Smart daily command (maps from transitional `xde dev`)
    dev = payload_sub.add_parser(
        "dev",
        help="Start Payload CMS app dev server (smart: up + db check + pnpm dev)",
    )
    dev.set_defaults(func=run_dev)

    # Ensure project directory
    setup = payload_sub.add_parser(
        "setup",
        help="Ensure Payload CMS project exists (idempotent)",
    )
    setup.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error output",
    )
    setup.set_defaults(func=run_setup_payloadcms)

    # Product env (distinct from generic `xgic env` in xgic.cli.dev)
    penv = payload_sub.add_parser(
        "env",
        help="Payload CMS env status and credential regenerate",
    )
    penv.add_argument(
        "--json",
        action="store_true",
        help="Output status as JSON",
    )
    penv.add_argument(
        "--regenerate",
        action="store_true",
        help="Write fresh credentials to .devcontainer/.env",
    )
    penv.add_argument(
        "--yes",
        action="store_true",
        help="Confirm regenerate without prompt",
    )
    penv.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview regenerate without writing",
    )
    penv.add_argument(
        "--env-file",
        metavar="PATH",
        help="Override path to .env (default .devcontainer/.env)",
    )
    penv.set_defaults(func=run_payload_env)

    # Schema generator for create-payload-config
    schema = payload_sub.add_parser(
        "schema",
        help="Generate create-payload-config JSON schema (template helper)",
    )
    schema.add_argument(
        "--generator",
        metavar="PATH",
        help="Override path to generate_schema.py",
    )
    schema.set_defaults(func=run_schema)

    # Targeted reset (project dir + DB volume)
    reset = payload_sub.add_parser(
        "reset",
        help="Fast targeted reset (project folder + active DB volume)",
    )
    reset.add_argument(
        "--yes",
        action="store_true",
        help="Skip confirmation and proceed",
    )
    reset.add_argument(
        "--dry-run",
        action="store_true",
        help="Show planned actions without making changes",
    )
    reset.add_argument(
        "--rotate-credentials",
        action="store_true",
        help="Also regenerate .devcontainer/.env credentials",
    )
    reset.set_defaults(func=run_reset)
