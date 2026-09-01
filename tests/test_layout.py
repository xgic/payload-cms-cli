"""Tests for Payload app layout resolution."""

from __future__ import annotations

from pathlib import Path

from xgic.cli.payload.layout import (
    create_payload_target_arg,
    is_producer_repo,
    is_workspace_root,
    normalize_layout,
    resolve_project_dir,
)


def test_normalize_layout() -> None:
    assert normalize_layout(None) == "auto"
    assert normalize_layout("app-root") == "app-root"
    assert normalize_layout("ROOT") == "app-root"
    assert normalize_layout("subdir") == "subdir"


def test_resolve_explicit_project_dir() -> None:
    assert resolve_project_dir({"projectDir": "app"}) == Path("app")
    assert resolve_project_dir({"projectDir": "."}) == Path(".")
    assert resolve_project_dir({"projectDir": "./app"}) == Path("app")


def test_resolve_app_root_layout() -> None:
    assert resolve_project_dir({"layout": "app-root"}) == Path(".")


def test_resolve_subdir_layout_uses_stable_app() -> None:
    assert resolve_project_dir({"layout": "subdir"}) == Path("app")
    # projectName must not become the path when layout is subdir
    assert (
        resolve_project_dir({"layout": "subdir", "projectName": "website"})
        == Path("app")
    )


def test_auto_producer(tmp_path: Path, monkeypatch: object) -> None:
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "Dockerfile").write_text("FROM scratch\n")
    monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
    assert is_producer_repo(tmp_path) is True
    assert resolve_project_dir({"layout": "auto"}, root=tmp_path) == Path("app")


def test_auto_template(tmp_path: Path) -> None:
    (tmp_path / ".devcontainer").mkdir()
    (tmp_path / ".devcontainer" / "devcontainer.json").write_text("{}")
    assert is_producer_repo(tmp_path) is False
    assert resolve_project_dir({"layout": "auto"}, root=tmp_path) == Path(".")


def test_create_payload_target_arg() -> None:
    assert create_payload_target_arg(Path(".")) == "."
    assert create_payload_target_arg(Path("app")) == "app"


def test_is_workspace_root() -> None:
    assert is_workspace_root(Path(".")) is True
    assert is_workspace_root(Path("./")) is True
    assert is_workspace_root(Path("app")) is False
