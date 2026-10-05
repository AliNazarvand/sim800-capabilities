"""Generate capabilities.yaml from models + sources."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import yaml

from .loader import (
    compute_content_hash,
    compute_scope_hash,
    load_all_models,
    load_scope,
    load_sources,
)
from .validator import validate


# Ordering rules ----------------------------------------------------------
_CODING_SCHEMES_ORDER = ["CS1", "CS2", "CS3", "CS4"]
_GNSS_PROTOCOLS_ORDER = ["NMEA", "PMTK", "other"]
_BT_PROFILES_ORDER = ["SPP", "HFP", "HSP", "A2DP", "AVRCP", "PBAP", "other"]
_CONSUMPTION_MODE_ORDER = [
    "idle", "sleep", "transmit", "psm", "edrx", "paging",
    "connected", "data_transfer", "registered", "other",
]


def _order_list(values, order):
    if not isinstance(values, list):
        return values
    idx = {v: i for i, v in enumerate(order)}
    return sorted(values, key=lambda v: (idx.get(v, len(order)), str(v)))


def _canonicalize_field_value(path: str, fv: Any) -> Any:
    if not isinstance(fv, dict) or "value" not in fv:
        return fv
    v = fv["value"]
    if path.endswith("bands.gsm") or path.endswith("bands.gprs"):
        if isinstance(v, list):
            fv["value"] = sorted(v)
    elif path.endswith("gprs.coding_schemes"):
        fv["value"] = _order_list(v, _CODING_SCHEMES_ORDER)
    elif path.endswith("gnss.protocols"):
        fv["value"] = _order_list(v, _GNSS_PROTOCOLS_ORDER)
    elif path.endswith("bluetooth.profiles"):
        fv["value"] = _order_list(v, _BT_PROFILES_ORDER)
    elif path.endswith("power.current_consumption"):
        if isinstance(v, list):
            fv["value"] = sorted(
                v,
                key=lambda r: (
                    _CONSUMPTION_MODE_ORDER.index(r.get("mode"))
                    if isinstance(r, dict) and r.get("mode") in _CONSUMPTION_MODE_ORDER
                    else len(_CONSUMPTION_MODE_ORDER),
                    str(r.get("conditions") or "") if isinstance(r, dict) else "",
                ),
            )
    return fv


def _walk_canonicalize(node: Any, prefix: str) -> None:
    if isinstance(node, dict):
        if "status" in node and "value" in node:
            _canonicalize_field_value(prefix, node)
            return
        for k, v in node.items():
            _walk_canonicalize(v, f"{prefix}.{k}" if prefix else k)


def _canonicalize_model(model: Dict[str, Any]) -> Dict[str, Any]:
    _walk_canonicalize(model.get("capabilities", {}), "capabilities")
    meta = model.setdefault("metadata", {})
    conflicts = meta.get("conflicts") or []
    meta["conflicts"] = sorted(conflicts, key=lambda c: c.get("id", ""))
    return model


def generate(root: Path) -> Dict[str, Any]:
    root = Path(root)
    errors = validate(root)
    if errors:
        raise ValueError("validation failed:\n" + "\n".join(errors))

    scope = load_scope(root)
    sources = load_sources(root)["sources"]
    models = [_canonicalize_model(m) for m in load_all_models(root)]

    content_hash = compute_content_hash(models, sources)
    scope_hash = compute_scope_hash(scope)

    return {
        "generated": True,
        "content_hash": content_hash,
        "scope_hash": scope_hash,
        "models": models,
    }


def write_capabilities(root: Path) -> Path:
    root = Path(root)
    doc = generate(root)
    target = root / "data" / "capabilities.yaml"
    with target.open("w", encoding="utf-8", newline="\n") as fh:
        yaml.safe_dump(doc, fh, sort_keys=False, allow_unicode=True, default_flow_style=False)
    return target