"""Secure user credential storage with strict filesystem permission guards (0600)."""

import json
import os
import stat
from pathlib import Path
from typing import Any


class CredentialStore:
    """Manages persistent credentials in user home config with 0600 security invariants."""

    DEFAULT_DIR = Path.home() / ".config" / "patchproof"
    CREDENTIALS_FILE = DEFAULT_DIR / "credentials.json"

    SUPPORTED_KEYS = {
        "anthropic": "ANTHROPIC_API_KEY",
        "gemini": "GEMINI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "deepseek": "DEEPSEEK_API_KEY",
        "github": "GITHUB_TOKEN",
    }

    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path or self.CREDENTIALS_FILE

    def _ensure_secure_dir(self) -> None:
        """Create config directory with 0700 permissions (user only)."""
        parent = self.file_path.parent
        if not parent.exists():
            parent.mkdir(parents=True, exist_ok=True)
            try:
                os.chmod(parent, stat.S_IRWXU)  # 0700
            except OSError:
                pass

    def load_credentials(self) -> dict[str, str]:
        """Read credentials from disk."""
        if not self.file_path.is_file():
            return {}

        try:
            raw = self.file_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            if isinstance(data, dict):
                return {str(k): str(v) for k, v in data.items()}
            return {}
        except Exception:
            return {}

    def save_credentials(self, credentials: dict[str, str]) -> None:
        """Save credentials to disk with strict 0600 (owner-only read/write) permissions."""
        self._ensure_secure_dir()

        payload = json.dumps(credentials, indent=2)
        self.file_path.write_text(payload, encoding="utf-8")
        try:
            # Enforce 0600: rw-------
            os.chmod(self.file_path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    def set_key(self, provider: str, key_value: str) -> None:
        """Store or update an API key for a designated provider."""
        provider_norm = provider.lower().strip()
        creds = self.load_credentials()
        creds[provider_norm] = key_value.strip()
        self.save_credentials(creds)

    def get_key(self, provider: str) -> str | None:
        """Retrieve key for provider, checking environment first, then credential store."""
        provider_norm = provider.lower().strip()
        env_var = self.SUPPORTED_KEYS.get(provider_norm)

        # 1. Check environment variables
        if env_var:
            env_val = os.environ.get(f"PATCHPROOF_{env_var}") or os.environ.get(env_var)
            if env_val:
                return env_val

        # 2. Check local credentials store
        creds = self.load_credentials()
        return creds.get(provider_norm)

    def delete_key(self, provider: str) -> bool:
        """Remove a key from the credentials store."""
        provider_norm = provider.lower().strip()
        creds = self.load_credentials()
        if provider_norm in creds:
            del creds[provider_norm]
            self.save_credentials(creds)
            return True
        return False

    def get_status(self) -> dict[str, dict[str, Any]]:
        """Return masked status and source of all supported credentials."""
        creds = self.load_credentials()
        status: dict[str, dict[str, Any]] = {}

        for provider, env_var in self.SUPPORTED_KEYS.items():
            env_val = os.environ.get(f"PATCHPROOF_{env_var}") or os.environ.get(env_var)
            store_val = creds.get(provider)

            if env_val:
                source = "environment"
                masked = self.mask_key(env_val)
                active = True
            elif store_val:
                source = "credentials.json"
                masked = self.mask_key(store_val)
                active = True
            else:
                source = "missing"
                masked = "Not set"
                active = False

            status[provider] = {
                "active": active,
                "source": source,
                "masked": masked,
                "env_var": env_var,
            }

        return status

    @staticmethod
    def mask_key(key: str) -> str:
        """Return safe masked representation (e.g., sk-ant-...4a9e)."""
        if not key:
            return ""
        if len(key) <= 8:
            return "****"
        return f"{key[:6]}...{key[-4:]}"
