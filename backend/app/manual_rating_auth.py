from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import sys
from typing import Any, Callable

from fastapi import HTTPException, Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SESSION_USER_KEY = "manual_rating_user"
PBKDF2_ITERATIONS = 120_000
SESSION_COOKIE = "session"
SESSION_SECRET_ENV_VAR = "MANUAL_RATING_SESSION_SECRET"
TEST_SESSION_SECRET_FALLBACK = "manual-rating-test-fallback-secret"

_user_lookup_by_username: Callable[[str], dict[str, Any] | None] | None = None


class SignedSessionMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        *,
        secret_key: str,
        same_site: str = "lax",
        https_only: bool = False,
    ) -> None:
        self.app = app
        self.secret_key = secret_key.encode("utf-8")
        self.same_site = same_site
        self.https_only = https_only

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = {
            key.decode("latin-1"): value.decode("latin-1")
            for key, value in scope.get("headers", [])
        }
        initial_session = self._load_session(headers.get("cookie", ""))
        scope["session"] = dict(initial_session)

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                response_headers = MutableHeaders(scope=message)
                session = scope.get("session", {})
                if session:
                    response_headers.append(
                        "Set-Cookie",
                        self._build_set_cookie_value(session),
                    )
                elif initial_session:
                    response_headers.append(
                        "Set-Cookie",
                        self._clear_cookie_value(),
                    )
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _load_session(self, cookie_header: str) -> dict[str, Any]:
        cookies = {}
        for chunk in cookie_header.split(";"):
            if "=" not in chunk:
                continue
            key, value = chunk.split("=", 1)
            cookies[key.strip()] = value.strip()
        token = cookies.get(SESSION_COOKIE)
        if not token:
            return {}
        try:
            payload_b64, signature = token.split(".", 1)
            payload = base64.urlsafe_b64decode(payload_b64.encode("ascii"))
        except (ValueError, UnicodeEncodeError):
            return {}
        expected_signature = hmac.new(self.secret_key, payload, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return {}
        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _build_set_cookie_value(self, session: dict[str, Any]) -> str:
        payload = json.dumps(session, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        payload_b64 = base64.urlsafe_b64encode(payload).decode("ascii")
        signature = hmac.new(self.secret_key, payload, hashlib.sha256).hexdigest()
        cookie = f"{SESSION_COOKIE}={payload_b64}.{signature}; path=/; SameSite={self.same_site}"
        cookie += "; HttpOnly"
        if self.https_only:
            cookie += "; Secure"
        return cookie

    def _clear_cookie_value(self) -> str:
        cookie = f"{SESSION_COOKIE}=null; path=/; Max-Age=0; SameSite={self.same_site}; HttpOnly"
        if self.https_only:
            cookie += "; Secure"
        return cookie


def get_session_secret() -> str:
    configured_secret = os.environ.get(SESSION_SECRET_ENV_VAR)
    if configured_secret:
        return configured_secret
    if "pytest" in sys.modules:
        return TEST_SESSION_SECRET_FALLBACK
    raise RuntimeError(
        f"{SESSION_SECRET_ENV_VAR} must be set for manual rating session signing outside tests"
    )


def configure_user_lookup(lookup_by_username: Callable[[str], dict[str, Any] | None]) -> None:
    global _user_lookup_by_username
    _user_lookup_by_username = lookup_by_username


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return f"{salt.hex()}:{digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_hex, digest_hex = stored_hash.split(":", 1)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except ValueError:
        return False
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
    )
    return hmac.compare_digest(actual, expected)


def require_logged_in(request: Request) -> dict[str, Any]:
    session_user = request.session.get(SESSION_USER_KEY)
    if not session_user:
        raise HTTPException(status_code=401, detail="not authenticated")
    username = _session_username(session_user)
    lookup_by_username = _lookup_by_username(request)
    if username is None or lookup_by_username is None:
        request.session.clear()
        raise HTTPException(status_code=401, detail="not authenticated")
    user = lookup_by_username(username)
    if user is None or not user["active"]:
        request.session.clear()
        raise HTTPException(status_code=401, detail="not authenticated")
    request.session[SESSION_USER_KEY] = {"username": user["username"]}
    return {
        key: user[key]
        for key in ("id", "username", "display_name", "role", "active")
    }


def require_admin(request: Request) -> dict[str, Any]:
    user = require_logged_in(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin required")
    return user


def _session_username(session_user: Any) -> str | None:
    if isinstance(session_user, str):
        return session_user
    if isinstance(session_user, dict):
        username = session_user.get("username")
        if isinstance(username, str):
            return username
    return None


def _lookup_by_username(request: Request) -> Callable[[str], dict[str, Any] | None] | None:
    repository = getattr(request.app.state, "manual_rating_repository", None)
    if repository is not None and hasattr(repository, "find_user_by_username"):
        return repository.find_user_by_username
    return _user_lookup_by_username
