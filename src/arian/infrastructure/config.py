"""Application configuration — single source of truth for all tunables.

Every magic number, regular expression, frozenset, classification
table, retry policy, and other configuration value used by Arian
lives here as a Pydantic field. Module-level values in
implementation files are prohibited by safe-coding policy (NASA /
IBM: constants in well-defined locations, not scattered). Each
service receives its slice via constructor injection at the
composition root.

CSR architecture (Configuration / Service / Repository):

    LoggingConfig         — log transport
    FileCollectorConfig   — repository scan filters
    DomainLimitsConfig    — domain-wide numeric limits
    LanguageConfig        — file-language lookup tables
    SecurityConfig        — path / secret redaction rules
    BootstrapConfig       — bootstrap-layer constants
    RepositoryConfig      — repository schema and config
    RendererConfig        — markdown template location
    ControllerConfig      — CLI input validation tables
    RetryConfig           — file-read retry policy (builder)
    AnalyzerConfig        — Python source patterns (analyzer)
    ClassifierConfig      — file-role lookup tables (classifier)
    MaterializerConfig    — fragment merging threshold (materializer)
    PlannerConfig         — role ordering and task boosts (planner)
"""

from __future__ import annotations

import os
from pathlib import Path
from re import Pattern
from re import compile
from typing import Any

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import field_validator
from pydantic import model_validator

from arian.domain.shared.enums import CompressionLevel
from arian.domain.shared.enums import ContextTask
from arian.domain.shared.enums import FileRole


def is_truthy(a_value: str | None, a_truthy_values: frozenset[str]) -> bool:
    """Return True if ``a_value`` is a recognized truthy string.

    Args:
        a_value: Raw environment variable value (or None).
        a_truthy_values: Set of strings recognized as boolean true.

    Returns:
        True for ``"1"``, ``"true"``, ``"yes"``, ``"on"`` (any case).
    """
    return a_value in a_truthy_values if a_value is not None else False


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------


class LoggingConfig(BaseModel):
    """Logging configuration — level, transport, and file output.

    Attributes:
        level: Application logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        async_logging: Enable async logging via QueueHandler → QueueListener.
        log_dir: Directory for log files. None disables file logging.
        max_bytes: Maximum log file size in bytes before rotation.
        backup_count: Number of rotated log files to keep.
        valid_levels: Complete set of stdlib logging level names.
        propagating_loggers: Logger names that propagate to the root handler.
        module: Module name used when configuring the application logger.
        app_logger_name: Name of the application logger.
    """

    model_config = ConfigDict(frozen=True)

    level: str = Field(default="INFO", description="Application logging level.")
    async_logging: bool = Field(default=False, description="Enable async logging via queue.")
    log_dir: Path | None = Field(
        default=Path("~/.arian/logs"),
        description="Directory for log files. None disables file logging.",
    )
    max_bytes: int = Field(default=10 * 1024 * 1024, description="Max log file size before rotation (bytes).")
    backup_count: int = Field(default=5, description="Number of rotated log files to keep.")
    valid_levels: frozenset[str] = Field(
        default_factory=lambda: frozenset({"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}),
        description="Set of stdlib logging level names accepted by the validator.",
    )
    propagating_loggers: tuple[str, ...] = Field(
        default_factory=lambda: ("arian",),
        description="Logger name prefixes that propagate to the root handler.",
    )
    module: str = Field(
        default="arian.bootstrap.logging",
        description="Module name used when configuring the application logger.",
    )
    app_logger_name: str = Field(
        default="arian",
        description="Name of the application logger.",
    )

    @field_validator("level", mode="before")
    @classmethod
    def _normalize_level(cls, a_value: object) -> object:
        """Reject non-string levels and normalize case to uppercase.

        Args:
            a_value: Raw level value from constructor, dict, or env.

        Returns:
            Uppercased level string.

        Raises:
            TypeError: If the level is not a string.
        """
        if not isinstance(a_value, str):
            msg = "Logging level must be a string"
            raise TypeError(msg)
        return a_value.upper()

    @model_validator(mode="after")
    def _validate_level_name(self) -> LoggingConfig:
        """Ensure the normalized level is a recognized logging level.

        Returns:
            The validated config instance.

        Raises:
            ValueError: If the level is not in ``valid_levels``.
        """
        if self.level not in self.valid_levels:
            msg = f"Invalid logging level: {self.level}"
            raise ValueError(msg)
        return self


# ---------------------------------------------------------------------------
# Repository (file collection)
# ---------------------------------------------------------------------------


class FileCollectorConfig(BaseModel):
    """File collector configuration — extensions and exclusions.

    Attributes:
        extensions: File extensions to include. None means all text files.
            A frozenset acts as a narrowing filter (only these extensions).
        max_file_size: Maximum file size in bytes. Files exceeding this are skipped.
        exclude: Directory names to exclude from scanning.
        use_gitignore: When False, ``.gitignore`` rules are ignored.
            The ``exclude`` set still applies.
        nested_gitignore: When True, ``.gitignore`` files in ancestor
            directories of the scan root are also honored.
    """

    model_config = ConfigDict(frozen=True)

    extensions: frozenset[str] | None = Field(
        default=None,
        description="File extensions to include. None = all text files.",
    )
    max_file_size: int = Field(
        default=10 * 1024 * 1024,
        description="Maximum file size in bytes.",
    )
    exclude: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                ".git",
                ".venv",
                "__pycache__",
                ".pytest_cache",
                "node_modules",
                "dist",
                "build",
                ".arian",
                ".tmp",
                ".mypy_cache",
                ".ruff_cache",
                "archived",
            }
        ),
        description="Directory names to exclude.",
    )
    use_gitignore: bool = Field(
        default=True,
        description="Honor .gitignore rules. False disables gitignore filtering entirely.",
    )
    nested_gitignore: bool = Field(
        default=False,
        description="Also load .gitignore from ancestor directories of the scan root.",
    )


