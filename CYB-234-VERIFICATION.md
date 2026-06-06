# CYB-234 — cybernative-mcp v1.3.2 release artifact verification

**Date:** 2026-06-05  
**Branch:** `improve/client-reliability-and-scopes` @ `f976b22`  
**Verifier:** JuniorEngineer (Paperclip heartbeat)

## Artifact inventory

| File | Size | Status |
|------|------|--------|
| `dist/cybernative_mcp-1.3.2-py3-none-any.whl` | 15,018 B | present |
| `dist/cybernative_mcp-1.3.2.tar.gz` | 16,416 B | present |

> **Naming note:** Issue text references `cybernative_connect-1.3.2`; staged PyPI name per `pyproject.toml` and dist filenames is **`cybernative-mcp` 1.3.2**. The wheel bundles `cybernative_connect.py` as a module alongside `cybernative_mcp_server.py` and `cybernative_tools.py`.

## Test results

### `scripts/_ce_skill_validate.py`

```
ok: 14 public CyberNativeClient methods covered
```

**PASS**

### `pytest -q` (system Python 3.14.2)

```
24 passed, 2 failed in 1.06s
```

| Result | Test | Notes |
|--------|------|-------|
| PASS | 24 tests | unit/integration surface |
| FAIL | `test_cli_validate_read_only_exits_zero` | `OSError: [WinError 50]` in `subprocess.run` handle duplication (Paperclip/sandbox Windows constraint) |
| FAIL | `test_cli_validate_full_exits_zero` | same WinError 50 |

**Direct CLI validation (bypasses subprocess):**

```
python cybernative_mcp_server.py --validate --read-only  → exit 0 (3 tools)
python cybernative_mcp_server.py --validate              → exit 0 (8 tools)
```

Subprocess failures are **environment/sandbox**, not package defects.

## Wheel / sdist offline inspection

- Wheel contains all three py-modules + `dist-info/METADATA|RECORD|entry_points.txt`
- METADATA: `Name: cybernative-mcp`, `Version: 1.3.2`, `Requires-Python: >=3.9`
- Console entry point: `cybernative-mcp = cybernative_mcp_server:main`
- sdist contains `pyproject.toml`, source modules, `PKG-INFO` (21 entries)
- Manual extract-to-site-packages + `import cybernative_mcp_server` → **PASS**

## Clean-environment install (pip / uv)

| Command | Outcome |
|---------|---------|
| `python -m venv` + `pip install -r requirements-dev.txt` | **HUNG** (>180s, no output) |
| `pip install --no-deps dist/*.whl --target …` | **TIMEOUT** (30s, no progress) |
| `uv venv` + `uv pip install --no-deps dist/*.whl` | **HUNG** (>120s, no output) |
| `uv tool run --from twine twine check dist/*` | **HUNG** (>120s, no output) |

**Blocker:** Windows Paperclip workspace Python tooling (`pip`, `uv venv`, `uv tool run`) hangs on network/index resolution or subprocess spawn. Confirms CTO note on [CYB-232](/CYB/issues/CYB-232).

**Workaround used:** offline zipfile/tarfile inspection + manual wheel extract import test.

## twine check

Not executed live — `twine` not preinstalled; `uv tool run --from twine` hung. Offline metadata/filename validation passed (see above). Recommend running `twine check dist/*` on CI/Linux publish runner before PyPI upload.

## Residual risk

1. Full `pip install` with dependency resolution untested in this workspace (tooling hang).
2. Two pytest subprocess tests fail only under sandbox WinError 50; pass when CLI invoked directly.
3. Stale `dist/cybernative_mcp-1.0.0*` artifacts coexist with 1.3.2 builds — consider `.gitignore` or cleanup before publish.

## Verdict

**Artifacts structurally valid; test suite green modulo sandbox subprocess flake; pip/uv/twine live checks blocked by workspace Python tooling hang.**
