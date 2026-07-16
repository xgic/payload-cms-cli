"""Register ``xgic.cli.payload`` subcommands on the core ``xgic`` CLI."""

from __future__ import annotations

import argparse

from xgic.cli.payload.commands.dev import run_dev
from xgic.cli.payload.commands.payload_env import run_payload_env
from xgic.cli.payload.commands.schema import run_schema
from xgic.cli.payload.commands.setup import run_setup_payloadcms


def register(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Entry point: ``xgic.cli.commands`` → Payload CMS product commands."""
    # Smart daily command (maps from transitional `xde dev`)
    dev = subparsers.add_parser(
        "dev",
        help="Start Payload CMS app dev server (smart: up + db check + pnpm dev)",
    )
    dev.set_defaults(func=run_dev)

    # Schema generator for create-payload-config
    schema = subparsers.add_parser(
        "schema",
        help="Generate create-payload-config JSON schema (template helper)",
    )
    schema.add_argument(
        "--generator",
        metavar="PATH",
        help="Override path to generate_schema.py",
    )
    schema.set_defaults(func=run_schema)

    # Nested setup (extensible)
    setup = subparsers.add_parser(
        "setup",
        help="Setup / ensure product components",
    )
    setup_sub = setup.add_subparsers(
        dest="setup_command",
        help="Component to set up",
        required=True,
    )
    payloadcms = setup_sub.add_parser(
        "payloadcms",
        help="Ensure Payload CMS project exists (idempotent)",
    )
    payloadcms.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress non-error output",
    )
    payloadcms.set_defaults(func=run_setup_payloadcms)

    # Product env (distinct from generic `xgic env` in xgic.cli.dev)
    penv = subparsers.add_parser(
        "payload-env",
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
