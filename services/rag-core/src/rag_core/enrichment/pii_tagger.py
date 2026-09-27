"""PII detection tagger for document chunks."""

import re


PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "ipv4": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "ipv6": re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"),
    "api_key": re.compile(r"(?i)(?:api[_-]?key|secret[_-]?key|access[_-]?token)\s*[=:]\s*\S+"),
    "gcp_service_account_key": re.compile(r'"private_key"\s*:\s*"-----BEGIN'),
}


class PIITagger:
    """Detects PII patterns in document content and adds tags."""

    def tag(self, content: str, metadata: dict) -> dict:
        """Scan content for PII and update metadata with findings.

        Args:
            content: Text content to scan.
            metadata: Existing metadata dict to update.

        Returns:
            Updated metadata with pii_types and contains_pii fields.
        """
        found_types: list[str] = []

        for pii_type, pattern in PII_PATTERNS.items():
            if pattern.search(content):
                found_types.append(pii_type)

        metadata["pii_types"] = found_types
        metadata["contains_pii"] = len(found_types) > 0

        return metadata
