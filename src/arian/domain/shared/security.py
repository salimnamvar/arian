"""Security utilities for path validation and content safety.

Provides SafePath value object and validation helpers that enforce
security constraints at the domain boundary.

This module exposes pure functions that take their configuration
explicitly via parameters. Path-length limits, secret-redaction
patterns, and other tunables live in
:class:`arian.infrastructure.config.SecurityConfig` — no
module-level values are permitted here per the safe-coding policy.
"""

from __future__ import annotations

from pathlib import Path

from arian.infrastructure.config import SecurityConfig


class SafePath:
    """Validated filesystem path confined to a root directory.

    Created via validate_input_path — never instantiate directly.

    Attributes:
        resolved: The resolved absolute path.
        root: The root directory this path is confined to.
    """

    def __init__(self, a_resolved: Path, a_root: Path) -> None:
        self.resolved: Path = a_resolved
        self.root: Path = a_root

    def __str__(self) -> str:
        return str(self.resolved)

    def __repr__(self) -> str:
        return f"SafePath({self.resolved!r}, root={self.root!r})"

    def relative_to_root(self) -> Path:
        """Return path relative to the root directory.

        Returns:
            Relative path from root.
        """
        return self.resolved.relative_to(self.root)


class ValidatePathResult:
    """Result of path validation.

    Attributes:
        is_success: Whether validation passed.
        value: SafePath if successful, None otherwise.
        message: Error message if validation failed.
    """

    def __init__(
        self,
        *,
        a_is_success: bool,
        a_value: SafePath | None = None,
        a_message: str = "",
    ) -> None:
        self.is_success: bool = a_is_success
        self.value: SafePath | None = a_value
        self.message: str = a_message

    @staticmethod
    def success(a_value: SafePath) -> ValidatePathResult:
        return ValidatePathResult(a_is_success=True, a_value=a_value)

    @staticmethod
    def failure(a_message: str) -> ValidatePathResult:
        return ValidatePathResult(a_is_success=False, a_message=a_message)


def validate_input_path(
    a_path: Path,
    a_root: Path,
    a_config: SecurityConfig,
) -> ValidatePathResult:
    """Validate and resolve a path within a root directory.

    Checks:
        - No ``..`` path components (path traversal).
        - No symlink loops (resolve and verify).
        - Path is within the given root.
        - Path length does not exceed ``a_config.max_path_length``.

    Args:
        a_path: Raw input path to validate.
        a_root: Root directory the path must be within.
        a_config: Security configuration.

    Returns:
        ValidatePathResult with is_success, value (SafePath), and message.
    """
    raw: str = str(a_path)
    result: ValidatePathResult = ValidatePathResult.failure("uninitialized")
    resolved_root: Path = a_root.resolve()
    resolved: Path = a_path
    b_continue: bool = True

    if len(raw) > a_config.max_path_length:
        msg = f"Path exceeds maximum length ({a_config.max_path_length}): {len(raw)}"
        result = ValidatePathResult.failure(msg)
        b_continue = False

    if b_continue:
        parts: tuple[str, ...] = a_path.parts
        if ".." in parts:
            msg = f"Path traversal detected: {raw}"
            result = ValidatePathResult.failure(msg)
            b_continue = False

    if b_continue:
        try:
            resolved = a_path.resolve()
        except OSError:
            msg = f"Cannot resolve path (possible symlink loop): {raw}"
            result = ValidatePathResult.failure(msg)
            b_continue = False

    if b_continue:
        try:
            resolved.relative_to(resolved_root)
        except ValueError:
            msg = f"Path escapes root directory: {raw}"
            result = ValidatePathResult.failure(msg)
            b_continue = False

    if b_continue:
        result = ValidatePathResult.success(SafePath(a_resolved=resolved, a_root=resolved_root))

    return result


def is_binary(a_content: bytes) -> bool:
    """Check if content is binary by looking for null bytes in the first 8KB.

    Args:
        a_content: Raw file content bytes.

    Returns:
        True if content appears to be binary.
    """
    chunk: bytes = a_content[:8192]
    return b"\x00" in chunk


def redact_secrets(a_text: str, a_config: SecurityConfig) -> str:
    """Mask API keys, tokens, and passwords in text output.

    Applies every regex in ``a_config.secret_patterns`` to the input
    and replaces the matched substrings with ``a_config.redacted``.

    Args:
        a_text: Text that may contain secrets.
        a_config: Security configuration.

    Returns:
        Text with secrets redacted.
    """
    result: str = a_text
    for pattern in a_config.secret_patterns:
        result = pattern.sub(a_config.redacted, result)
    return result


def sanitize_error_message(a_message: str, a_root: str | None = None) -> str:
    """Sanitize error messages to avoid leaking internal paths.

    Args:
        a_message: Raw error message.
        a_root: Repository root to mask.

    Returns:
        Sanitized message.
    """
    message: str = a_message.replace(a_root, "<repository>") if a_root else a_message
    return message
