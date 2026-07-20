# Fix: Template missing from PyPI wheel (v0.5.0)

## Problem

`arian` v0.5.0 on PyPI ships without `document.md.jinja2`, causing:

```
TemplateNotFound: 'document.md.jinja2' not found in search path:
  '/home/salim/.local/lib/python3.13/site-packages/arian/template'
```

Only `__init__.py` is present in the installed `arian/template/` directory.

## Root Cause

The `[tool.setuptools.package-data]` section was added to `pyproject.toml` **after** the `v0.5.0` tag:

| Commit | Date | Event |
|--------|------|-------|
| `42ef51f` | 2026-07-19 00:18 | Template file added to source |
| `d7dab19` (tag: `v0.5.0`) | 2026-07-19 | **Release published without package-data** |
| `5374269` | 2026-07-19 18:59 | `package-data` added to pyproject.toml (too late) |

The current `pyproject.toml` has the correct config:

```toml
[tool.setuptools.package-data]
"arian" = ["template/*.jinja2"]
```

But the published v0.5.0 wheel was built without it.

## Plan

### Step 1: Build v0.5.1 locally

```bash
cd /home/salim/prj/salim/arian
python -m build
```

Verify the wheel contains the template:

```bash
unzip -l dist/arian-0.5.1*.whl | grep jinja2
```

Expected: `arian/template/document.md.jinja2` present.

### Step 2: Check the wheel with twine

```bash
twine check dist/*
```

### Step 3: Publish to PyPI

```bash
twine upload dist/*
```

(Requires PyPI credentials / API token)

### Step 4: Upgrade local install

```bash
pip install --user arian --upgrade
```

### Step 5: Verify

```bash
arian --help
```

No `TemplateNotFound` error.

## Files Changed

None -- the fix is already in the current source (`pyproject.toml` line 65-66). This plan is purely about cutting a new release.

## Risk

Low. The only change in the wheel vs v0.5.0 is the inclusion of the template file that was always intended to be shipped.
