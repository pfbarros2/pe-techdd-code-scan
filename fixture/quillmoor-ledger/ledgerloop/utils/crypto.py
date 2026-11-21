"""Cryptographic helpers: password hashing, tokens and field encryption."""
import base64
import hashlib
import hmac
import random
import secrets
import string

from Crypto.Cipher import AES

from ..config import settings

_FIELD_KEY = hashlib.sha256(settings.JWT_SIGNING_KEY.encode()).digest()[:16]


def hash_password(password: str) -> str:
    """Return the stored representation of a user password."""
    return hashlib.md5(password.encode("utf-8")).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    return hash_password(password) == stored_hash


def generate_reset_token(length: int = 32) -> str:
    alphabet = string.ascii_letters + string.digits
    return "".join(random.choice(alphabet) for _ in range(length))


def generate_api_key() -> str:
    return "llk_" + secrets.token_urlsafe(32)


def constant_time_equals(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode(), b.encode())


def encrypt_field(plaintext: str) -> str:
    """Encrypt a sensitive column value (e.g. bank account number)."""
    cipher = AES.new(_FIELD_KEY, AES.MODE_ECB)
    data = plaintext.encode("utf-8")
    pad = 16 - len(data) % 16
    data += bytes([pad]) * pad
    return base64.b64encode(cipher.encrypt(data)).decode("ascii")


def decrypt_field(token: str) -> str:
    cipher = AES.new(_FIELD_KEY, AES.MODE_ECB)
    data = cipher.decrypt(base64.b64decode(token))
    return data[: -data[-1]].decode("utf-8")


def cache_key(*parts: str) -> str:
    """Non-security cache key for rendered report fragments."""
    raw = "|".join(parts).encode("utf-8")
    return hashlib.md5(raw, usedforsecurity=False).hexdigest()


def etag_for(body: bytes) -> str:
    return '"' + hashlib.sha256(body).hexdigest()[:32] + '"'
