"""Tests for domain shared secrets module."""

from __future__ import annotations

import os
from typing import Protocol

from arian.domain.shared.secrets import EnvironmentSecretProvider
from arian.domain.shared.secrets import SecretProvider


def test_secret_provider_is_protocol() -> None:
    """Test SecretProvider is a Protocol."""
    assert issubclass(SecretProvider, Protocol)


def test_secret_provider_structural_subtyping() -> None:
    """Test a concrete class satisfies SecretProvider via structural subtyping."""

    class Vault:
        """Stub vault."""

        def __init__(self) -> None:
            self.data: dict[str, str] = {"MY_KEY": "secret_value"}

        def get_secret(self, a_name: str) -> str | None:
            return self.data.get(a_name)

    provider: SecretProvider = Vault()
    assert provider.get_secret("MY_KEY") == "secret_value"
    assert provider.get_secret("MISSING") is None


def test_environment_secret_provider_returns_env_value() -> None:
    """Test EnvironmentSecretProvider reads from environment."""
    provider = EnvironmentSecretProvider()

    os.environ["ARIAN_TEST_SECRET_KEY"] = "test_value_123"
    try:
        result = provider.get_secret("ARIAN_TEST_SECRET_KEY")
        assert result == "test_value_123"
    finally:
        del os.environ["ARIAN_TEST_SECRET_KEY"]


def test_environment_secret_provider_returns_none_for_missing() -> None:
    """Test EnvironmentSecretProvider returns None for missing keys."""
    provider = EnvironmentSecretProvider()
    result = provider.get_secret("NONEXISTENT_KEY_98765")
    assert result is None


def test_environment_secret_provider_satisfies_protocol() -> None:
    """Test EnvironmentSecretProvider satisfies SecretProvider protocol."""
    provider: SecretProvider = EnvironmentSecretProvider()
    assert provider.get_secret("PATH") is not None
