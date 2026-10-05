"""Query helpers over the capability database."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from .loader import load_all_models, load_model, load_scope


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("-", "_")).strip().lower()


def list_models(root: Path) -> List[Dict[str, Any]]:
    scope = load_scope(root)
    out = []
    for m in scope["models"]:
        doc = load_model(root, m)
        out.append({"model": doc["model"], "family": doc["family"], "version": doc["version"]})
    return out


def find(root: Path, query: str) -> List[Dict[str, Any]]:
    q = _norm(query)
    results = []
    for doc in load_all_models(root):
        candidates = [
            ("model", doc["model"]),
            ("family", doc["family"]),
        ] + [("alias", a) for a in doc.get("aliases", [])]
        for field, val in candidates:
            if q in _norm(str(val)):
                results.append({
                    "model": doc["model"],
                    "family": doc["family"],
                    "matched_field": field,
                    "matched_value": val,
                })
    return results


def resolve_model(root: Path, name: str) -> Optional[Dict[str, Any]]:
    n = _norm(name)
    scope = load_scope(root)
    for m in scope["models"]:
        doc = load_model(root, m)
        if _norm(doc["model"]) == n:
            return doc
        for a in doc.get("aliases", []):
            if _norm(a) == n:
                return doc
    return None


def is_excluded(root: Path, name: str) -> Optional[Dict[str, Any]]:
    """Return the excluded_models entry (if any) matching a name."""
    n = _norm(name)
    scope = load_scope(root)
    for entry in scope.get("excluded_models", []) or []:
        if _norm(entry.get("model", "")) == n:
            return entry
    return None


def get_path(doc: Dict[str, Any], path: str) -> Any:
    node: Any = doc
    for part in path.split("."):
        if isinstance(node, dict):
            if part not in node:
                raise KeyError(path)
            node = node[part]
        else:
            raise KeyError(path)
    return node