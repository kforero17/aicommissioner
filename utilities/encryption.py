"""Encryption utilities for sensitive data."""
from typing import Optional
from cryptography.fernet import Fernet
from config import settings


class TokenEncryption:
    """Handles encryption and decryption of OAuth tokens."""

    def __init__(self):
        self._cipher = Fernet(settings.encryption_key.encode())

    def encrypt(self, token: str) -> str:
        """Encrypt a token for storage."""
        if not token:
            return ""
        return self._cipher.encrypt(token.encode()).decode()

    def decrypt(self, encrypted_token: str) -> str:
        """Decrypt a stored token."""
        if not encrypted_token:
            return ""
        return self._cipher.decrypt(encrypted_token.encode()).decode()

    def encrypt_optional(self, token: Optional[str]) -> Optional[str]:
        """Encrypt an optional token."""
        return self.encrypt(token) if token else None

    def decrypt_optional(self, encrypted_token: Optional[str]) -> Optional[str]:
        """Decrypt an optional token."""
        return self.decrypt(encrypted_token) if encrypted_token else None


token_encryption = TokenEncryption()
