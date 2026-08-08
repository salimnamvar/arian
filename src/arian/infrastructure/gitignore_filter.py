"""Path filtering using pathspec for .gitignore support.

Supports three orthogonal controls:

    1. Directory-name excludes (e.g. ``.git``, ``node_modules``).
    2. ``.gitignore`` patterns loaded from CWD and (optionally) every
       ``.gitignore`` file found under CWD recursively. Nested rules
       are honored in deepest-first order, mirroring git's resolution
       order. ``!`` negation patterns are honored.
    3. An explicit-path allow-list — any path that is, or lives beneath,
       a path in this set bypasses the gitignore filter entirely. This
       mirrors ``git add -f`` semantics so that CLI positional
       arguments always win over a too-broad gitignore rule.

The filter is designed to be re-used across many ``should_include()``
calls within a single collection. ``last_matched_pattern`` is set
whenever the filter rejects a path due to a gitignore rule so the
collector can attribute skips to the offending pattern.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pathspec


@dataclass(frozen=True)
class GitignoreOptions:
    """Static configuration for the gitignore layer.

    The filter accepts these as a single object so its public surface
    stays free of boolean positional parameters — a safe-coding
    no-no (NASA JPL Power-of-Ten rule 4: limit function arguments).

    Attributes:
        enabled: When False, no ``.gitignore`` rules are honored.
        nested: When True, ``.gitignore`` files in every directory
            under cwd are also loaded, deepest first. Off by default
            to preserve the pre-existing single-file behaviour.
    """

    enabled: bool = True
    nested: bool = False


class PathFilter:
    """Filter paths using gitignore patterns.

    Attributes:
        _exclude: Directory names that are always excluded.
        _gitignore_specs: Loaded ``(root, spec)`` pairs, deepest first.
        _explicit_paths: Paths whose contents always pass the filter.
        last_matched_pattern: After ``should_include`` returns False for
            a gitignore reason, the source pattern. ``None`` otherwise.
    """

    def __init__(
        self,
        a_exclude: frozenset[str],
        a_gitignore_options: GitignoreOptions = GitignoreOptions(),
    ) -> None:
        """Initialize path filter.

        Args:
            a_exclude: Directory names to always exclude (e.g. ``.git``).
            a_gitignore_options: Static gitignore layer configuration.
                The explicit-path allow-list is set at runtime via
                :meth:`set_explicit_paths` because it changes per
                collection call.
        """
        self._exclude: frozenset[str] = a_exclude
        self._explicit_paths: frozenset[Path] = frozenset()
        self._gitignore_specs: list[tuple[Path, Any]] = (
            self._load_gitignore_specs(a_gitignore_options) if a_gitignore_options.enabled else []
        )
        self.last_matched_pattern: str | None = None

    def set_explicit_paths(self, a_paths: frozenset[Path]) -> None:
        """Replace the explicit-path allow-list.

        Args:
            a_paths: New set of paths that always pass the filter.
        """
        self._explicit_paths = a_paths

    def _load_gitignore_specs(self, a_options: GitignoreOptions) -> list[tuple[Path, Any]]:
        """Return ``(dir, spec)`` pairs for every ``.gitignore`` to honor.

        When ``nested`` is disabled, only ``<cwd>/.gitignore`` is
        loaded. When enabled, every ``.gitignore`` under cwd is
        loaded, deepest first — so a deeper file's rules take
        precedence over a shallower one (matching git's own
        behaviour). The list is empty when no ``.gitignore`` is found.

        Args:
            a_options: Gitignore layer configuration.

        Returns:
            List of ``(directory, PathSpec)`` tuples, deepest first.
        """
        cwd: Path = Path.cwd()
        gitignore_files: list[Path] = []
        primary: Path = cwd / ".gitignore"
        if primary.is_file():
            gitignore_files.append(primary)
        if a_options.nested:
            for descendant in cwd.rglob(".gitignore"):
                if descendant != primary and descendant.is_file():
                    gitignore_files.append(descendant)
        specs: list[tuple[Path, Any]] = []
        for gi in gitignore_files:
            spec: Any = pathspec.PathSpec.from_lines(
                "gitignore",
                gi.read_text().splitlines(),
            )
            specs.append((gi.parent, spec))
        # Deepest first (most parents = deepest file)
        specs.sort(key=lambda pair: len(pair[0].parts), reverse=True)
        return specs

    @staticmethod
    def _effective_ignore_pattern(a_spec: Any, a_relative: str) -> str | None:
        """Return the gitignore pattern that caused ``a_relative`` to be ignored.

        Gitignore rules are applied in order, and the *last* matching
        pattern wins. ``!pattern`` (``include=False``) negates any
        earlier ``include=True`` match. So we walk the patterns and
        remember only the last one that matched, returning it only if
        it is an inclusion rule (i.e. the path is actually ignored).
        Comment and blank lines (which ``pathspec`` represents as
        ``include=None``, ``regex=None`` patterns) are skipped.

        Args:
            a_spec: A :class:`pathspec.PathSpec` instance.
            a_relative: Path relative to the directory of the
                ``.gitignore`` that produced the spec.

        Returns:
            The pattern string that effectively ignored the path, or
            ``None`` if no inclusion pattern matched.
        """
        effective: str | None = None
        for pattern in a_spec.patterns:
            if pattern.include is None or pattern.regex is None:
                continue
            if pattern.regex.match(a_relative):
                effective = pattern.pattern if pattern.include else None
        return effective

    @staticmethod
    def _is_within(a_path: Path, a_root: Path) -> bool:
        """Return True if ``a_path`` equals ``a_root`` or lives beneath it.

        Lexical containment check that never raises: a path is within a
        root when the root is the path itself or one of its parents.
        This avoids the exception-as-control-flow pattern of
        ``try: relative_to``.

        Args:
            a_path: Absolute path to test.
            a_root: Root directory to test against.

        Returns:
            True if ``a_path`` is ``a_root`` or a descendant of it.
        """
        result: bool = a_root == a_path or a_root in a_path.parents
        return result

    def _is_under_explicit(self, a_path: Path) -> bool:
        """Return True if ``a_path`` is, or lives beneath, an explicit path.

        Args:
            a_path: Absolute or relative path to test.

        Returns:
            True if any explicit path is a prefix of ``a_path`` (or
            equal to it).
        """
        result: bool = any(self._is_within(a_path, root) for root in self._explicit_paths)
        return result

    def _gitignore_rejects(self, a_path: Path) -> str | None:
        """Return the pattern string that rejects ``a_path``, or None.

        Walks every loaded ``(root, spec)`` pair in deepest-first
        order. The first one that matches ``a_path`` (relative to its
        own root) decides. The effective pattern — accounting for
        ``!`` negation within the spec — is returned for diagnostics.

        The input path is resolved to absolute first so that callers
        may pass either absolute paths (e.g. from
        :func:`pathlib.Path.iterdir` of an absolute root) or relative
        paths (e.g. when scanning ``Path(".")``).

        Args:
            a_path: Absolute or relative path to test.

        Returns:
            The pattern string that caused the rejection, or ``None``
            if no rule matched.
        """
        result: str | None = None
        resolved: Path = a_path if a_path.is_absolute() else (Path.cwd() / a_path)
        for spec_root, spec in self._gitignore_specs:
            if not self._is_within(resolved, spec_root):
                continue
            relative: str = str(resolved.relative_to(spec_root))
            if spec.match_file(relative):
                result = self._effective_ignore_pattern(spec, relative)
                break
        return result

    def should_include(self, a_path: Path) -> bool:
        """Check if path should be included.

        Gate order: excluded dir → explicit override → gitignore.

        Args:
            a_path: Path to check.

        Returns:
            True if path should be included. Side effect: when this
            returns False, ``last_matched_pattern`` is set to the
            offending rule (``"<exclude>"`` for directory-name excludes,
            or the matching gitignore pattern string).
        """
        result: bool = True
        self.last_matched_pattern = None
        resolved: Path = a_path if a_path.is_absolute() else (Path.cwd() / a_path)
        if any(part in self._exclude for part in resolved.parts):
            self.last_matched_pattern = "<exclude>"
            result = False
        elif not self._is_under_explicit(resolved):
            matched: str | None = self._gitignore_rejects(a_path)
            if matched is not None:
                self.last_matched_pattern = matched
                result = False
        return result