# ---------------------------------------------------------------------------
# Domain limits
# ---------------------------------------------------------------------------


class DomainLimitsConfig(BaseModel):
    """Cross-cutting numeric limits shared by all layers.

    Attributes:
        max_file_size_bytes: Maximum file size in bytes accepted by
            the collector. Mirrors ``FileCollectorConfig.max_file_size``
            for callers that need the value without instantiating a
            collector.
        max_collected_files: Maximum number of files the collector
            is allowed to gather in a single pass. Beyond this the
            planner refuses to start.
        max_token_budget: Maximum token budget a user may request.
        default_max_concurrent_loads: Bounded-concurrency default
            for content loads.
    """

    model_config = ConfigDict(frozen=True)

    max_file_size_bytes: int = Field(default=10 * 1024 * 1024, description="Max file size in bytes.")
    max_collected_files: int = Field(default=10_000, description="Max files to collect.")
    max_token_budget: int = Field(default=1_000_000, description="Max token budget.")
    default_max_concurrent_loads: int = Field(default=10, description="Bounded concurrency default.")


# ---------------------------------------------------------------------------
# Language detection
# ---------------------------------------------------------------------------


class LanguageConfig(BaseModel):
    """File-language detection lookup tables.

    Attributes:
        lang_map: Extension -> language identifier map.
        filename_map: Filename -> language identifier map.
        shebang_map: Interpreter name -> language identifier map.
        min_shebang_tokens_for_env: Minimum tokens required to
            interpret a ``env``-prefixed shebang line.
        unknown_language: Language string returned when detection
            fails. Distinct from the empty string used internally
            to signal "unrecognised".
    """

    model_config = ConfigDict(frozen=True)

    lang_map: dict[str, str] = Field(
        default_factory=lambda: {
            ".py": "python",
            ".pyx": "python",
            ".pyw": "python",
            ".pyi": "python",
            ".ipynb": "python",
            ".js": "javascript",
            ".jsx": "jsx",
            ".mjs": "javascript",
            ".cjs": "javascript",
            ".ts": "typescript",
            ".tsx": "tsx",
            ".go": "go",
            ".rs": "rust",
            ".java": "java",
            ".kt": "kotlin",
            ".kts": "kotlin",
            ".c": "c",
            ".h": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".hpp": "cpp",
            ".hxx": "cpp",
            ".cs": "csharp",
            ".rb": "ruby",
            ".php": "php",
            ".phtml": "php",
            ".swift": "swift",
            ".sh": "bash",
            ".bash": "bash",
            ".zsh": "zsh",
            ".fish": "fish",
            ".sql": "sql",
            ".html": "html",
            ".htm": "html",
            ".css": "css",
            ".scss": "scss",
            ".sass": "sass",
            ".less": "less",
            ".md": "markdown",
            ".markdown": "markdown",
            ".rst": "rst",
            ".txt": "",
            ".json": "json",
            ".jsonl": "json",
            ".yaml": "yaml",
            ".yml": "yaml",
            ".toml": "toml",
            ".xml": "xml",
            ".svg": "svg",
            ".puml": "puml",
            ".plantuml": "puml",
            ".dockerfile": "dockerfile",
            ".mk": "makefile",
            ".makefile": "makefile",
            ".ini": "ini",
            ".cfg": "ini",
            ".env": "dotenv",
            ".gradle": "gradle",
            ".scala": "scala",
            ".r": "r",
            ".rmd": "r",
            ".lua": "lua",
            ".vim": "vim",
            ".svelte": "svelte",
            ".vue": "vue",
            ".astro": "astro",
            ".jinja2": "jinja2",
            ".j2": "jinja2",
            ".jinja": "jinja2",
            ".mustache": "mustache",
            ".hbs": "handlebars",
            ".tmpl": "template",
            ".tpl": "template",
            ".proto": "protobuf",
            ".graphql": "graphql",
            ".gql": "graphql",
            ".tf": "hcl",
            ".hcl": "hcl",
            ".csv": "csv",
            ".tsv": "tsv",
            ".log": "log",
            ".diff": "diff",
            ".patch": "diff",
        },
        description="Extension -> language identifier map.",
    )
    filename_map: dict[str, str] = Field(
        default_factory=lambda: {
            "makefile": "make",
            "dockerfile": "dockerfile",
            "cmakelists.txt": "cmake",
            "gemfile": "ruby",
            "rakefile": "ruby",
            "justfile": "just",
        },
        description="Filename -> language identifier map.",
    )
    shebang_map: dict[str, str] = Field(
        default_factory=lambda: {
            "python": "python",
            "python3": "python",
            "node": "javascript",
            "ruby": "ruby",
            "bash": "bash",
            "sh": "sh",
            "zsh": "zsh",
            "fish": "fish",
            "perl": "perl",
            "lua": "lua",
            "php": "php",
            "r": "r",
            "scala": "scala",
            "go": "go",
            "rust": "rust",
        },
        description="Interpreter name -> language identifier map.",
    )
    min_shebang_tokens_for_env: int = Field(
        default=2,
        ge=2,
        description="Minimum tokens required for an 'env'-prefixed shebang.",
    )


# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------


class SecurityConfig(BaseModel):
    """Path and secret redaction configuration.

    Attributes:
        max_path_length: Maximum allowed raw path length before it
            is rejected as suspicious.
        secret_patterns: Ordered list of regex patterns whose matches
            are replaced by ``redacted``.
        redacted: Replacement string used to mask secrets.
    """

    model_config = ConfigDict(frozen=True)

    max_path_length: int = Field(default=4096, ge=1, description="Max raw path length.")
    secret_patterns: tuple[Pattern[str], ...] = Field(
        default_factory=lambda: (
            compile(r"(?i)(api[_-]?key|secret|token|password|passwd|pwd)[\"'\s:=]+([A-Za-z0-9_\-]{8,})"),
            compile(r"(?i)bearer\s+([A-Za-z0-9_\-\.]{8,})"),
            compile(
                r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----[\s\S]*?-----END (?:RSA |EC |DSA |OPENSSH |)PRIVATE KEY-----"
            ),
        ),
        description="Ordered regex patterns whose matches are redacted.",
    )
    redacted: str = Field(default="****", description="Replacement used to mask secrets.")


# ---------------------------------------------------------------------------
# Bootstrap
# ---------------------------------------------------------------------------


class BootstrapConfig(BaseModel):
    """Bootstrap-layer runtime configuration.

    Attributes:
        app_module: Dotted module path of the bootstrap module (used
            when configuring the application logger).
        truthy_env_values: Strings recognized as boolean true when
            parsing ``ARIAN_*`` flag environment variables.
    """

    model_config = ConfigDict(frozen=True)

    app_module: str = Field(
        default="arian.bootstrap.logging",
        description="Module path used when configuring the application logger.",
    )
    truthy_env_values: frozenset[str] = Field(
        default_factory=lambda: frozenset({"1", "true", "yes", "on", "TRUE", "True", "YES", "Yes", "ON", "On"}),
        description="Strings recognized as boolean true in ARIAN_* env flags.",
    )


