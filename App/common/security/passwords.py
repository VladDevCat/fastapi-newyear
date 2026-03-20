import secrets

import bcrypt


def hash_password(password: str) -> tuple[str, str]:
    salt = secrets.token_hex(16)
    combined = f"{password}{salt}".encode("utf-8")
    password_hash = bcrypt.hashpw(combined, bcrypt.gensalt()).decode("utf-8")
    return password_hash, salt


def verify_password(password: str, salt: str, password_hash: str) -> bool:
    combined = f"{password}{salt}".encode("utf-8")
    return bcrypt.checkpw(combined, password_hash.encode("utf-8"))