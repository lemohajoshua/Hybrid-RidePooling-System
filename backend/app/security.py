# app/security.py
"""
Password hashing utilities. Centralised so auth.py never has to touch a
raw password beyond hashing it once at registration.
"""

from typing import Optional
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, password_hash: Optional[str]) -> bool:
    """Returns False (never raises) if there's no hash to compare against,
    e.g. a legacy row created before this migration."""
    if not password_hash:
        return False
    try:
        return pwd_context.verify(plain_password, password_hash)
    except (ValueError, TypeError):
        return False
