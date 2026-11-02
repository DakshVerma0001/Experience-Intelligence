"""
Authentication for Experience Intelligence itself.

IMPORTANT: this identity system is intentionally separate from the production
Knowledge Repository portal's user accounts. Experience Intelligence never
stores or transmits a user's production portal password. See docs/security.md
for the SSO integration point if/when this app is wired to a shared identity
provider (e.g. the portal's Supabase Auth via OIDC).
"""
from __future__ import annotations

import datetime as dt

import jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str, role: str, extra: dict | None = None) -> str:
    settings = get_settings()
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "exp": now + dt.timedelta(minutes=settings.access_token_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])


def create_service_token(client_id: str, secret: str, audience: str) -> str:
    """Short-lived signed token for machine-to-machine calls to the production
    portal import gateway. Never contains a user password."""
    now = dt.datetime.now(dt.timezone.utc)
    payload = {
        "sub": client_id,
        "aud": audience,
        "iat": now,
        "exp": now + dt.timedelta(minutes=5),
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)
