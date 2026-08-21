"""``xgic payload dev`` — smart Payload CMS development server start."""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path

from xgic.cli.app import CommandContext
from xgic.cli.core.environment import EnvironmentType
from xgic.cli.payload.config import (
    DEFAULT_PRIMARY_SERVICE,
    db_ready,
    get_compose_project_name,
    get_db_profile,
    make_payload_docker_controller,
)
from xgic.cli.payload.layout import display_project_location, resolve_project_dir
from xgic.cli.payload.project import (
    ensure_db_services,
    is_payload_project_complete,
    load_create_payload_config,
)
from xgic.cli.utils.output import print_info, print_success, print_warning

# Exit codes commonly used when the user presses Ctrl+C / sends SIGINT.
_SIGINT_EXIT_CODES = {130, -signal.SIGINT, 128 + signal.SIGINT}


def _app_cwd(project_dir: Path) -> Path:
    if project_dir == Path("."):
        return Path.cwd()
    return (Path.cwd() / project_dir).resolve()


def _terminate_pnpm(proc: subprocess.Popen[bytes]) -> None:
    if proc.poll() is not None:
        return
    try:
        if sys.platform == "win32":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGINT)
    except OSError:
        pass
    try:
        proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5)


def _report_pnpm_exit(returncode: int, app_cwd: Path) -> int:
    try:
        rel = Path(os.path.relpath(app_cwd, Path.cwd()))
    except ValueError:
        rel = app_cwd
    project_hint = display_project_location(rel)

    if returncode in _SIGINT_EXIT_CODES:
        print_info("Development server stopped by user (Ctrl+C).")
        return 0

    if returncode == 0:
        # Next.js often exits 0 on SIGTERM (child exitCode null -> || 0).
        # That is not a healthy idle end for a long-running app dev server.
        print_warning(
            "The app dev child process exited with code 0 while under "
            "`xgic payload dev`. For a long-running Next.js server that usually means "
            "SIGTERM/SIGINT, a compile crash, or the terminal session ended "
            "- not a normal idle shutdown."
        )
        print_info("Retry with: xgic payload dev")
        print_info(
            f"If it stops again while Compiling / (app: {project_hint}), "
            "check DB connectivity, free memory, and (on bind-mounted "
            "Windows workspaces) named volumes for node_modules/.next."
        )
        return 1

    print_warning(
        f"The app dev child process exited with code {returncode} "
        "(launched by `xgic payload dev`)."
    )
    print_info("Retry with: xgic payload dev")
    return returncode or 1


def _run_pnpm_dev(app_cwd: Path) -> int:
    """Run pnpm dev in the foreground until it stops.

    Do not install shell ``trap ... exit 0`` handlers: they made SIGTERM
    stops look like a successful idle exit while the page was still
    compiling / serving. Inherit stdio so the VS Code terminal stays attached.
    """
    print_info(f"Launching pnpm dev in {app_cwd}...")
    env = os.environ.copy()
    if env.get("CI", "").lower() in {"1", "true", "yes"}:
        print_warning(
            "CI=true is set in this environment; unsetting for pnpm dev "
            "so Next.js stays in interactive watch mode."
        )
        env["CI"] = ""

    try:
        proc = subprocess.Popen(
            ["pnpm", "dev"],
            cwd=str(app_cwd),
            env=env,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
    except FileNotFoundError:
        print_warning(
            "pnpm not found. Run inside the Dev Container image "
            "(or install pnpm on PATH)."
        )
        return 1

    try:
        returncode = proc.wait()
    except KeyboardInterrupt:
        print_info("Stopping development server (Ctrl+C)...")
        _terminate_pnpm(proc)
        print_info("Development server stopped by user (Ctrl+C).")
        return 0

    return _report_pnpm_exit(returncode, app_cwd)


def run_dev(ctx: CommandContext) -> int:
    """Start DB if needed and launch the Payload CMS app dev server."""
    env = ctx.env
    cfg = load_create_payload_config()
    project_dir = resolve_project_dir(cfg)

    if not is_payload_project_complete(project_dir):
        print_warning(
            "Payload CMS app is not set up yet at "
            f"{display_project_location(project_dir)}."
        )
        print_info("Run first:  xgic payload env --regenerate --yes")
        print_info("Then:       xgic payload setup")
        print_info("Then:       xgic payload dev")
        return 1

    print_info("Starting Payload CMS development server...")
    print_info(f"App location: {display_project_location(project_dir)}")

    docker = make_payload_docker_controller(env)
    docker.project_name = get_compose_project_name()
    profile = get_db_profile()

    # Never recreate the primary Dev Container service; only ensure DB.
    if not db_ready(docker):
        print_warning(
            f"Database ({profile}) not ready. Starting DB service only..."
        )
        db_rc = ensure_db_services(quiet=False)
        if db_rc != 0:
            print_warning(
                "Could not start database. Fix Compose/DB, then re-run "
                "xgic payload dev."
            )
            return db_rc
    else:
        print_success("Database is ready")

    app_cwd = _app_cwd(project_dir)
    if not (app_cwd / "package.json").is_file():
        print_warning(f"No package.json under {app_cwd}")
        return 1

    if env.env_type in (
        EnvironmentType.DEV_CONTAINER,
        EnvironmentType.GENERIC_CONTAINER,
    ):
        return _run_pnpm_dev(app_cwd)

    # Host: try docker exec into primary service (optional path)
    rel = (
        "."
        if project_dir == Path(".")
        else project_dir.as_posix().strip("/")
    )
    try:
        print_info(
            f"Launching pnpm dev via container service "
            f"{DEFAULT_PRIMARY_SERVICE!r}..."
        )
        docker.exec(
            DEFAULT_PRIMARY_SERVICE,
            "sh",
            "-c",
            f"cd /workspace/{rel} && exec pnpm dev",
            check=False,
        )
    except Exception as e:
        print_warning(f"Failed to launch pnpm dev from host: {e}")
        print_info(
            "Prefer: Dev Containers → Reopen in Container, then "
            "xgic payload dev"
        )
        return 1

    print_success("Environment ready for development.")
    print_info("Environment context: " + env.describe())
    return 0
