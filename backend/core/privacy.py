import re
import base64
import os
import logging
import hashlib
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime, timedelta, UTC
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend

logger = logging.getLogger(__name__)

class DataClassification(str, Enum):
    """Classification levels for data sensitivity."""
    PUBLIC = "public"
    PERSONAL = "personal"
    SENSITIVE = "sensitive"
    RESTRICTED = "restricted"

class PrivacyService:
    """
    Privacy service for data encryption, classification, and PII redaction.
    Consolidates encryption patterns from v2 and compliance patterns from v3.
    """

    def __init__(self, secret_key: str, salt: str, redaction_level: str = "partial"):
        self.redaction_level = redaction_level
        self.key = self._derive_key(secret_key, salt)
        self.aesgcm = AESGCM(self.key)

        # Unified Regex patterns from JARVISv2/v3
        self.patterns = {
            DataClassification.SENSITIVE: [
                r'\b\d{3}-\d{2}-\d{4}\b',  # US SSN
                r'\b(?:\d{4}[ -]?){3}\d{4}\b',  # Credit card (generic 16-digit)
                r'\b[A-Z]{2}[0-9A-Z]{2}[0-9A-Z]{1,30}\b',  # IBAN
            ],
            DataClassification.PERSONAL: [
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b',  # Email
                # Phone numbers - specific patterns to avoid CC fragments
                r'(?<!\d)\d{3}-\d{3}-\d{4}(?!\d)', # 10-digit
                r'(?<!\d)\(\d{3}\)\s\d{3}-\d{4}(?!\d)', # 10-digit (brackets)
                r'(?<!\d)\d{3}-\d{4}(?!\d)', # 7-digit
                r'\b\d{9,19}\b',  # Bank acct
                r'\b(?:\d{1,3}\.){3}\d{1,3}\b',  # IPv4
            ]
        }

        self.sensitive_keywords = [
            "password", "social security", "medical record", "financial",
            "ssn", "credit card", "bank account", "tax id", "national insurance",
            "sensitive", "restricted", "confidential"
        ]

        self.personal_keywords = [
            "name", "address", "phone", "email", "birthday", "birth date",
            "passport", "driver's license", "national id", "personal", "pii"
        ]

        # GDPR/CCPA compliance settings (from v3)
        self.data_retention_policies = {
            DataClassification.PUBLIC: timedelta(days=365),
            DataClassification.PERSONAL: timedelta(days=180),
            DataClassification.SENSITIVE: timedelta(days=90),
            DataClassification.RESTRICTED: timedelta(days=30)
        }

    def _derive_key(self, password: str, salt: str) -> bytes:
        """Derive a 32-byte encryption key using PBKDF2."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt.encode(),
            iterations=100000,
            backend=default_backend()
        )
        return kdf.derive(password.encode())

    def encrypt(self, data: str) -> str:
        """
        Encrypt data using AES-GCM.
        Returns base64(nonce + ciphertext + tag).
        """
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, data.encode('utf-8'), None)
        return base64.b64encode(nonce + ciphertext).decode('utf-8')

    def decrypt(self, encrypted_data: str) -> str:
        """Decrypt data encrypted via the encrypt method."""
        encrypted_bytes = base64.b64decode(encrypted_data)
        nonce = encrypted_bytes[:12]
        ciphertext = encrypted_bytes[12:]
        plaintext = self.aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')

    def classify(self, content: str) -> DataClassification:
        """Classify data based on sensitivity patterns and keywords."""
        content_lower = content.lower()

        for classification, pattern_list in self.patterns.items():
            for pattern in pattern_list:
                if re.search(pattern, content):
                    return classification

        for keyword in self.sensitive_keywords:
            if keyword in content_lower:
                return DataClassification.SENSITIVE

        for keyword in self.personal_keywords:
            if keyword in content_lower:
                return DataClassification.PERSONAL

        return DataClassification.PUBLIC

    def redact(self, content: str) -> str:
        """Redact sensitive information from content based on redaction_level."""
        if self.redaction_level == "none":
            return content

        # 1. Emails
        content = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', '[EMAIL_REDACTED]', content)
        
        # 2. Strict patterns (run before generic digits)
        if self.redaction_level == "strict":
            content = re.sub(r'\b(?:\d{4}[ -]?){3}\d{4}\b', '[CREDIT_CARD_REDACTED]', content)
            content = re.sub(r'\b\d{3}-\d{2}-\d{4}\b', '[SSN_REDACTED]', content)
            content = re.sub(r'\b[A-Z]{2}[0-9A-Z]{2}[0-9A-Z]{1,30}\b', '[IBAN_REDACTED]', content)
            content = re.sub(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', '[IP_REDACTED]', content)

        # 3. Phone numbers (Specific patterns to avoid false positives with CCs)
        content = re.sub(r'(?<!\d)\d{3}-\d{3}-\d{4}(?!\d)', '[PHONE_REDACTED]', content)
        content = re.sub(r'(?<!\d)\(\d{3}\)\s\d{3}-\d{4}(?!\d)', '[PHONE_REDACTED]', content)
        content = re.sub(r'(?<!\d)\d{3}-\d{4}(?!\d)', '[PHONE_REDACTED]', content)

        return content

    def create_audit_log(self, action: str, data_type: str, user_id: str) -> Dict[str, Any]:
        """Create a privacy audit log entry for compliance tracking."""
        return {
            "timestamp": datetime.now(UTC).isoformat(),
            "action": action,
            "data_type": data_type,
            "user_id": user_id,
            "compliance": "GDPR/CCPA/ECF",
            "status": "compliant"
        }

    def should_process_locally(self, content: str) -> bool:
        """Determine if data should be processed locally."""
        classification = self.classify(content)
        if self.redaction_level == "strict":
            return classification != DataClassification.PUBLIC
        return classification in [DataClassification.SENSITIVE, DataClassification.RESTRICTED]

    def hash_id(self, value: str) -> str:
        """Generate a deterministic hash for a value (e.g. user ID) to preserve privacy."""
        return hashlib.sha256(value.encode()).hexdigest()
