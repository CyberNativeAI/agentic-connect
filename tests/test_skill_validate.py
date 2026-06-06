import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_validate_module():
    spec = importlib.util.spec_from_file_location(
        "ce_skill_validate",
        REPO_ROOT / "scripts" / "_ce_skill_validate.py",
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_skill_validate_passes_on_repo():
    module = _load_validate_module()
    assert module.validate() == []


def test_skill_validate_detects_missing_method(monkeypatch):
    module = _load_validate_module()
    monkeypatch.setattr(module, "public_client_methods", lambda: ["phantom_method"])
    errors = module.validate()
    assert errors
    assert any("phantom_method" in err for err in errors)
