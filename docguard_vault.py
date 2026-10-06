import base64
import hashlib
import tempfile
from pathlib import Path
from cryptography.fernet import Fernet
import docguard_security as security

BASE_DIR = Path(__file__).resolve().parent
VAULT_DIR = BASE_DIR / "vault"
VAULT_DIR.mkdir(parents=True, exist_ok=True)
_active_key = None


def _derive_key(pin):
    salt = security.get_salt()
    if not salt:
        raise ValueError("Security account is not configured.")
    material = hashlib.pbkdf2_hmac("sha256", pin.encode("utf-8"), salt.encode("utf-8"), 200000, dklen=32)
    return base64.urlsafe_b64encode(material)


def initialize_key(pin):
    global _active_key
    _active_key = _derive_key(pin)
    return True


def is_initialized():
    return _active_key is not None


def store_file(source):
    if _active_key is None:
        raise RuntimeError("Vault is locked. Please login first.")
    source_path = Path(source)
    if not source_path.exists():
        raise FileNotFoundError("Selected file does not exist.")
    encrypted_filename = source_path.name + ".encrypted"
    destination = VAULT_DIR / encrypted_filename
    cipher = Fernet(_active_key)
    with open(source_path, "rb") as file:
        original_data = file.read()
    with open(destination, "wb") as file:
        file.write(cipher.encrypt(original_data))
    return str(destination)


def restore_to_temp(stored_path, original_name):
    if _active_key is None:
        raise RuntimeError("Vault is locked.")
    stored_file = Path(stored_path)
    if not stored_file.exists():
        raise FileNotFoundError("Encrypted document not found.")
    cipher = Fernet(_active_key)
    with open(stored_file, "rb") as file:
        encrypted_data = file.read()
    decrypted_data = cipher.decrypt(encrypted_data)
    temp_directory = Path(tempfile.mkdtemp(prefix="docguard_"))
    output_file = temp_directory / original_name
    with open(output_file, "wb") as file:
        file.write(decrypted_data)
    return str(output_file)


def delete_file(stored_path):
    file_path = Path(stored_path)
    if not file_path.exists():
        return False
    try:
        file_path.unlink()
        return True
    except Exception:
        return False


def clear_key():
    global _active_key
    _active_key = None


def file_exists(stored_path):
    return Path(stored_path).exists()


def get_vault_directory():
    return VAULT_DIR
