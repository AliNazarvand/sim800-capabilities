from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sim800_capabilities.validator import validate


def test_data_integrity_passes():
    root = Path(__file__).resolve().parents[1]
    errors = validate(root)
    assert errors == [], "Validation errors:\n" + "\n".join(errors)


def test_all_models_are_parseable():
    import yaml
    root = Path(__file__).resolve().parents[1]
    scope = yaml.safe_load((root / "data" / "scope.yaml").read_text(encoding="utf-8"))
    for m in scope["models"]:
        p = root / "data" / "models" / f"{m.lower()}.yaml"
        assert p.exists(), f"missing model file for {m}"
        doc = yaml.safe_load(p.read_text(encoding="utf-8"))
        assert doc["model"] == m
        assert "capabilities" in doc
        assert "power" in doc["capabilities"]
        assert "current_consumption" in doc["capabilities"]["power"]