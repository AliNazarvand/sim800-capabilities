"""Compare two models field-by-field."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .loader import load_model
from .query import resolve_model


def _iter_leaves(node: Any, prefix: str = ""):
    if isinstance(node, dict):
        if "status" in node and "value" in node:
            yield prefix, node
            return
        for k, v in node.items():
            new_prefix = f"{prefix}.{k}" if prefix else k
            yield from _iter_leaves(v, new_prefix)


def compare(root: Path, model1: str, model2: str) -> List[Dict[str, Any]]:
    doc1 = resolve_model(root, model1)
    doc2 = resolve_model(root, model2)
    if doc1 is None:
        raise ValueError(f"model not found: {model1}")
    if doc2 is None:
        raise ValueError(f"model not found: {model2}")

    leaves1 = dict(_iter_leaves(doc1.get("capabilities", {}), "capabilities"))
    leaves2 = dict(_iter_leaves(doc2.get("capabilities", {}), "capabilities"))

    out: List[Dict[str, Any]] = []
    for path in sorted(set(leaves1) | set(leaves2)):
        f1 = leaves1.get(path)
        f2 = leaves2.get(path)
        if f1 is None:
            out.append({"field_path": path, "model1_value": None, "model2_value": {"value": f2["value"], "status": f2["status"]}, "diff_type": "missing_left"})
            continue
        if f2 is None:
            out.append({"field_path": path, "model1_value": {"value": f1["value"], "status": f1["status"]}, "model2_value": None, "diff_type": "missing_right"})
            continue
        t1 = (f1["value"], f1["status"])
        t2 = (f2["value"], f2["status"])
        if t1 == t2:
            dt = "same"
        elif f1["status"] == "conflict" or f2["status"] == "conflict":
            dt = "conflict"
        else:
            dt = "different"
        out.append({
            "field_path": path,
            "model1_value": {"value": f1["value"], "status": f1["status"]},
            "model2_value": {"value": f2["value"], "status": f2["status"]},
            "diff_type": dt,
        })
    return out