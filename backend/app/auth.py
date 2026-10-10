"""Authentication.

Two independent mechanisms:
- Admin API + dashboard: `Authorization: Bearer <API_KEY>` (or `X-API-Key`),
  or a signed, HttpOnly session cookie issued by POST /auth/login.
- Vapi webhook: shared secret in the `X-Vapi-Secret` header. Kept separate so
  dashboard auth can never block the voice agent (and vice versa).
"""

import hmac

from fastapi import Request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.config import get_settings
from app.envelope import APIError

SESSION_COOKIE = "pr_session"
SESSION_MAX_AGE = 60 * 60 * 12  # 12 hours


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().secret_key, salt="dashboard-session")


def _matches(provided: str | None, expected: str) -> bool:
    return bool(provided) and hmac.compare_digest(provided.encode(), expected.encode())


def issue_session_token() -> str:
    return _serializer().dumps({"role": "admin"})


def api_key_is_valid(key: str) -> bool:
    return _matches(key, get_settings().api_key)


def require_admin(request: Request) -> None:
    """FastAPI dependency guarding patient and call-log endpoints."""
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer ") and api_key_is_valid(auth[7:].strip()):
        return
    if api_key_is_valid(request.headers.get("x-api-key", "")):
        return
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        try:
            _serializer().loads(token, max_age=SESSION_MAX_AGE)
            return
        except (BadSignature, SignatureExpired):
            pass
    raise APIError(401, "UNAUTHORIZED", "Missing or invalid credentials.")


def require_vapi_secret(request: Request) -> None:
    if not _matches(request.headers.get("x-vapi-secret"), get_settings().vapi_webhook_secret):
        raise APIError(401, "UNAUTHORIZED", "Invalid webhook secret.")
