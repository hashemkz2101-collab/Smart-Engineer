"""Password hashing, password policy, and opaque-token helpers (DEC-022).

Only the standard library is used. Passwords are hashed with scrypt and stored as
``scrypt$N$r$p$salt$hash`` (URL-safe base64, no padding) so the parameters can be
raised later without invalidating old hashes. Opaque tokens are random and are
stored only as SHA-256 digests, so a database leak does not reveal usable tokens.
"""

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

PASSWORD_MIN_LENGTH = 10
PASSWORD_MAX_LENGTH = 128
# A deliberately tiny denylist; a fuller list is a later hardening item.
COMMON_PASSWORDS = frozenset(
    {
        "password",
        "password1",
        "1234567890",
        "12345678910",
        "qwertyuiop",
        "iloveyou123",
        "letmein1234",
        "0123456789",
    }
)
TOKEN_BYTES = 32


@dataclass(frozen=True, slots=True)
class ScryptParams:
    n: int = 2**15
    r: int = 8
    p: int = 1

    @property
    def maxmem(self) -> int:
        return 128 * self.n * self.r * 2 + 1024 * 1024


DEFAULT_SCRYPT = ScryptParams()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str, params: ScryptParams = DEFAULT_SCRYPT) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=params.n,
        r=params.r,
        p=params.p,
        maxmem=params.maxmem,
    )
    return f"scrypt${params.n}${params.r}${params.p}${_b64(salt)}${_b64(digest)}"


def verify_password(password: str, stored: str) -> bool:
    """Return True only for a matching password; malformed hashes never match."""
    try:
        scheme, n, r, p, salt, expected = stored.split("$")
        if scheme != "scrypt":
            return False
        params = ScryptParams(int(n), int(r), int(p))
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_unb64(salt),
            n=params.n,
            r=params.r,
            p=params.p,
            maxmem=params.maxmem,
        )
        return hmac.compare_digest(digest, _unb64(expected))
    except (ValueError, TypeError):
        return False


def password_problems(password: str, email: str = "") -> list[str]:
    """Return machine-readable reasons a password is unacceptable (empty = fine)."""
    problems: list[str] = []
    if len(password) < PASSWORD_MIN_LENGTH:
        problems.append("too_short")
    if len(password) > PASSWORD_MAX_LENGTH:
        problems.append("too_long")
    lowered = password.lower()
    if lowered in COMMON_PASSWORDS:
        problems.append("too_common")
    local_part = email.split("@", 1)[0].lower()
    if len(local_part) >= 3 and local_part in lowered:
        problems.append("contains_email")
    return problems


def new_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(email: str) -> str:
    return email.strip().lower()
