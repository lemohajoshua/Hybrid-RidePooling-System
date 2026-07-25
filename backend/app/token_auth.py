# app/token_auth.py
"""
Lightweight bearer-token authentication.

This is NOT a full OAuth/session system - it's a small, honest RBAC layer:
each token is a signed (id, role, expiry) payload. Endpoints that mutate
data belonging to a specific driver/passenger require this token and check
that the token's id/role actually matches the resource being modified, so
one driver can no longer accept/reject rides or toggle status on behalf of
another just by knowing their driver_id.
"""

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Optional

from fastapi import Header, HTTPException

SECRET_KEY = os.getenv("TOKEN_SECRET", "dev-secret-change-me-in-.env")
TOKEN_TTL_SECONDS = 60 * 60 * 24 * 7  # 7 days


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def create_token(user_id: str, role: str) -> str:
    payload = {"id": user_id, "role": role, "exp": int(time.time()) + TOKEN_TTL_SECONDS}
    payload_bytes = json.dumps(payload).encode()
    payload_b64 = _b64encode(payload_bytes)
    signature = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).digest()
    signature_b64 = _b64encode(signature)
    return f"{payload_b64}.{signature_b64}"


def verify_token(token: str) -> dict:
    try:
        payload_b64, signature_b64 = token.split(".")
        expected_sig = hmac.new(SECRET_KEY.encode(), payload_b64.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(_b64encode(expected_sig), signature_b64):
            raise ValueError("bad signature")
        payload = json.loads(_b64decode(payload_b64))
        if payload.get("exp", 0) < time.time():
            raise ValueError("expired")
        return payload
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired session - please log in again")


async def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """FastAPI dependency: extracts and verifies the bearer token."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing authentication token")
    token = authorization.removeprefix("Bearer ")
    return verify_token(token)


def require_self(current_user: dict, expected_id: str, expected_role: Optional[str] = None):
    """Raise 403 unless the authenticated user IS the resource owner."""
    if expected_role and current_user.get("role") != expected_role:
        raise HTTPException(status_code=403, detail=f"This action requires a {expected_role} account")
    if current_user.get("id") != expected_id:
        raise HTTPException(status_code=403, detail="You can't perform this action on another user's behalf")
