"""First-admin bootstrap for Next.js 16 blank unauthenticated /admin.

Unauthenticated Payload admin routes on Next.js 16 render an empty RSC shell
(payloadcms/payload#17545). Authenticated /admin and development autoLogin
render the dashboard. Do not vendor a Next.js patch.
"""

from __future__ import annotations

import json
import os
import re
import secrets
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

from xgic.cli.payload.config import (
    DEFAULT_ADMIN_EMAIL,
    DEFAULT_CONFIG_FILE,
    get_admin_email,
)
from xgic.cli.payload.env_helpers import (
    ENV_FILE,
    _set_env_key,
    looks_like_placeholder,
    parse_dotenv,
)
from xgic.cli.utils.output import print_info, print_success, print_warning

_AUTOLOGIN_MARKER = re.compile(r"\bautoLogin\s*:")
_ADMIN_OBJECT = re.compile(r"(admin:\s*\{)")
_AUTOLOGIN_BLOCK = """    autoLogin:
      process.env.NODE_ENV === 'development' &&
      process.env.PAYLOAD_ADMIN_EMAIL &&
      process.env.PAYLOAD_ADMIN_PASSWORD
        ? {
            email: process.env.PAYLOAD_ADMIN_EMAIL,
            password: process.env.PAYLOAD_ADMIN_PASSWORD,
          }
        : false,
"""

_CONFIG_CANDIDATES = (
    "src/payload.config.ts",
    "src/payload.config.js",
    "payload.config.ts",
    "payload.config.js",
)


def payload_config_path(project_dir: Path) -> Path | None:
    """Return the generated Payload config path if it exists."""
    base = Path.cwd() if project_dir == Path(".") else project_dir
    for rel in _CONFIG_CANDIDATES:
        path = base / rel
        if path.is_file():
            return path
    return None


def ensure_admin_autologin(project_dir: Path) -> bool:
    """Inject development autoLogin into payload.config.ts. Return True if written."""
    path = payload_config_path(project_dir)
    if path is None:
        return False
    text = path.read_text(encoding="utf-8")
    if _AUTOLOGIN_MARKER.search(text):
        return False
    new, n = _ADMIN_OBJECT.subn(r"\1\n" + _AUTOLOGIN_BLOCK.rstrip("\n"), text, count=1)
    if n != 1:
        return False
    path.write_text(new + ("" if new.endswith("\n") else "\n"), encoding="utf-8")
    return True


def upsert_admin_env_keys(content: str, *, email: str, password: str | None = None) -> str:
    """Ensure PAYLOAD_ADMIN_* keys exist without rotating a real password."""
    parsed = parse_dotenv(content)
    if "PAYLOAD_ADMIN_EMAIL" not in parsed or looks_like_placeholder(
        parsed.get("PAYLOAD_ADMIN_EMAIL", "")
    ):
        content = _set_env_key(content, "PAYLOAD_ADMIN_EMAIL", email)
    existing_password = parsed.get("PAYLOAD_ADMIN_PASSWORD", "")
    if not existing_password or looks_like_placeholder(existing_password):
        content = _set_env_key(
            content,
            "PAYLOAD_ADMIN_PASSWORD",
            password or secrets.token_urlsafe(24),
        )
    return content


def read_admin_credentials(
    env_file: Path = ENV_FILE,
) -> tuple[str, str]:
    """Return (email, password) from compose .env or process env."""
    email = os.environ.get("PAYLOAD_ADMIN_EMAIL", "").strip()
    password = os.environ.get("PAYLOAD_ADMIN_PASSWORD", "").strip()
    if env_file.is_file():
        try:
            parsed = parse_dotenv(env_file.read_text(encoding="utf-8"))
        except OSError:
            parsed = {}
        if not email:
            email = parsed.get("PAYLOAD_ADMIN_EMAIL", "").strip()
        if not password:
            password = parsed.get("PAYLOAD_ADMIN_PASSWORD", "").strip()
    return email, password


