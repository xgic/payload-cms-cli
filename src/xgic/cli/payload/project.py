"""Payload CMS project setup / ensure helpers."""

from __future__ import annotations

import contextlib
import json
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from xgic.cli.payload.config import (
    DEFAULT_COMPOSE_FILE,
    DEFAULT_CONFIG_FILE,
    db_ready,
    get_compose_project_name,
    get_db_profile,
    make_payload_docker_controller,
)
from xgic.cli.payload.env_helpers import (
    load_live_env_from_devcontainer,
    sync_live_env_into_project,
)
from xgic.cli.payload.layout import (
    create_payload_target_arg,
    display_project_location,
    resolve_project_dir,
)
from xgic.cli.utils.output import print_info, print_success, print_warning

_sync_live_env_into_project = sync_live_env_into_project

# Native packages whose install scripts pnpm 10+ otherwise skips.
# @swc/core is required by create-payload-app itself; the rest match the
# website template allow-list plus Next.js optional native add-ons.
NATIVE_PNPM_BUILDS: tuple[str, ...] = (
    "@swc/core",
    "@parcel/watcher",
    "esbuild",
    "sharp",
    "unrs-resolver",
    "workerd",
)


def load_create_payload_config(
    config_path: Path = DEFAULT_CONFIG_FILE,
) -> dict[str, Any]:
    """Load create-payload-config.json (or sensible defaults)."""
    defaults: dict[str, Any] = {
        "projectName": "my-payload-cms",
        "projectDir": None,
        "layout": "auto",
        "composeProjectName": None,
        "template": "website",
        "dbAdapter": "postgres",
        "agent": "none",
        "dbUri": "",
    }
    if not config_path.exists():
        return defaults
    try:
        with config_path.open(encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        for k, v in data.items():
            if v is not None:
                defaults[k] = v
        return defaults
    except (json.JSONDecodeError, OSError):
        return defaults


def get_project_name(config: dict[str, Any]) -> str:
    """Extract projectName with safe default (identity, not necessarily path)."""
    name = config.get("projectName")
    if isinstance(name, str) and name.strip():
        return name.strip()
    return "my-payload-cms"


def is_payload_project_complete(project_dir: Path) -> bool:
    """Return True if project_dir looks like a finished Payload CMS app."""
    base = Path.cwd() if project_dir == Path(".") else project_dir
    if not base.is_dir():
        return False
    candidates = [
        base / "payload.config.ts",
        base / "payload.config.js",
        base / "src" / "payload.config.ts",
        base / "src" / "payload.config.js",
    ]
    return any(p.exists() for p in candidates)


def pnpx_allow_build_args(
    packages: tuple[str, ...] = NATIVE_PNPM_BUILDS,
) -> list[str]:
    """Return ``pnpx --allow-build=…`` flags for native install scripts."""
    return [f"--allow-build={name}" for name in packages]


def merge_package_json_only_built(
    text: str, names: tuple[str, ...] = NATIVE_PNPM_BUILDS
) -> str:
    """Return package.json text with ``pnpm.onlyBuiltDependencies`` merged."""
    data = json.loads(text)
    pnpm = data.setdefault("pnpm", {})
    existing = pnpm.get("onlyBuiltDependencies") or []
    if not isinstance(existing, list):
        existing = []
    str_existing = [str(item) for item in existing]
    merged = list(dict.fromkeys([*str_existing, *names]))
    if merged == str_existing:
        return text
    pnpm["onlyBuiltDependencies"] = merged
    return json.dumps(data, indent=2) + "\n"


def merge_workspace_allow_builds(
    text: str, names: tuple[str, ...] = NATIVE_PNPM_BUILDS
) -> str:
    """Return pnpm-workspace.yaml text with ``allowBuilds`` keys merged.

    Avoids a YAML dependency: only handles the generated website-template
    shape (a top-level ``allowBuilds:`` mapping of ``name: true``).
    """
    normalized = text if text.endswith("\n") or text == "" else text + "\n"
    lines = normalized.splitlines()
    start = next(
        (i for i, ln in enumerate(lines) if ln.startswith("allowBuilds:")),
        None,
    )
    if start is None:
        extra = ["allowBuilds:"] + [f"  {n}: true" for n in names]
        return normalized + "\n".join(extra) + "\n"

    existing: list[str] = []
    end = start + 1
    while end < len(lines):
        ln = lines[end]
        if not ln.strip():
            end += 1
            continue
        if ln.startswith(" ") or ln.startswith("\t"):
            existing.append(ln.strip().split(":", 1)[0].strip())
            end += 1
            continue
        break
    missing = [n for n in names if n not in existing]
    if not missing:
        return normalized
    insert = [f"  {n}: true" for n in missing]
    new_lines = lines[:end] + insert + lines[end:]
    return "\n".join(new_lines) + "\n"


def ensure_native_pnpm_builds(
    project_dir: Path, *, quiet: bool = False
) -> None:
    """Allow-list native install scripts in a generated Payload CMS app."""
    changed = False
    workspace = project_dir / "pnpm-workspace.yaml"
    package_json = project_dir / "package.json"
    try:
        if workspace.is_file():
            old = workspace.read_text(encoding="utf-8")
            new = merge_workspace_allow_builds(old)
            if new != old:
                workspace.write_text(new, encoding="utf-8")
                changed = True
        if package_json.is_file():
            old = package_json.read_text(encoding="utf-8")
            new = merge_package_json_only_built(old)
            if new != old:
                package_json.write_text(new, encoding="utf-8")
                changed = True
    except (OSError, json.JSONDecodeError) as e:
        if not quiet:
            print_warning(f"Could not update pnpm native allow-list: {e}")
        return
    if not changed:
        return
    if not quiet:
        print_info(
            "Allowing native pnpm install scripts "
            f"({', '.join(NATIVE_PNPM_BUILDS)}) in "
            f"{display_project_location(project_dir)}."
        )
    result = subprocess.run(
        ["pnpm", "install"],
        cwd=str(project_dir),
        check=False,
    )
    if result.returncode != 0 and not quiet:
        print_warning(
            "pnpm install after native allow-list update exited "
            f"{result.returncode}. Re-run inside the app directory if "
            "install scripts were skipped."
        )


def build_create_payload_command(
    target: str,
    *,
    template: str = "website",
    db_adapter: str = "postgres",
    db_connection_string: str | None = None,
    agent: str = "none",
) -> list[str]:
    """Return the argv list for a non-interactive create-payload-app run."""
    cmd = [
        "pnpx",
        *pnpx_allow_build_args(),
        "create-payload-app@latest",
        target,
        "-t",
        template,
        "--use-pnpm",
    ]

    if db_connection_string:
        cmd.extend(
            ["--db", db_adapter, "--db-connection-string", db_connection_string]
        )
    else:
        cmd.extend(["--db", db_adapter, "--db-accept-recommended"])

    if agent and str(agent).lower() not in ("", "none"):
        cmd.extend(["--agent", str(agent)])
    else:
        cmd.append("--no-agent")

    return cmd


def resolve_db_connection_string(
    json_db_uri: str, live_db_uri: str
) -> str | None:
    """Prefer live env DB URI over config JSON."""
    return live_db_uri or json_db_uri or None


def validate_compose_project_name(name: str) -> str:
    """Return a Docker Compose–safe project name or raise ValueError."""
    cleaned = name.strip().lower()
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,62}", cleaned):
        raise ValueError(
            f"Invalid projectName for Docker Compose: {name!r}. "
            "Use 1–63 chars: start with a letter or digit; then [a-z0-9_-]."
        )
    return cleaned


