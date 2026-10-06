import hashlib
import json
import secrets
import uuid
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)
ACCOUNTS_FILE = CONFIG_DIR / "accounts.json"
LEGACY_ACCOUNT_FILE = CONFIG_DIR / "account.json"
_current_user_id = None


def hash_pin(pin, salt):
    return hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode("utf-8"), 120000).hex()


def _load_accounts():
    if not ACCOUNTS_FILE.exists():
        return []
    try:
        with open(ACCOUNTS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _save_accounts(accounts):
    with open(ACCOUNTS_FILE, "w", encoding="utf-8") as file:
        json.dump(accounts, file, indent=4)


def _migrate_legacy_account():
    if ACCOUNTS_FILE.exists() or not LEGACY_ACCOUNT_FILE.exists():
        return
    try:
        with open(LEGACY_ACCOUNT_FILE, "r", encoding="utf-8") as file:
            old = json.load(file)
        if old.get("username") and old.get("pin_hash") and old.get("salt"):
            account = {
                "user_id": uuid.uuid4().hex,
                "full_name": old.get("full_name", old.get("name", "User")),
                "username": old["username"],
                "salt": old["salt"],
                "pin_hash": old["pin_hash"]
            }
            _save_accounts([account])
    except Exception:
        pass


def has_account():
    _migrate_legacy_account()
    return len(_load_accounts()) > 0


def create_account(full_name, username, pin):
    _migrate_legacy_account()
    accounts = _load_accounts()
    if any(a.get("username", "").lower() == username.lower() for a in accounts):
        raise ValueError("That username already exists.")
    salt = secrets.token_hex(16)
    account = {
        "user_id": uuid.uuid4().hex,
        "full_name": full_name,
        "username": username,
        "salt": salt,
        "pin_hash": hash_pin(pin, salt)
    }
    accounts.append(account)
    _save_accounts(accounts)
    global _current_user_id
    _current_user_id = account["user_id"]
    return account["user_id"]


def authenticate(username, pin):
    _migrate_legacy_account()
    global _current_user_id
    for account in _load_accounts():
        if account.get("username") != username:
            continue
        salt = account.get("salt")
        stored_hash = account.get("pin_hash")
        if salt and stored_hash and secrets.compare_digest(hash_pin(pin, salt), stored_hash):
            _current_user_id = account.get("user_id")
            return True
        return False
    return False


def load_account():
    _migrate_legacy_account()
    for account in _load_accounts():
        if account.get("user_id") == _current_user_id:
            return account
    return None


def profile():
    account = load_account()
    if not account:
        return None
    return {
        "user_id": account.get("user_id"),
        "full_name": account.get("full_name", ""),
        "name": account.get("full_name", ""),
        "username": account.get("username", "")
    }


def get_name():
    account = load_account()
    return account.get("full_name", "") if account else ""


def get_username():
    account = load_account()
    return account.get("username", "") if account else ""


def get_salt():
    account = load_account()
    return account.get("salt") if account else None


def get_current_user_id():
    return _current_user_id


def logout():
    global _current_user_id
    _current_user_id = None


def is_configured():
    return has_account()


def reset():
    if ACCOUNTS_FILE.exists():
        ACCOUNTS_FILE.unlink()
    if LEGACY_ACCOUNT_FILE.exists():
        LEGACY_ACCOUNT_FILE.unlink()
    logout()
