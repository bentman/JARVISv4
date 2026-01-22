import pytest
from backend.core.privacy import PrivacyService, DataClassification

def test_privacy_encryption_roundtrip():
    service = PrivacyService(secret_key="test-key", salt="test-salt")
    original_text = "Sensitive data 123"
    
    encrypted = service.encrypt(original_text)
    assert encrypted != original_text
    
    decrypted = service.decrypt(encrypted)
    assert decrypted == original_text

def test_privacy_classification():
    service = PrivacyService(secret_key="test-key", salt="test-salt")
    
    assert service.classify("Just some text") == DataClassification.PUBLIC
    assert service.classify("My email is test@example.com") == DataClassification.PERSONAL
    assert service.classify("My SSN is 123-45-6789") == DataClassification.SENSITIVE
    assert service.classify("This is a confidential medical record") == DataClassification.SENSITIVE

def test_privacy_redaction_partial():
    service = PrivacyService(secret_key="test-key", salt="test-salt", redaction_level="partial")
    text = "Contact me at 555-0199 or test@example.com. Card: 1234-5678-9012-3456"
    
    redacted = service.redact(text)
    assert "[EMAIL_REDACTED]" in redacted
    assert "[PHONE_REDACTED]" in redacted
    assert "1234-5678-9012-3456" in redacted  # CC not redacted in partial

def test_privacy_redaction_strict():
    service = PrivacyService(secret_key="test-key", salt="test-salt", redaction_level="strict")
    text = "Contact me at 555-0199 or test@example.com. Card: 1234-5678-9012-3456"
    
    redacted = service.redact(text)
    assert "[EMAIL_REDACTED]" in redacted
    assert "[PHONE_REDACTED]" in redacted
    assert "[CREDIT_CARD_REDACTED]" in redacted

def test_privacy_audit_log():
    service = PrivacyService(secret_key="test-key", salt="test-salt")
    log = service.create_audit_log("access", "personal", "user_123")
    
    assert log["action"] == "access"
    assert log["data_type"] == "personal"
    assert log["user_id"] == "user_123"
    assert "timestamp" in log
    assert log["compliance"] == "GDPR/CCPA/ECF"

def test_privacy_hash_id():
    service = PrivacyService(secret_key="test-key", salt="test-salt")
    user_id = "user_123"
    h1 = service.hash_id(user_id)
    h2 = service.hash_id(user_id)
    
    assert h1 == h2
    assert h1 != user_id
    assert len(h1) == 64  # SHA256 hex length
