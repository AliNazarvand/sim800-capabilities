"""Audit report over the capability database."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from .loader import load_all_models


def _iter_field_values(node: Any, prefix: str = "capabilities"):
    if isinstance(node, dict):
        if "status" in node and "value" in node:
            yield prefix, node
            return
        for k, v in node.items():
            yield from _iter_field_values(v, f"{prefix}.{k}")


def audit(root: Path, model_filter: str | None = None) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for doc in load_all_models(root):
        if model_filter and doc["model"] != model_filter:
            continue
        for path, fv in _iter_field_values(doc.get("capabilities", {})):
            rows.append({
                "model": doc["model"],
                "field_path": path,
                "status": fv.get("status"),
                "confidence": fv.get("confidence"),
                "source_id": fv.get("source_id"),
                "inference_source": fv.get("inference_source"),
                "reason": fv.get("reason"),
            })
    return rows


def conflicts_report(root: Path, model_filter: str | None = None, unresolved_only: bool = False) -> List[Dict[str, Any]]:
    import json
    out: List[Dict[str, Any]] = []
    for doc in load_all_models(root):
        if model_filter and doc["model"] != model_filter:
            continue
        for c in doc.get("metadata", {}).get("conflicts", []) or []:
            if unresolved_only and c.get("resolution") != "unresolved":
                continue
            ov = c.get("old_value")
            nv = c.get("new_value")
            if isinstance(ov, (dict, list)):
                ov = json.dumps(ov, ensure_ascii=False)
            if isinstance(nv, (dict, list)):
                nv = json.dumps(nv, ensure_ascii=False)
            out.append({
                "model": doc["model"],
                "id": c.get("id"),
                "field_path": c.get("field_path"),
                "old_value": ov,
                "new_value": nv,
                "old_source_id": c.get("old_source_id"),
                "new_source_id": c.get("new_source_id"),
                "resolution": c.get("resolution"),
                "chosen_source_id": c.get("chosen_source_id"),
                "reason": c.get("reason"),
            })
    return out