# ---------------------------------------------------------------------------
# Repository (persistence)
# ---------------------------------------------------------------------------


class RepositoryConfig(BaseModel):
    """Repository (persistence) configuration.

    Attributes:
        schema_sql: DDL executed when a new SQLite store is created.
    """

    model_config = ConfigDict(frozen=True)

    schema_sql: str = Field(
        default_factory=lambda: (
            """
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            language TEXT NOT NULL,
            role TEXT NOT NULL,
            tokens INTEGER NOT NULL,
            hash TEXT NOT NULL,
            size_bytes INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS symbols (
            name TEXT NOT NULL,
            kind TEXT NOT NULL,
            file_path TEXT NOT NULL,
            signature TEXT NOT NULL,
            docstring TEXT DEFAULT '',
            line_start INTEGER DEFAULT 0,
            line_end INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS dependencies (
            source_path TEXT NOT NULL,
            target_path TEXT NOT NULL,
            kind TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS modules (
            name TEXT PRIMARY KEY,
            path TEXT NOT NULL,
            files TEXT DEFAULT '[]'
        );
        """
        ),
        description="DDL executed when a new SQLite store is created.",
    )


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


class RendererConfig(BaseModel):
    """Markdown renderer configuration.

    Attributes:
        template_dir: Directory containing the Jinja2 templates used
            to render context manifests.
    """

    model_config = ConfigDict(frozen=True)

    template_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.parent / "template",
        description="Directory containing the Jinja2 templates used for context manifests.",
    )


# ---------------------------------------------------------------------------
# Controller
# ---------------------------------------------------------------------------


class ControllerConfig(BaseModel):
    """CLI / controller input-validation tables.

    Attributes:
        valid_scopes: Set of allowed scope-mode values for ``--scope``.
        valid_tasks: Set of allowed ``--task`` values. Populated
            dynamically from :class:`ContextTask` enum.
    """

    model_config = ConfigDict(frozen=True)

    valid_scopes: frozenset[str] = Field(
        default_factory=lambda: frozenset({"merged", "separate"}),
        description="Set of allowed scope-mode values for --scope.",
    )


# ---------------------------------------------------------------------------
# Service: builder (file-read retry policy)
# ---------------------------------------------------------------------------


class RetryConfig(BaseModel):
    """File-read retry policy used by :class:`ContextBuilder`.

    Attributes:
        attempts: Number of attempts to read a file's bytes before
            propagating the last OSError.
        backoff_base_seconds: Base sleep between retries in seconds.
            The actual sleep for attempt N is
            ``backoff_base_seconds * backoff_exponent_base**N``.
        backoff_exponent_base: Base of the exponential backoff exponent.
    """

    model_config = ConfigDict(frozen=True)

    attempts: int = Field(default=3, ge=1, description="Number of read attempts.")
    backoff_base_seconds: float = Field(default=0.05, gt=0.0, description="Base retry backoff in seconds.")
    backoff_exponent_base: int = Field(default=2, ge=2, description="Base of the backoff exponent.")


# ---------------------------------------------------------------------------
# Infrastructure: git operations
# ---------------------------------------------------------------------------


