from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sim800_capabilities.compare import compare


def test_compare_identical():
    root = Path(__file__).resolve().parents[1]
    rows = compare(root, "SIM800", "SIM800")
    assert all(r["diff_type"] == "same" for r in rows)


def test_compare_different():
    root = Path(__file__).resolve().parents[1]
    rows = compare(root, "SIM800", "SIM800L")
    assert any(r["diff_type"] == "different" for r in rows)