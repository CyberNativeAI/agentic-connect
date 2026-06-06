# cybernative-connect release and manual publish fallback

This checklist keeps `cybernative-connect` ready to publish when PyPI trusted
publisher access or an explicit token is available.

## Local release verification

Run from the repository root:

```bash
py -3 -m pip install -r requirements-dev.txt
py -3 -m pip install build twine
py -3 -m pytest
py -3 scripts/_ce_skill_validate.py
py -3 -m build
py -3 -m twine check dist/*
```

Expected artifacts for v1.3.2:

```text
dist/cybernative_connect-1.3.2-py3-none-any.whl
dist/cybernative_connect-1.3.2.tar.gz
```

## Install from staged artifacts

Use a clean virtual environment:

```bash
py -3 -m venv .venv-release
.\.venv-release\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install dist/cybernative_connect-1.3.2-py3-none-any.whl
cybernative-connect --help
python -c "from cybernative_tools import CyberNativeClient; print(CyberNativeClient.__name__)"
```

## Publish when credentials exist

Preferred path is PyPI trusted publishing from CI. Manual fallback when the board
provides a PyPI token:

```bash
py -3 -m twine upload --repository pypi dist/*
```

Use `TWINE_USERNAME=__token__` and `TWINE_PASSWORD=<pypi-token>` in the local
environment or the interactive prompt. Do not paste tokens into tickets, logs,
screenshots, or checked-in files.

## Pre-publish guardrails

- Confirm `pyproject.toml` version matches the intended release tag.
- Rebuild `dist/` from a clean tree; do not upload stale artifacts.
- Run `twine check dist/*` immediately before upload.
- Verify README rendering and console script help after wheel install.
- If publish fails, preserve the command output in a redacted issue comment and
  do not retry with modified credentials until the owner confirms the token scope.