def sync_compose_project_name(
    project_name: str,
    *,
    compose_path: Path = Path(DEFAULT_COMPOSE_FILE),
) -> bool:
    """Set the top-level Compose ``name:`` field to *project_name*.

    Returns True when the file was updated, False when unchanged/skipped.
    """
    try:
        safe = validate_compose_project_name(project_name)
    except ValueError as e:
        print_warning(str(e))
        return False
    if not compose_path.is_file():
        return False
    try:
        text = compose_path.read_text(encoding="utf-8")
    except OSError as e:
        print_warning(f"Could not read {compose_path}: {e}")
        return False
    if re.search(r"(?m)^name:\s*", text):
        new_text, n = re.subn(
            r"(?m)^name:\s*.*$",
            f"name: {safe}",
            text,
            count=1,
        )
        if n == 0:
            return False
    else:
        new_text = f"name: {safe}\n{text}"
    if new_text == text:
        return False
    try:
        compose_path.write_text(new_text, encoding="utf-8")
    except OSError as e:
        print_warning(f"Could not write {compose_path}: {e}")
        return False
    return True


def ensure_devcontainer_env(*, quiet: bool = False) -> int:
    """Ensure ``.devcontainer/.env`` exists (create with fresh credentials if missing)."""
    from xgic.cli.payload.env_helpers import ENV_FILE, perform_env_regenerate

    if ENV_FILE.is_file():
        return 0
    if not quiet:
        print_info(
            f"{ENV_FILE} not found — generating credentials "
            "(same as: xgic payload env --regenerate --yes)"
        )
    return perform_env_regenerate(yes=True, env_file=ENV_FILE)


