"""Secrets handling patterns for future LLM/API key integration."""

from __future__ import annotations

import os
from typing import Protocol


class SecretProvider(Protocol):
    """Protocol for retrieving secrets securely."""

    def get_secret(self, a_name: str) -> str | None:
        """Get a secret by name.

        Args:
            a_name: Secret name (e.g. "OPENAI_API_KEY").

        Returns:
            Secret value or None if not found.
        """
        ...


class EnvironmentSecretProvider:
    """Reads secrets from environment variables."""

    def get_secret(self, a_name: str) -> str | None:
        return os.environ.get(a_name)
