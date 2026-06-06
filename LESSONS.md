# Lessons

## 2026-06-06 — Flat py-modules + bare `pytest` (CYB-255)

CI failed with pytest exit code 2 (`ModuleNotFoundError` for `cybernative_connect`) because only `requirements-dev.txt` was installed and CI invoked bare `pytest`. The console script does not add the repo root to `sys.path`; `python -m pytest` does. For setuptools `py-modules` layouts, either `pip install -e .` in CI, set `[tool.pytest.ini_options] pythonpath = ["."]`, or use `python -m pytest`. Reproduce with a fresh venv that has not run `pip install -e .`.
