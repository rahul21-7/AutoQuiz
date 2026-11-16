import hashlib
import os
import secrets
from typing import Tuple

def hash_password(password: str) -> Tuple[str, str]:
    """Generates a secure salted PBKDF2 hash for a password (SRS 5.3, TC-01)."""
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100000
    )
    return key.hex(), salt

def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verifies a plain password against the stored salted PBKDF2 hash."""
    key = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations=100000
    )
    return secrets.compare_digest(key.hex(), stored_hash)

def generate_session_token() -> str:
    """Generates a cryptographically random session token."""
    return secrets.token_urlsafe(32)

