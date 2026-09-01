"""First-admin bootstrap and development autoLogin inject."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from xgic.cli.payload.admin_bootstrap import (
    ensure_admin_autologin,
    ensure_first_admin_user,
    upsert_admin_env_keys,
)
from xgic.cli.payload.env_helpers import parse_dotenv


def test_upsert_admin_env_keys_adds_missing_and_keeps_password() -> None:
    first = upsert_admin_env_keys("", email="admin@example.com", password="one")
    parsed = parse_dotenv(first)
    assert parsed["PAYLOAD_ADMIN_EMAIL"] == "admin@example.com"
    assert parsed["PAYLOAD_ADMIN_PASSWORD"] == "one"
    second = upsert_admin_env_keys(
        first, email="other@example.com", password="two"
    )
    parsed2 = parse_dotenv(second)
    assert parsed2["PAYLOAD_ADMIN_EMAIL"] == "admin@example.com"
    assert parsed2["PAYLOAD_ADMIN_PASSWORD"] == "one"


def test_ensure_admin_autologin_inserts_once(tmp_path: Path) -> None:
    cfg = tmp_path / "src" / "payload.config.ts"
    cfg.parent.mkdir()
    cfg.write_text(
        "export default buildConfig({\n"
        "  admin: {\n"
        "    user: Users.slug,\n"
        "  },\n"
        "})\n",
        encoding="utf-8",
    )
    assert ensure_admin_autologin(tmp_path) is True
    text = cfg.read_text(encoding="utf-8")
    assert "autoLogin:" in text
    assert "PAYLOAD_ADMIN_EMAIL" in text
    assert "NODE_ENV === 'development'" in text
    assert ensure_admin_autologin(tmp_path) is False
    assert text.count("autoLogin:") == 1


def test_ensure_admin_autologin_missing_config(tmp_path: Path) -> None:
    assert ensure_admin_autologin(tmp_path) is False


class _Resp:
    def __init__(self, payload: object, status: int = 200) -> None:
        self._payload = payload
        self.status = status

    def read(self) -> bytes:
        return json.dumps(self._payload).encode()

    def __enter__(self) -> _Resp:
        return self

    def __exit__(self, *args: object) -> None:
        return None


def test_ensure_first_admin_user_exists() -> None:
    with patch(
        "xgic.cli.payload.admin_bootstrap.urllib.request.urlopen",
        return_value=_Resp({"initialized": True}),
    ):
        assert (
            ensure_first_admin_user(
                base_url="http://127.0.0.1:3000",
                email="a@b.c",
                password="x",
            )
            == "exists"
        )


def test_ensure_first_admin_user_created() -> None:
    calls: list[str] = []

    def fake_open(req: object, timeout: float = 0) -> _Resp:
        url = req if isinstance(req, str) else getattr(req, "full_url", "")
        calls.append(str(url))
        if "init" in str(url):
            return _Resp({"initialized": False})
        return _Resp({"token": "t"}, status=200)

    with patch(
        "xgic.cli.payload.admin_bootstrap.urllib.request.urlopen",
        side_effect=fake_open,
    ):
        assert (
            ensure_first_admin_user(
                base_url="http://127.0.0.1:3000",
                email="a@b.c",
                password="x",
            )
            == "created"
        )
    assert any("first-register" in c for c in calls)


def test_ensure_first_admin_user_unreachable() -> None:
    with patch(
        "xgic.cli.payload.admin_bootstrap.urllib.request.urlopen",
        side_effect=OSError("down"),
    ):
        assert (
            ensure_first_admin_user(
                base_url="http://127.0.0.1:3000",
                email="a@b.c",
                password="x",
            )
            == "unreachable"
        )
