"""Password hashing (argon2) and email normalization."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

_hasher = PasswordHasher()


def normalize_email(email: str) -> str:
    """Lowercase and strip for global uniqueness and lookup."""
    return email.strip().lower()


def hash_password(plain: str) -> str:
    """Hash a password for storage."""
    return _hasher.hash(plain)


def verify_password(plain: str, password_hash: str | None) -> bool:
    """Return True if plain matches hash."""
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, plain)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False
