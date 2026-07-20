"""Domain constants for resource limits and safeguards."""

from __future__ import annotations

MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10MB max output file
MAX_COLLECTED_FILES: int = 10_000  # Max files to collect
MAX_TOKEN_BUDGET: int = 1_000_000  # Max token budget
DEFAULT_MAX_CONCURRENT_LOADS: int = 10  # Bounded concurrency for file reads
