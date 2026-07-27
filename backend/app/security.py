# app/security.py
"""
Password hashing utilities. Centralised so auth.py never has to touch a
raw password beyond hashing it once at registration.

Uses the `bcrypt` library directly rather than passlib - passlib 1.7.4
(its last release) is incompatible with bcrypt 4.1+ (it crashes with
"module 'bcrypt' has no attribute '__about__'" because it tries to read
an internal version marker that newer bcrypt removed). Calling bcrypt
directly avoids that whole problem.
"""

from typing import Optional
import bcrypt


def hash_password(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed.decode('utf-8')


def verify_password(plain_password: str, password_hash: Optional[str]) -> bool:
    """Returns False (never raises) if there's no hash to compare against,
    e.g. a legacy row created before this migration."""
    if not password_hash:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), password_hash.encode('utf-8'))
    except (ValueError, TypeError):
        return False
