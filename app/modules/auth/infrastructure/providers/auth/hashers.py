"""Password hashing adapter (stdlib PBKDF2-HMAC) — maps no exceptions to domain."""

from __future__ import annotations

import hashlib
import hmac
import secrets

_ITERATIONS = 390_000
_SALT_BYTES = 16


class Pbkdf2PasswordHasher:
    async def __connect__(self) -> None:
        pass

    async def __disconnect__(self) -> None:
        pass

    """PasswordHasher port implemented with `hashlib.pbkdf2_hmac`."""

    def hash(self, password: str) -> str:
        salt = secrets.token_bytes(_SALT_BYTES)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
        return f"pbkdf2_sha256${_ITERATIONS}${salt.hex()}${digest.hex()}"

    def verify(self, password: str, hashed: str) -> bool:
        try:
            _, iterations, salt_hex, digest_hex = hashed.split("$")
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(digest_hex)
        except (ValueError, TypeError):
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, int(iterations))
        return hmac.compare_digest(digest, expected)
