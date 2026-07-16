"""``xgic setup payloadcms`` — ensure Payload CMS project directory."""

from __future__ import annotations

from xgic.cli.app import CommandContext
from xgic.cli.payload.project import ensure_payload_project


def run_setup_payloadcms(ctx: CommandContext) -> int:
    """Idempotent Payload CMS project ensure."""
    quiet = bool(getattr(ctx.args, "quiet", False))
    return ensure_payload_project(quiet=quiet)
