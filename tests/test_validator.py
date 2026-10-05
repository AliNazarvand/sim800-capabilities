from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sim800_capabilities.validator import validate


def test_valid_database():
    root = Path(__file__).resolve().parents[1]
    errors = validate(root)
    assert errors == [], "Validation errors:\n" + "\n".join(errors)