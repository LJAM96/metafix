"""Encryption utilities for secure storage of API keys and tokens."""

import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from config import get_settings


def _get_encryption_key() -> bytes:
    """Derive encryption key from secret key."""
    settings = get_settings()
    secret = settings.secret_key.encode()
    
    # Use PBKDF2 to derive a proper Fernet key from the secret
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"metafix-salt-v1",  # Static salt for deterministic key derivation
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret))
    return key


def encrypt_value(value: str) -> str:
    """Encrypt a string value for storage."""
    if not value:
        return ""
    
    key = _get_encryption_key()
    f = Fernet(key)
    encrypted = f.encrypt(value.encode())
    return base64.urlsafe_b64encode(encrypted).decode()


def decrypt_value(encrypted_value: str) -> str:
    """Decrypt a stored encrypted value."""
    if not encrypted_value:
        return ""
    
    try:
        key = _get_encryption_key()
        f = Fernet(key)
        encrypted = base64.urlsafe_b64decode(encrypted_value.encode())
        decrypted = f.decrypt(encrypted)
        return decrypted.decode()
    except Exception:
        # Return empty string if decryption fails
        return ""
