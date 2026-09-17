"""
Local authentication module for PULSE90.
Lightweight password hashing with PBKDF2-HMAC-SHA256 and salt.
"""

from __future__ import annotations

import hashlib
import json
import os
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,24}$")


def _ensure_data_dir() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)


def _load_users() -> dict:
    _ensure_data_dir()
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save_users(users: dict) -> None:
    _ensure_data_dir()
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)


def _hash_password(password: str, salt: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 200_000).hex()


def sign_up(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    if not USERNAME_RE.match(username):
        return False, "Usernames must be 3–24 characters: letters, numbers, or underscore."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."

    users = _load_users()
    if username.lower() in {u.lower() for u in users}:
        return False, "That username is already taken."

    salt = os.urandom(16)
    users[username] = {"salt": salt.hex(), "hash": _hash_password(password, salt)}
    _save_users(users)
    return True, "Account created successfully."


def sign_in(username: str, password: str) -> tuple[bool, str]:
    username = username.strip()
    users = _load_users()
    record = users.get(username)
    if record is None:
        return False, "No account with that username. Try creating one."

    salt = bytes.fromhex(record["salt"])
    if _hash_password(password, salt) != record["hash"]:
        return False, "Incorrect password."

    return True, "Signed in successfully."