class GitConfig(BaseModel):
    """Git subprocess operation configuration.

    Attributes:
        timeout_seconds: Maximum seconds to wait for a git subprocess
            before killing it. Protects against hangs on large or
            corrupted repositories.
    """

    model_config = ConfigDict(frozen=True)

    timeout_seconds: float = Field(default=30.0, gt=0.0, description="Git subprocess timeout in seconds.")


# ---------------------------------------------------------------------------
# Service: analyzer (Python source patterns)
# ---------------------------------------------------------------------------


class AnalyzerConfig(BaseModel):
    """Python source layout detection configuration.

    Attributes:
        def_pattern: Regex matching a top-level def / async def / class header.
        import_pattern: Regex matching a top-level import / from-import.
        docstring_start: Regex matching the opening of a docstring,
            possibly prefixed by a raw / unicode / bytes / f-string marker.
        min_singleline_docstring_quotes: Minimum count of triple-quote
            characters on a single line to count as a complete docstring
            (one opening + one closing).
    """

    model_config = ConfigDict(frozen=True)

    def_pattern: Pattern[str] = Field(
        default_factory=lambda: compile(r"^(\s*)(async\s+)?(def|class|async\s+def)\s+\w+.*?:\s*(?:#.*)?$"),
        description="Regex matching a def / class header line.",
    )
    import_pattern: Pattern[str] = Field(
        default_factory=lambda: compile(r"^\s*(from\s+\S+\s+import|import\s+)"),
        description="Regex matching a top-level import line.",
    )
    docstring_start: Pattern[str] = Field(
        default_factory=lambda: compile(r'^\s*[rRuUbBfF]*("""|\'\'\')'),
        description="Regex matching the opening of a docstring.",
    )
    min_singleline_docstring_quotes: int = Field(
        default=2,
        ge=2,
        description="Minimum triple-quote count for a single-line docstring.",
    )


# ---------------------------------------------------------------------------
# Service: classifier (file-role lookup tables)
# ---------------------------------------------------------------------------


