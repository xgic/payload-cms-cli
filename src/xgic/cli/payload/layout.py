"""Resolve where the Payload CMS app lives relative to the workspace.

Producer (image) repos scaffold into a stable ``projectDir`` (default ``app/``).
Application / template repos use the workspace root (app-root layout).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

LayoutMode = Literal["auto", "app-root", "subdir"]

DEFAULT_PRODUCER_PROJECT_DIR = "app"


def is_producer_repo(root: Path | None = None) -> bool:
    """Return True when cwd looks like the payload-cms-dev image producer."""
    base = root if root is not None else Path.cwd()
    if (base / ".devcontainer" / "Dockerfile").is_file():
        return True
    pyproject = base / "pyproject.toml"
    if pyproject.is_file():
        try:
            text = pyproject.read_text(encoding="utf-8")
        except OSError:
            return False
        if "xgic-payload-cms-dev" in text:
            return True
    return False


def normalize_layout(raw: Any) -> LayoutMode:
    """Normalize layout config value to a known mode."""
    if not isinstance(raw, str) or not raw.strip():
        return "auto"
    value = raw.strip().lower().replace("_", "-")
    if value in ("app-root", "approot", "root"):
        return "app-root"
    if value in ("subdir", "sub-dir", "directory"):
        return "subdir"
    return "auto"


def resolve_project_dir(
    config: dict[str, Any],
    *,
    root: Path | None = None,
) -> Path:
    """Return the relative Path where the Payload app should live.

    Precedence:
    1. Explicit ``projectDir`` (``.`` means workspace root)
    2. ``layout: app-root`` → ``.``
    3. ``layout: subdir`` → ``app`` (stable default; not projectName)
    4. ``layout: auto`` → producer → ``app``; else app-root ``.``
    """
    base = root if root is not None else Path.cwd()
    layout = normalize_layout(config.get("layout"))

    explicit = config.get("projectDir")
    if explicit is not None and str(explicit).strip() not in ("", "null", "None"):
        raw = str(explicit).strip().replace("\\", "/")
        if raw in (".", "./"):
            return Path(".")
        return Path(raw.lstrip("./"))

    if layout == "app-root":
        return Path(".")
    if layout == "subdir":
        return Path(DEFAULT_PRODUCER_PROJECT_DIR)

    # auto
    if is_producer_repo(base):
        return Path(DEFAULT_PRODUCER_PROJECT_DIR)
    return Path(".")


def create_payload_target_arg(project_dir: Path) -> str:
    """Argument passed to create-payload-app for the target directory."""
    if project_dir == Path(".") or str(project_dir) in (".", ""):
        return "."
    return project_dir.as_posix().strip("/")


def is_workspace_root(project_dir: Path) -> bool:
    """Return True when *project_dir* is the workspace root (app-root layout)."""
    return project_dir == Path(".") or str(project_dir).strip() in (".", "./", "")


def display_project_location(project_dir: Path) -> str:
    """Human-readable location for logs."""
    if is_workspace_root(project_dir):
        return "workspace root (.)"
    return f"{project_dir.as_posix()}/"
