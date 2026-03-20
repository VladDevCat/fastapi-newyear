import hashlib
import secrets


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_random_token(length: int = 48) -> str:
    return secrets.token_urlsafe(length)


def generate_state() -> str:
    return secrets.token_urlsafe(32)