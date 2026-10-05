from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sim800_capabilities.query import list_models, find, resolve_model, get_path


def test_list_models():
    root = Path(__file__).resolve().parents[1]
    rows = list_models(root)
    assert len(rows) == 9
    assert all("model" in r and "family" in r for r in rows)


def test_find():
    root = Path(__file__).resolve().parents[1]
    hits = find(root, "sim808")
    assert any(h["model"] == "SIM808" for h in hits)


def test_resolve_and_get():
    root = Path(__file__).resolve().parents[1]
    doc = resolve_model(root, "SIM800")
    assert doc is not None
    fv = get_path(doc, "capabilities.bands.type")
    assert fv["value"] == "quad-band"