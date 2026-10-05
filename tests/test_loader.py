from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sim800_capabilities.loader import (
    load_scope, load_sources, load_model, load_all_models,
    compute_content_hash, compute_scope_hash, canonical_json,
)


def test_load_scope():
    root = Path(__file__).resolve().parents[1]
    scope = load_scope(root)
    assert "SIM800" in scope["models"]
    assert scope["family_map"]["SIM800"] == "SIM800"


def test_load_all_models():
    root = Path(__file__).resolve().parents[1]
    models = load_all_models(root)
    assert len(models) == 9


def test_canonical_json_stable():
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonical_json(a) == canonical_json(b)


def test_hashes_are_deterministic():
    root = Path(__file__).resolve().parents[1]
    sources = load_sources(root)["sources"]
    models = load_all_models(root)
    h1 = compute_content_hash(models, sources)
    h2 = compute_content_hash(models, sources)
    assert h1 == h2
    assert len(h1) == 64