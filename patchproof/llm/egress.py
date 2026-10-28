"""Egress protection: secret scanning, sensitive path denial, and prompt preview."""

import re
from pathlib import Path


class EgressSecurityViolation(Exception):
    """Raised when context contains forbidden unredacted secrets or credentials."""
    pass


class EgressGate:
    """Sanitizes prompts and outbound context payloads before dispatching to LLM APIs."""

    SECRET_PATTERNS = [
        (r"AKIA[0-9A-Z]{16}", "[REDACTED_AWS_KEY]"),
        (r"ghp_[0-9a-zA-Z]{36}", "[REDACTED_GITHUB_PAT]"),
        (r"bearer\s+[A-Za-z0-9\-_\.]+", "Bearer [REDACTED_TOKEN]"),
        (r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", "[REDACTED_PRIVATE_KEY]"),
    ]

    DENIED_PATH_PATTERNS = [
        re.compile(r"\.env(\.[a-zA-Z0-9]+)?$"),
        re.compile(r".*credentials.*"),
        re.compile(r".*id_rsa.*"),
    ]

    @classmethod
    def sanitize_text(cls, text: str) -> str:
        """Scan and redact known secrets from prompt text."""
        sanitized = text
        for pattern, replacement in cls.SECRET_PATTERNS:
            sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
        return sanitized

    @classmethod
    def check_file_path(cls, file_path: str | Path) -> None:
        """Ensure file is not on the sensitive file denylist."""
        path_str = str(file_path).lower()
        for pat in cls.DENIED_PATH_PATTERNS:
            if pat.search(path_str):
                raise EgressSecurityViolation(
                    f"Attempted to send sensitive file to LLM context: {file_path}"
                )