def ensure_admin_credential_files(
    *,
    project_dir: Path,
    config_file: Path = DEFAULT_CONFIG_FILE,
    compose_env: Path = ENV_FILE,
    quiet: bool = False,
) -> tuple[str, str]:
    """Write admin email/password to compose and app .env. Return credentials."""
    email = get_admin_email(config_file)
    password = ""
    content = ""
    try:
        if compose_env.is_file():
            content = compose_env.read_text(encoding="utf-8")
            parsed = parse_dotenv(content)
            password = parsed.get("PAYLOAD_ADMIN_PASSWORD", "").strip()
            existing_email = parsed.get("PAYLOAD_ADMIN_EMAIL", "").strip()
            if existing_email and not looks_like_placeholder(existing_email):
                email = existing_email
    except OSError:
        content = ""
    new_content = upsert_admin_env_keys(content, email=email, password=password or None)
    if new_content != content:
        compose_env.parent.mkdir(parents=True, exist_ok=True)
        compose_env.write_text(new_content, encoding="utf-8")
        if not quiet:
            print_info(
                f"Wrote PAYLOAD_ADMIN_EMAIL / PAYLOAD_ADMIN_PASSWORD to {compose_env}"
            )
    email, password = read_admin_credentials(compose_env)
    if not email:
        email = DEFAULT_ADMIN_EMAIL
    if not password:
        password = secrets.token_urlsafe(24)
        compose_env.write_text(
            upsert_admin_env_keys(
                compose_env.read_text(encoding="utf-8")
                if compose_env.is_file()
                else "",
                email=email,
                password=password,
            ),
            encoding="utf-8",
        )

    base = Path.cwd() if project_dir == Path(".") else project_dir
    app_env = base / ".env"
    try:
        if app_env.is_file() or payload_config_path(project_dir) is not None:
            app_content = (
                app_env.read_text(encoding="utf-8") if app_env.is_file() else ""
            )
            synced = upsert_admin_env_keys(
                app_content, email=email, password=password
            )
            if synced != app_content:
                app_env.parent.mkdir(parents=True, exist_ok=True)
                app_env.write_text(synced, encoding="utf-8")
                if not quiet:
                    print_info(f"Synced admin credentials into {app_env}")
    except OSError:
        pass
    return email, password


def ensure_first_admin_user(
    *,
    base_url: str,
    email: str,
    password: str,
    name: str = "Admin",
    timeout: float = 3.0,
) -> str:
    """Idempotent first-register. Return created, exists, or unreachable."""
    root = base_url.rstrip("/")
    try:
        with urllib.request.urlopen(f"{root}/api/users/init", timeout=timeout) as resp:
            init = json.load(resp)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return "unreachable"
    if bool(init.get("initialized")):
        return "exists"
    req = urllib.request.Request(
        f"{root}/api/users/first-register",
        data=json.dumps(
            {"email": email, "password": password, "name": name}
        ).encode(),
        headers={"content-type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if 200 <= resp.status < 300:
                return "created"
    except (urllib.error.URLError, TimeoutError, OSError):
        return "unreachable"
    return "unreachable"


def candidate_base_urls() -> list[str]:
    """Local Next.js origins to probe for first-register."""
    seen: list[str] = []
    for raw in (
        os.environ.get("NEXT_PUBLIC_SERVER_URL", ""),
        "http://127.0.0.1:3000",
        "http://localhost:3000",
    ):
        url = raw.strip().rstrip("/")
        if url and url not in seen:
            seen.append(url)
    return seen


def spawn_first_admin_guard(*, compose_env: Path = ENV_FILE) -> None:
    """After Next listens, create the first admin if the users table is empty."""

    def _run() -> None:
        email, password = read_admin_credentials(compose_env)
        if not email or not password:
            return
        urls = candidate_base_urls()
        for _ in range(90):
            time.sleep(2)
            for url in urls:
                status = ensure_first_admin_user(
                    base_url=url, email=email, password=password
                )
                if status == "created":
                    print_success(
                        f"Created first Payload admin {email}. "
                        "Development autoLogin is enabled for /admin."
                    )
                    return
                if status == "exists":
                    return

    thread = threading.Thread(
        target=_run, name="xgic-first-admin", daemon=True
    )
    thread.start()


def apply_admin_dev_login(
    project_dir: Path,
    *,
    quiet: bool = False,
    config_file: Path = DEFAULT_CONFIG_FILE,
) -> None:
    """Env keys + autoLogin inject for an existing or just-scaffolded app."""
    try:
        ensure_admin_credential_files(
            project_dir=project_dir,
            config_file=config_file,
            quiet=quiet,
        )
        wrote = ensure_admin_autologin(project_dir)
    except OSError as exc:
        if not quiet:
            print_warning(f"Could not enable development admin autoLogin: {exc}")
        return
    if wrote and not quiet:
        print_info(
            "Enabled Payload admin.autoLogin for development "
            "(Next.js 16 unauthenticated /admin is a blank RSC shell; "
            "see payloadcms/payload#17545)."
        )