class ClassifierConfig(BaseModel):
    """File-role classification configuration.

    All fields are the canonical lookup tables consumed by
    :class:`FileClassifier`. They are exposed as configuration
    rather than as module-level constants so the rules can be
    reviewed, extended, and (in principle) overridden per
    invocation.

    Attributes:
        readme_names: Filenames (and variants) that mark a README.
        config_names: Explicit configuration filenames (basename match).
        entry_names: Filenames that mark a module's entry point.
        generated_parts: Path parts that mark generated/vendor code.
        config_suffixes: File suffixes treated as configuration.
        doc_suffixes: File suffixes treated as documentation.
        web_suffixes: File suffixes treated as web/service code.
        basename_config: Configuration file basenames (no extension match).
        doc_parts: Path parts that mark documentation directories.
        test_parts: Path parts that mark test directories.
        util_parts: Path parts that mark utility/helper directories.
        role_importance: Base importance score per role (0 = highest).
        role_compression: Default compression level per role.
    """

    model_config = ConfigDict(frozen=True)

    readme_names: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {"readme", "readme.md", "readme.rst", "readme.txt", "contributing", "contributing.md"}
        ),
        description="Filenames (and variants) that mark a README.",
    )
    config_names: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {
                "pyproject.toml",
                "setup.py",
                "setup.cfg",
                "package.json",
                "tsconfig.json",
                "cargo.toml",
                "go.mod",
                "makefile",
                "dockerfile",
                ".env",
                ".env.example",
            }
        ),
        description="Explicit configuration filenames (basename match).",
    )
    entry_names: frozenset[str] = Field(
        default_factory=lambda: frozenset({"main.py", "__main__.py", "app.py", "cli.py"}),
        description="Filenames that mark an entry point.",
    )
    generated_parts: frozenset[str] = Field(
        default_factory=lambda: frozenset({"migrations", "generated", "__generated__", "vendor", "node_modules"}),
        description="Path parts that mark generated code.",
    )
    config_suffixes: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {".toml", ".yaml", ".yml", ".ini", ".cfg", ".sql", ".json", ".jsonl", ".xml", ".env"}
        ),
        description="File suffixes treated as configuration.",
    )
    doc_suffixes: frozenset[str] = Field(
        default_factory=lambda: frozenset({".md", ".markdown", ".rst", ".txt"}),
        description="File suffixes treated as documentation.",
    )
    web_suffixes: frozenset[str] = Field(
        default_factory=lambda: frozenset(
            {".html", ".htm", ".css", ".scss", ".sass", ".less", ".svelte", ".vue", ".astro"}
        ),
        description="File suffixes treated as web/service code.",
    )
    basename_config: frozenset[str] = Field(
        default_factory=lambda: frozenset({"makefile", "dockerfile", "cmakelists.txt", "justfile"}),
        description="Configuration file basenames (no extension).",
    )
    doc_parts: frozenset[str] = Field(
        default_factory=lambda: frozenset({"docs", "doc"}),
        description="Path parts that mark documentation directories.",
    )
    test_parts: frozenset[str] = Field(
        default_factory=lambda: frozenset({"test", "tests", "testing"}),
        description="Path parts that mark test directories.",
    )
    util_parts: frozenset[str] = Field(
        default_factory=lambda: frozenset({"util", "utils", "utility", "helpers", "common"}),
        description="Path parts that mark utility directories.",
    )
    role_importance: dict[FileRole, int] = Field(
        default_factory=lambda: {
            FileRole.README: 0,
            FileRole.DOCUMENTATION: 1,
            FileRole.ENTRY_POINT: 1,
            FileRole.CONFIGURATION: 2,
            FileRole.DOMAIN: 2,
            FileRole.SERVICE: 3,
            FileRole.INFRASTRUCTURE: 4,
            FileRole.UTILITY: 5,
            FileRole.UNKNOWN: 6,
            FileRole.TEST: 7,
            FileRole.GENERATED: 9,
        },
        description="Base importance score per role (0 = highest priority).",
    )
    role_compression: dict[FileRole, CompressionLevel] = Field(
        default_factory=lambda: {
            FileRole.README: CompressionLevel.FULL,
            FileRole.DOCUMENTATION: CompressionLevel.FULL,
            FileRole.ENTRY_POINT: CompressionLevel.FULL,
            FileRole.CONFIGURATION: CompressionLevel.FULL,
            FileRole.DOMAIN: CompressionLevel.FULL,
            FileRole.SERVICE: CompressionLevel.FULL,
            FileRole.INFRASTRUCTURE: CompressionLevel.FULL,
            FileRole.UTILITY: CompressionLevel.SIGNATURES,
            FileRole.UNKNOWN: CompressionLevel.FULL,
            FileRole.TEST: CompressionLevel.SIGNATURES,
            FileRole.GENERATED: CompressionLevel.STRUCTURE,
        },
        description="Default compression level per role.",
    )


# ---------------------------------------------------------------------------
# Service: materializer
# ---------------------------------------------------------------------------


class MaterializerConfig(BaseModel):
    """Context materializer configuration.

    Attributes:
        min_fragment_chunk_occurrences: A fragment path is worth
            merging only if it appears in at least this many chunks.
    """

    model_config = ConfigDict(frozen=True)

    min_fragment_chunk_occurrences: int = Field(
        default=2,
        ge=2,
        description="Minimum chunks a fragment path must appear in to be merged.",
    )


# ---------------------------------------------------------------------------
# Service: planner
# ---------------------------------------------------------------------------


