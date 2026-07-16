"""Tests for Payload CMS CLI registration and command handlers."""

from __future__ import annotations

import argparse
from unittest.mock import MagicMock, patch

from xgic.cli.app import CommandContext
from xgic.cli.core.environment import EnvironmentContext, EnvironmentType
from xgic.cli.payload.commands.dev import run_dev
from xgic.cli.payload.commands.schema import run_schema
from xgic.cli.payload.commands.setup import run_setup_payloadcms
from xgic.cli.payload.plugin import register


def test_register_commands() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    register(sub)
    for name in ("dev", "schema", "payload-env"):
        args = parser.parse_args([name])
        assert args.command == name
        assert callable(args.func)
    args = parser.parse_args(["setup", "payloadcms", "--quiet"])
    assert args.command == "setup"
    assert args.setup_command == "payloadcms"
    assert args.quiet is True
    assert callable(args.func)


def test_run_setup_payloadcms() -> None:
    ns = argparse.Namespace(quiet=True)
    ctx = CommandContext(
        env=EnvironmentContext(env_type=EnvironmentType.HOST),
        args=ns,
    )
    with patch(
        "xgic.cli.payload.commands.setup.ensure_payload_project",
        return_value=0,
    ) as ensure:
        assert run_setup_payloadcms(ctx) == 0
        ensure.assert_called_once_with(quiet=True)


def test_run_schema_missing_generator(tmp_path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    ns = argparse.Namespace(generator=None)
    ctx = CommandContext(
        env=EnvironmentContext(env_type=EnvironmentType.HOST),
        args=ns,
    )
    assert run_schema(ctx) == 1


def test_run_dev_starts_services_when_down() -> None:
    ns = argparse.Namespace()
    env = EnvironmentContext(env_type=EnvironmentType.HOST)
    ctx = CommandContext(env=env, args=ns)
    with (
        patch(
            "xgic.cli.payload.commands.dev.make_payload_docker_controller"
        ) as make,
        patch("xgic.cli.payload.commands.dev.db_ready", return_value=True),
        patch(
            "xgic.cli.payload.commands.dev.get_payload_project_name",
            return_value="site",
        ),
    ):
        docker = MagicMock()
        docker.services_running.return_value = False
        docker.exec.return_value = MagicMock(returncode=0)
        make.return_value = docker
        assert run_dev(ctx) == 0
        docker.up.assert_called_once()
        docker.exec.assert_called()
