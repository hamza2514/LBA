"""
Sign-in: users live in Postgres, passwords are salted PBKDF2-SHA256 hashes
(never stored or logged in clear). The signed-in user is kept in the
Streamlit session.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets

import streamlit as st

import core.db as db

_ITERATIONS = 200_000
_SESSION_KEY = "auth_user"
ROLES = ("admin", "user")
MIN_PASSWORD_LENGTH = 8


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    return f"pbkdf2${_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt_hex, digest_hex = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(iterations))
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


def _clean(username: str) -> str:
    return username.strip().lower()


def validate_new_password(password: str, confirm: str) -> str | None:
    """Error message, or None when the password is acceptable."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password must be at least {MIN_PASSWORD_LENGTH} characters."
    if password != confirm:
        return "Passwords don't match."
    return None


def create_user(username: str, password: str, full_name: str = "", role: str = "user") -> None:
    if role not in ROLES:
        raise ValueError(f"Unknown role {role!r}")
    if not _clean(username):
        raise ValueError("Username is required.")
    db.save_user(_clean(username), hash_password(password), full_name.strip(), role)


def authenticate(username: str, password: str) -> dict | None:
    user = db.get_user(_clean(username))
    if user and verify_password(password, user["password_hash"]):
        return {k: user[k] for k in ("username", "full_name", "role")}
    return None


def needs_setup() -> bool:
    """True until the first (administrator) account exists."""
    return db.count_users() == 0


def current_user() -> dict | None:
    return st.session_state.get(_SESSION_KEY)


def sign_in(user: dict) -> None:
    st.session_state[_SESSION_KEY] = user


def sign_out() -> None:
    st.session_state.clear()
