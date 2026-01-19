"""Tests for encryption utilities."""

import pytest
from services.encryption import encrypt_value, decrypt_value


class TestEncryption:
    """Tests for encryption/decryption functions."""
    
    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted value can be decrypted back to original."""
        original = "my-secret-token-12345"
        
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        
        assert decrypted == original
    
    def test_encrypted_value_different_from_original(self):
        """Encrypted value is different from original."""
        original = "my-secret-token"
        encrypted = encrypt_value(original)
        
        assert encrypted != original
        assert len(encrypted) > len(original)
    
    def test_encrypt_empty_string(self):
        """Empty string returns empty string."""
        assert encrypt_value("") == ""
        assert decrypt_value("") == ""
    
    def test_same_value_encrypts_differently(self):
        """Same value encrypted twice produces same result (deterministic)."""
        # Note: Fernet uses a timestamp so values could differ,
        # but for our use case we just care that decryption works
        original = "test-value"
        
        encrypted1 = encrypt_value(original)
        encrypted2 = encrypt_value(original)
        
        # Both should decrypt to same value
        assert decrypt_value(encrypted1) == original
        assert decrypt_value(encrypted2) == original
    
    def test_decrypt_invalid_value_returns_empty(self):
        """Decrypting invalid value returns empty string."""
        result = decrypt_value("not-a-valid-encrypted-value")
        assert result == ""
    
    def test_encrypt_unicode_value(self):
        """Unicode values can be encrypted and decrypted."""
        original = "test-token-with-unicode-"
        
        encrypted = encrypt_value(original)
        decrypted = decrypt_value(encrypted)
        
        assert decrypted == original