class PlannerConfig(BaseModel):
    """Context planner configuration — role ordering and task boosts.

    Attributes:
        role_order: Role-priority ordering used when sorting planned
            files within a chunk. Lower number = higher priority.
        task_file_boost: Per-task importance deltas applied on top of
            the base score. Negative numbers boost a role.
        compression_ratios: Estimated fraction of original tokens that
            survive each compression level.
        fragment_signature_ratio: Token fraction assumed for a
            SIGNATURES fragment of a large file.
    """

    model_config = ConfigDict(frozen=True)

    role_order: dict[FileRole, int] = Field(
        default_factory=lambda: {
            FileRole.README: 0,
            FileRole.DOCUMENTATION: 1,
            FileRole.ENTRY_POINT: 2,
            FileRole.CONFIGURATION: 3,
            FileRole.DOMAIN: 4,
            FileRole.SERVICE: 5,
            FileRole.INFRASTRUCTURE: 6,
            FileRole.UTILITY: 7,
            FileRole.TEST: 8,
            FileRole.GENERATED: 9,
            FileRole.UNKNOWN: 10,
        },
        description="Role-priority ordering within a chunk (lower = earlier).",
    )
    task_file_boost: dict[ContextTask, dict[FileRole, int]] = Field(
        default_factory=lambda: {
            ContextTask.BUG_FIX: {
                FileRole.TEST: -3,
                FileRole.SERVICE: -2,
                FileRole.DOMAIN: -1,
            },
            ContextTask.FEATURE: {
                FileRole.DOMAIN: -2,
                FileRole.SERVICE: -1,
                FileRole.TEST: -1,
            },
            ContextTask.REVIEW: {
                FileRole.SERVICE: -2,
                FileRole.DOMAIN: -1,
            },
            ContextTask.ONBOARDING: {
                FileRole.README: -5,
                FileRole.CONFIGURATION: -1,
            },
            ContextTask.REFACTOR: {
                FileRole.SERVICE: -2,
                FileRole.INFRASTRUCTURE: -1,
            },
            ContextTask.DOCUMENT: {
                FileRole.README: -3,
                FileRole.DOMAIN: -1,
                FileRole.SERVICE: -1,
            },
            ContextTask.GENERAL: {},
        },
        description="Per-task importance deltas (negative = boost).",
    )
    compression_ratios: dict[CompressionLevel, float] = Field(
        default_factory=lambda: {
            CompressionLevel.FULL: 1.0,
            CompressionLevel.SIGNATURES: 0.3,
            CompressionLevel.STRUCTURE: 0.1,
            CompressionLevel.SUMMARY: 0.05,
            CompressionLevel.AUTO: 1.0,
        },
        description="Estimated token survival ratio per compression level.",
    )
    fragment_signature_ratio: float = Field(
        default=0.3,
        gt=0.0,
        lt=1.0,
        description="Token fraction assumed for a SIGNATURES fragment.",
    )


# ---------------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------------


