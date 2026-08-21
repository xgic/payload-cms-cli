"""Tests for Payload CMS CLI registration and command handlers."""

from __future__ import annotations

import argparse
from pathlib import Path
from unittest.mock import MagicMock, patch

from xgic.cli.app import CommandContext
from xgic.cli.core.environment import EnvironmentContext, EnvironmentType
from xgic.cli.payload.commands.dev import run_dev
from xgic.cli.payload.commands.reset import run_reset
from xgic.cli.payload.commands.schema import run_schema
from xgic.cli.payload.commands.setup import run_setup_payloadcms
from xgic.cli.payload.plugin import register


def test_register_payload_group_commands() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command")
    register(sub)

    for action in ("dev", "setup", "env", "schema", "reset"):
        args = parser.parse_args(["payload", action])
        assert args.command == "payload"
        assert args.payload_command == action
        assert callable(args.func)

    args = parser.parse_args(["payload", "setup", "--quiet"])
    assert args.quiet is True
    assert callable(args.func)

    args = parser.parse_args(
        ["payload", "env", "--regenerate", "--yes", "--dry-run"]
    )
    assert args.regenerate is True
    assert args.yes is True
    assert args.dry_run is True


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


def test_run_dev_requires_setup() -> None:
    ns = argparse.Namespace()
    env = EnvironmentContext(env_type=EnvironmentType.HOST)
    ctx = CommandContext(env=env, args=ns)
    with (
        patch(
            "xgic.cli.payload.commands.dev.is_payload_project_complete",
            return_value=False,
        ),
        patch(
            "xgic.cli.payload.commands.dev.resolve_project_dir",
            return_value=Path("app"),
        ),
    ):
        assert run_dev(ctx) == 1


def test_run_dev_when_ready_on_host() -> None:
    ns = argparse.Namespace()
    env = EnvironmentContext(env_type=EnvironmentType.HOST)
    ctx = CommandContext(env=env, args=ns)
    with (
        patch(
            "xgic.cli.payload.commands.dev.make_payload_docker_controller"
        ) as make,
        patch("xgic.cli.payload.commands.dev.db_ready", return_value=True),
        patch(
            "xgic.cli.payload.commands.dev.is_payload_project_complete",
            return_value=True,
        ),
        patch(
            "xgic.cli.payload.commands.dev.resolve_project_dir",
            return_value=Path("app"),
        ),
        patch(
            "xgic.cli.payload.commands.dev._app_cwd",
            return_value=Path("/tmp/app"),
        ),
        patch("pathlib.Path.is_file", return_value=True),
    ):
        docker = MagicMock()
        docker.exec.return_value = MagicMock(returncode=0)
        make.return_value = docker
        assert run_dev(ctx) == 0
        docker.exec.assert_called()
        docker.up.assert_not_called()
        # Must not use the old trap-exit-0 shell wrapper.
        joined = " ".join(str(a) for a in docker.exec.call_args[0])
        assert "trap" not in joined
        assert "exec pnpm dev" in joined


def test_run_dev_in_container_treats_zero_exit_as_failure() -> None:
    ns = argparse.Namespace()
    env = EnvironmentContext(env_type=EnvironmentType.DEV_CONTAINER)
    ctx = CommandContext(env=env, args=ns)
    proc = MagicMock()
    proc.wait.return_value = 0
    proc.poll.return_value = 0
    with (
        patch(
            "xgic.cli.payload.commands.dev.make_payload_docker_controller"
        ) as make,
        patch("xgic.cli.payload.commands.dev.db_ready", return_value=True),
        patch(
            "xgic.cli.payload.commands.dev.is_payload_project_complete",
            return_value=True,
        ),
        patch(
            "xgic.cli.payload.commands.dev.resolve_project_dir",
            return_value=Path("app"),
        ),
        patch(
            "xgic.cli.payload.commands.dev._app_cwd",
            return_value=Path("/tmp/app"),
        ),
        patch("pathlib.Path.is_file", return_value=True),
        patch(
            "xgic.cli.payload.commands.dev.subprocess.Popen",
            return_value=proc,
        ) as popen,
    ):
        make.return_value = MagicMock()
        assert run_dev(ctx) == 1
        popen.assert_called_once()
        assert popen.call_args.args[0] == ["pnpm", "dev"]
        assert "trap" not in str(popen.call_args)

def test_run_reset_dry_run() -> None:
    ns = argparse.Namespace(dry_run=True, yes=False, rotate_credentials=False)
    ctx = CommandContext(
        env=EnvironmentContext(env_type=EnvironmentType.HOST),
        args=ns,
    )
    with patch(
        "xgic.cli.payload.commands.reset.make_payload_docker_controller"
    ) as make:
        make.return_value = MagicMock()
        assert run_reset(ctx) == 0


def test_run_reset_requires_yes() -> None:
    ns = argparse.Namespace(dry_run=False, yes=False, rotate_credentials=False)
    ctx = CommandContext(
        env=EnvironmentContext(env_type=EnvironmentType.HOST),
        args=ns,
    )
    with patch(
        "xgic.cli.payload.commands.reset.make_payload_docker_controller"
    ) as make:
        make.return_value = MagicMock()
        assert run_reset(ctx) == 1
