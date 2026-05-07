from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
from typing import Any

from fastapi import HTTPException, Request
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

SESSION_USER_KEY = "manual_rating_user"
PBKDF2_ITERATIONS = 120_000
SESSION_COOKIE = "session"


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
                        f"{SESSION_COOKIE}=null; path=/; Max-Age=0; SameSite={self.same_site}",
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
        if self.https_only:
            cookie += "; Secure"
        return cookie


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
    except ValueError:
        return False
    expected = bytes.fromhex(digest_hex)
    actual = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
    )
    return hmac.compare_digest(actual, expected)


def require_logged_in(request: Request) -> dict[str, Any]:
    user = request.session.get(SESSION_USER_KEY)
    if not user:
        raise HTTPException(status_code=401, detail="not authenticated")
    return user


def require_admin(request: Request) -> dict[str, Any]:
    user = require_logged_in(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin required")
    return user
