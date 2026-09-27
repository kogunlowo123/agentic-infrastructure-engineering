"""Input validation and screening for agent requests."""

import re
import logging
from typing import Any

logger = logging.getLogger(__name__)

INJECTION_PATTERNS = [
    re.compile(r"ignore previous instructions", re.IGNORECASE),
    re.compile(r"you are now", re.IGNORECASE),
    re.compile(r"disregard (all|your|the) (instructions|rules|guidelines)", re.IGNORECASE),
    re.compile(r"system prompt", re.IGNORECASE),
]


class InputScreener:
    """Validates agent inputs against policy and detects injection attempts."""

    def screen(self, input_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Screen input for policy violations and injection attacks.

        Returns:
            (is_valid, rejection_reason)
        """
        text_fields = self._extract_text_fields(input_data)

        for text in text_fields:
            for pattern in INJECTION_PATTERNS:
                if pattern.search(text):
                    logger.warning("Injection attempt detected: %s", text[:100])
                    return False, "Input contains prohibited patterns"

        return True, None

    def _extract_text_fields(self, data: Any, max_depth: int = 5) -> list[str]:
        """Recursively extract string values from nested dicts."""
        texts: list[str] = []
        if max_depth <= 0:
            return texts
        if isinstance(data, str):
            texts.append(data)
        elif isinstance(data, dict):
            for v in data.values():
                texts.extend(self._extract_text_fields(v, max_depth - 1))
        elif isinstance(data, list):
            for item in data:
                texts.extend(self._extract_text_fields(item, max_depth - 1))
        return texts
