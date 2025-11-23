"""
Token encryption utilities for secure storage.

Uses Fernet symmetric encryption from the cryptography library.
Tokens are encrypted before storing in Firestore and decrypted when retrieved.
"""

import logging
import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

# Singleton encryption key instance
_fernet: Optional[Fernet] = None


class EncryptionError(Exception):
    """Raised when encryption/decryption fails."""

    pass


def _get_fernet() -> Fernet:
    """
    Get or create the Fernet encryption instance.

    The encryption key is read from TOKEN_ENCRYPTION_KEY environment variable.
    The key should be a 32-byte base64-encoded string (URL-safe).

    Returns:
        Fernet instance for encryption/decryption

    Raises:
        ValueError: If TOKEN_ENCRYPTION_KEY is not set or invalid
    """
    global _fernet

    if _fernet is not None:
        return _fernet

    key = os.getenv("TOKEN_ENCRYPTION_KEY")
    if not key:
        raise ValueError(
            "TOKEN_ENCRYPTION_KEY environment variable must be set for token encryption"
        )

    try:
        # Fernet key should be 32 bytes, base64-encoded (URL-safe)
        _fernet = Fernet(key.encode())
        logger.info("Token encryption initialized")
        return _fernet
    except Exception as e:
        raise ValueError(f"Invalid TOKEN_ENCRYPTION_KEY: {e}")


def encrypt_token(plaintext: str) -> str:
    """
    Encrypt a token string.

    Args:
        plaintext: The token value to encrypt

    Returns:
        Base64-encoded encrypted token

    Raises:
        EncryptionError: If encryption fails
    """
    try:
        fernet = _get_fernet()
        encrypted_bytes = fernet.encrypt(plaintext.encode())
        result: str = encrypted_bytes.decode()
        return result
    except ValueError:
        # Re-raise configuration errors
        raise
    except Exception as e:
        logger.error(f"Failed to encrypt token: {e}")
        raise EncryptionError(f"Encryption failed: {e}")


def decrypt_token(ciphertext: str) -> str:
    """
    Decrypt an encrypted token string.

    Args:
        ciphertext: Base64-encoded encrypted token

    Returns:
        Decrypted plaintext token

    Raises:
        EncryptionError: If decryption fails (invalid key or corrupted data)
    """
    try:
        fernet = _get_fernet()
        decrypted_bytes = fernet.decrypt(ciphertext.encode())
        result: str = decrypted_bytes.decode()
        return result
    except ValueError:
        # Re-raise configuration errors
        raise
    except InvalidToken:
        logger.error("Failed to decrypt token: invalid token or key")
        raise EncryptionError("Decryption failed: invalid token or key mismatch")
    except Exception as e:
        logger.error(f"Failed to decrypt token: {e}")
        raise EncryptionError(f"Decryption failed: {e}")


def encrypt_token_optional(plaintext: Optional[str]) -> Optional[str]:
    """
    Encrypt a token string if not None.

    Args:
        plaintext: The token value to encrypt, or None

    Returns:
        Base64-encoded encrypted token, or None if input was None
    """
    if plaintext is None:
        return None
    return encrypt_token(plaintext)


def decrypt_token_optional(ciphertext: Optional[str]) -> Optional[str]:
    """
    Decrypt an encrypted token string if not None.

    Args:
        ciphertext: Base64-encoded encrypted token, or None

    Returns:
        Decrypted plaintext token, or None if input was None
    """
    if ciphertext is None:
        return None
    return decrypt_token(ciphertext)


def generate_encryption_key() -> str:
    """
    Generate a new Fernet encryption key.

    This is a utility function for generating keys during setup.
    The generated key can be used as TOKEN_ENCRYPTION_KEY.

    Returns:
        URL-safe base64-encoded 32-byte key
    """
    key_bytes = Fernet.generate_key()
    result: str = key_bytes.decode()
    return result


def is_encryption_configured() -> bool:
    """
    Check if token encryption is configured.

    Returns:
        True if TOKEN_ENCRYPTION_KEY is set, False otherwise
    """
    return os.getenv("TOKEN_ENCRYPTION_KEY") is not None


def reset_encryption() -> None:
    """
    Reset the encryption singleton.

    Useful for testing to ensure clean state between tests.
    """
    global _fernet
    _fernet = None