def ensure_db_services(*, quiet: bool = False, wait_seconds: float = 45.0) -> int:
    """Start only the DB Compose profile service (never recreate the IDE primary)."""
    from xgic.cli.core.environment import EnvironmentContext

    if not Path(DEFAULT_COMPOSE_FILE).is_file():
        if not quiet:
            print_info(
                f"No {DEFAULT_COMPOSE_FILE}; skipping Compose DB bring-up."
            )
        return 0

    env = EnvironmentContext.detect()
    docker = make_payload_docker_controller(env)
    compose_project = get_compose_project_name()
    docker.project_name = compose_project
    profile = get_db_profile()

    if db_ready(docker):
        if not quiet:
            print_success(f"Database service ({profile}) already ready.")
        return 0

    if not quiet:
        print_info(
            f"Starting database service only: service={profile!r} "
            f"(project {compose_project!r})"
        )
    try:
        # Start the named service without forcing --profile. Services that use
        # profiles still start when listed by name if already enabled; services
        # without profiles (e.g. always-on postgres) work without a profile flag.
        docker.up(services=[profile])
    except FileNotFoundError:
        print_warning(
            "docker not found. Run setup inside the Dev Container "
            "(or ensure Docker CLI is on PATH)."
        )
        return 1
    except subprocess.CalledProcessError as e:
        print_warning(f"Failed to start database service: {e}")
        print_info(
            "Tip: from inside the Dev Container, try: "
            f"xgic up --profile {profile}"
        )
        return 1

    deadline = time.monotonic() + wait_seconds
    while time.monotonic() < deadline:
        if db_ready(docker):
            if not quiet:
                print_success(f"Database service ({profile}) is ready.")
            return 0
        time.sleep(1.0)

    print_warning(
        f"Database service ({profile}) did not become ready within "
        f"{int(wait_seconds)}s. Continuing with scaffold; "
        "re-check with: xgic payload env"
    )
    return 0


def ensure_payload_project(*, quiet: bool = False) -> int:
    """Ensure the Payload CMS project exists and is usable."""
    cfg = load_create_payload_config()
    project_name = get_project_name(cfg)
    try:
        project_name = validate_compose_project_name(project_name)
    except ValueError as e:
        print_warning(str(e))
        return 1

    project_dir = resolve_project_dir(cfg)
    target = create_payload_target_arg(project_dir)

    # First-run: create .devcontainer/.env when missing (no separate
    # `xgic payload env --regenerate --yes` step required).
    env_rc = ensure_devcontainer_env(quiet=quiet)
    if env_rc != 0:
        return env_rc

    # Compose project name from config (composeProjectName), not npm projectName.
    compose_project = get_compose_project_name()
    if sync_compose_project_name(compose_project) and not quiet:
        print_info(
            f"Docker Compose project name set to {compose_project!r} "
            f"in {DEFAULT_COMPOSE_FILE}"
        )

    if is_payload_project_complete(project_dir):
        if not quiet:
            print_success(
                "Payload CMS project already complete at "
                f"{display_project_location(project_dir)}."
            )
        db_rc = ensure_db_services(quiet=quiet)
        return db_rc if db_rc != 0 else 0

    if project_dir != Path(".") and project_dir.exists() and not quiet:
        print_warning(
            f"Directory '{project_dir.as_posix()}' exists but does not appear "
            "to be a complete Payload CMS project. Creation may overwrite or fail."
        )

    db_rc = ensure_db_services(quiet=quiet)
    if db_rc != 0 and not quiet:
        print_warning(
            "Database bring-up had issues; create-payload-app may still run."
        )

    template = str(cfg.get("template") or "website")
    db_adapter = str(cfg.get("dbAdapter") or "postgres")
    json_db_uri = str(cfg.get("dbUri") or "")
    agent = str(cfg.get("agent") or "none")

    live_db_uri, live_secret = load_live_env_from_devcontainer()
    db_uri_for_cli: str | None = resolve_db_connection_string(
        json_db_uri, live_db_uri
    )

    with contextlib.suppress(Exception):
        subprocess.run(
            ["corepack", "enable"],
            check=False,
            capture_output=True,
        )

    cmd = build_create_payload_command(
        target,
        template=template,
        db_adapter=db_adapter,
        db_connection_string=db_uri_for_cli,
        agent=agent,
    )

    if not quiet:
        print_info(
            f"Starting Payload CMS project creation at "
            f"{display_project_location(project_dir)} "
            f"(projectName={project_name!r}, template={template}, db={db_adapter})..."
        )
        print_info("Command: " + " ".join(cmd))

    try:
        result = subprocess.run(cmd, check=False)
    except FileNotFoundError as e:
        print_warning(f"Required tool not found for project creation: {e}")
        print_info(
            "Run `xgic payload setup` inside the VS Code Dev Container "
            "(Node/pnpm/pnpx are provided by the image). "
            "Host Windows without Node is not supported for setup yet."
        )
        return 1

    if result.returncode != 0:
        if not quiet:
            print_warning(
                f"create-payload-app exited with status {result.returncode}."
            )
            print_info(
                "Setup failed. Fix the error above, then re-run: "
                "xgic payload setup"
            )
        return result.returncode if result.returncode != 0 else 1

    if not is_payload_project_complete(project_dir):
        if not quiet:
            print_warning(
                "create-payload-app reported success but "
                f"{display_project_location(project_dir)} does not look like a "
                "complete Payload project (missing payload.config)."
            )
        return 1

    if not quiet:
        print_success(
            "Payload CMS project created successfully at "
            f"{display_project_location(project_dir)}."
        )
    ensure_native_pnpm_builds(project_dir, quiet=quiet)
    _sync_live_env_into_project(project_dir, live_db_uri, live_secret)
    return 0