class ArianConfig(BaseModel):
    """Root configuration for Arian — hierarchical, frozen, injectable.

    All service-layer configuration lives here, grouped by the
    service that consumes it. The bootstrap reads an ``ArianConfig``
    instance and wires each slice into the corresponding service
    constructor.

    Attributes:
        logging: Logging configuration.
        collector: File collector configuration.
        limits: Cross-cutting numeric limits.
        language: File-language lookup tables.
        security: Path / secret redaction rules.
        bootstrap: Bootstrap-layer constants.
        repository: Persistence-layer schema.
        renderer: Markdown template location.
        controller: CLI input-validation tables.
        retry: File-read retry policy.
        git: Git subprocess operation configuration.
        analyzer: Python source pattern configuration.
        classifier: File-role classification tables.
        materializer: Fragment merging threshold.
        planner: Role ordering and task boosts.
    """

    model_config = ConfigDict(frozen=True)

    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    collector: FileCollectorConfig = Field(default_factory=FileCollectorConfig)
    limits: DomainLimitsConfig = Field(default_factory=DomainLimitsConfig)
    language: LanguageConfig = Field(default_factory=LanguageConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    bootstrap: BootstrapConfig = Field(default_factory=BootstrapConfig)
    repository: RepositoryConfig = Field(default_factory=RepositoryConfig)
    renderer: RendererConfig = Field(default_factory=RendererConfig)
    controller: ControllerConfig = Field(default_factory=ControllerConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    git: GitConfig = Field(default_factory=GitConfig)
    analyzer: AnalyzerConfig = Field(default_factory=AnalyzerConfig)
    classifier: ClassifierConfig = Field(default_factory=ClassifierConfig)
    materializer: MaterializerConfig = Field(default_factory=MaterializerConfig)
    planner: PlannerConfig = Field(default_factory=PlannerConfig)

    @staticmethod
    def load() -> ArianConfig:
        """Create a fresh ArianConfig with default values.

        Returns:
            New ArianConfig instance.
        """
        return ArianConfig()

    @classmethod
    def load_from_env(cls) -> ArianConfig:
        """Create ArianConfig from environment variables.

        Environment variables:
            ARIAN_LOG_LEVEL: Logging level (default: INFO).
            ARIAN_LOG_DIR: Logging directory path (default: ~/.arian/logs).
            ARIAN_EXTENSIONS: Comma-separated file extensions (narrowing filter).
                When set, only these extensions are collected.
                When unset, all text files are collected.
            ARIAN_EXCLUDE: Comma-separated directory names to exclude.
            ARIAN_NO_GITIGNORE: When set to a truthy value (``1``, ``true``,
                ``yes``, ``on``), ``.gitignore`` rules are ignored.
            ARIAN_NESTED_GITIGNORE: When set to a truthy value, ``.gitignore``
                files in ancestor directories of the scan root are also
                honored.

        Returns:
            ArianConfig populated from environment variables.
        """
        log_level: str = os.environ.get("ARIAN_LOG_LEVEL", "INFO")
        log_dir_raw: str | None = os.environ.get("ARIAN_LOG_DIR")
        log_dir: Path | None = Path(log_dir_raw) if log_dir_raw else Path("~/.arian/logs")

        logging_cfg = LoggingConfig(level=log_level, log_dir=log_dir)

        collector_kwargs: dict[str, Any] = {}
        extensions_raw: str | None = os.environ.get("ARIAN_EXTENSIONS")
        if extensions_raw:
            collector_kwargs["extensions"] = frozenset(
                ext.strip() if ext.strip().startswith(".") else f".{ext.strip()}"
                for ext in extensions_raw.split(",")
                if ext.strip()
            )

        exclude_raw: str | None = os.environ.get("ARIAN_EXCLUDE")
        if exclude_raw:
            collector_kwargs["exclude"] = frozenset(name.strip() for name in exclude_raw.split(",") if name.strip())

        truthy_values: frozenset[str] = BootstrapConfig().truthy_env_values
        if is_truthy(os.environ.get("ARIAN_NO_GITIGNORE"), truthy_values):
            collector_kwargs["use_gitignore"] = False
        if is_truthy(os.environ.get("ARIAN_NESTED_GITIGNORE"), truthy_values):
            collector_kwargs["nested_gitignore"] = True

        collector_cfg = FileCollectorConfig(**collector_kwargs)
        return cls(logging=logging_cfg, collector=collector_cfg)

    @classmethod
    def load_from_dict(cls, a_data: dict[str, Any]) -> ArianConfig:  # any-exempt: external dict input schema
        """Create ArianConfig from a dictionary — useful for testing.

        Args:
            a_data: Dictionary with optional configuration keys.

        Returns:
            ArianConfig populated from the provided dictionary.
        """
        return cls.model_validate(a_data)

    @classmethod
    def load_with_precedence(cls, a_env: dict[str, str] | None = None) -> ArianConfig:
        """Load config with precedence: defaults < env < CLI.

        Precedence order:
            1. Built-in defaults (class fields)
            2. Environment variables (ARIAN_LOG_LEVEL, etc.)
            3. CLI args (future — not yet implemented)

        Args:
            a_env: Optional environment dict (for testing). Uses os.environ if None.

        Returns:
            ArianConfig with values resolved by precedence.
        """
        cfg = cls.load()
        env = a_env if a_env is not None else dict(os.environ)
        if "ARIAN_LOG_LEVEL" in env:
            level: str = env["ARIAN_LOG_LEVEL"].upper()
            cfg = cfg.model_copy(update={"logging": cfg.logging.model_copy(update={"level": level})})
        if "ARIAN_LOG_DIR" in env:
            raw: str = env["ARIAN_LOG_DIR"]
            log_dir: Path | None = Path(raw) if raw else None
            cfg = cfg.model_copy(update={"logging": cfg.logging.model_copy(update={"log_dir": log_dir})})
        return cfg
