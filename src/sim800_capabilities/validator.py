"""Schema + cross-file validation for the capability database."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

import jsonschema

from .loader import (
    load_all_models,
    load_out_of_scope,
    load_scope,
    load_sources,
)

INFERENCE_RULE_RE = re.compile(r"^[a-z_]+:\s*.+$")


# Enum tables ------------------------------------------------------------
ENUM_TABLES: Dict[str, List[Any]] = {
    "bands.type": ["quad-band", "dual-band", "tri-band", "penta-band", "single-band", "other"],
    "gprs.device_class": ["A", "B", "C"],
    "bluetooth.version": ["1.1", "2.0", "2.1", "3.0", "4.0", "4.1", "4.2", "5.0", "other"],
    "pcm.mode": ["master", "slave", "both", "other"],
    "usb.version": ["1.1", "2.0", "3.0", "other"],
    "usb.speed": ["low-speed", "full-speed", "high-speed", "super-speed", "other"],
    "usb.connector": ["micro", "mini", "type-c", "other", "none"],
    "uart_serial.flow_control": ["none", "hardware", "software", "both", "other"],
    "gnss.antenna_interface": ["active", "passive", "none", "other"],
}

# Conditional required sub-fields when supported.value == true ------------
SUPPORTED_REQUIRED: Dict[str, List[str]] = {
    "bluetooth": ["version", "profiles"],
    "pcm": ["channels", "mode"],
    "usb": ["version", "speed"],
    "gnss": ["constellations", "channels"],
}


def _load_schema(root: Path, name: str) -> Dict[str, Any]:
    import json
    with (Path(root) / "schema" / name).open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", str(s).replace("-", "_")).strip().lower()


def validate(root: Path) -> List[str]:
    """Return list of errors. Empty list means valid."""
    errors: List[str] = []
    root = Path(root)

    # --- sources ---
    sources_doc = load_sources(root)
    try:
        jsonschema.validate(sources_doc, _load_schema(root, "sources.schema.json"))
    except jsonschema.ValidationError as e:
        errors.append(f"sources.yaml schema error: {e.message}")

    # --- scope ---
    scope = load_scope(root)
    try:
        jsonschema.validate(scope, _load_schema(root, "scope.schema.json"))
    except jsonschema.ValidationError as e:
        errors.append(f"scope.yaml schema error: {e.message}")

    # --- out-of-scope ---
    oos = load_out_of_scope(root)
    try:
        jsonschema.validate(oos, _load_schema(root, "out-of-scope.schema.json"))
    except jsonschema.ValidationError as e:
        errors.append(f"out-of-scope.yaml schema error: {e.message}")

    models_scope = list(scope.get("models", []))
    family_map = scope.get("family_map", {})
    in_scope_caps = set(scope.get("in_scope_capabilities", []))
    out_of_scope_caps = set(scope.get("out_of_scope_capabilities", []))

    if in_scope_caps & out_of_scope_caps:
        errors.append("in_scope_capabilities and out_of_scope_capabilities overlap")

    for entry in scope.get("excluded_models", []) or []:
        if entry.get("model") in models_scope:
            errors.append(f"excluded model {entry.get('model')} also in models list")

    for m in models_scope:
        if m not in family_map:
            errors.append(f"family_map missing model {m}")

    # sources cross-check
    sources_by_id = {s["id"]: s for s in sources_doc.get("sources", [])}
    for s in sources_doc.get("sources", []):
        if s["tier"] == "secondary" and s["doc_type"] == "hardware_design":
            errors.append(f"source {s['id']}: secondary tier cannot be hardware_design")
        if s["tier"] == "primary" and s["doc_type"] == "at_command_manual":
            errors.append(f"source {s['id']}: primary tier cannot be at_command_manual")
        if s["local_path"] and not s["sha256"]:
            errors.append(f"source {s['id']}: local_path requires sha256")
        if not s["url_pinned"] and not s["local_path"]:
            errors.append(f"source {s['id']}: need url_pinned or local_path")
        ov = set(s["applicable_models"]) & set(s["not_applicable_models"])
        if ov:
            errors.append(f"source {s['id']}: applicable/not_applicable overlap: {ov}")
        for m in s["applicable_models"] + s["not_applicable_models"]:
            if m not in models_scope:
                errors.append(f"source {s['id']}: model {m} not in scope.models")

    # --- models ---
    cap_schema = _load_schema(root, "capability.schema.json")
    seen_models = set()
    seen_aliases: Dict[str, str] = {}

    for model_doc in load_all_models(root):
        model_name = model_doc.get("model")
        if model_name in seen_models:
            errors.append(f"duplicate model {model_name}")
        seen_models.add(model_name)

        try:
            jsonschema.validate(model_doc, cap_schema)
        except jsonschema.ValidationError as e:
            errors.append(f"model {model_name}: schema error at {list(e.absolute_path)}: {e.message}")
            continue

        for alias in model_doc.get("aliases", []):
            key = _norm(alias)
            if key in seen_aliases:
                errors.append(f"duplicate alias '{alias}' between {seen_aliases[key]} and {model_name}")
            seen_aliases[key] = model_name

        if family_map.get(model_name) != model_doc.get("family"):
            errors.append(f"model {model_name}: family mismatch with scope.family_map")

        # FieldValue rules
        for path, fv in _iter_field_values(model_doc.get("capabilities", {})):
            errors.extend(_check_field_value(model_name, path, fv, sources_by_id))

        # conditional supported.value == true requirements
        errors.extend(_check_supported_requirements(model_name, model_doc))

        # Conflict sync
        errors.extend(_check_conflicts(model_name, model_doc))

    # scope vs models
    for m in models_scope:
        if m not in seen_models:
            errors.append(f"model {m} in scope but file missing")

    return errors


def _iter_field_values(node: Any, prefix: str = "capabilities"):
    if isinstance(node, dict):
        if "status" in node and "value" in node:
            yield prefix, node
            return
        for k, v in node.items():
            yield from _iter_field_values(v, f"{prefix}.{k}")


def _rel_path(path: str) -> str:
    if path.startswith("capabilities."):
        return path[len("capabilities."):]
    return path


def _check_field_value(model: str, path: str, fv: Dict[str, Any], sources_by_id: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    status = fv.get("status")
    value = fv.get("value")
    conf = fv.get("confidence")

    if status is None:
        errs.append(f"{model}:{path}: missing status")
        return errs

    if value is None and status not in {"not_documented", "not_supported", "not_in_scope", "inferred", "conflict"}:
        errs.append(f"{model}:{path}: value=null not allowed with status={status}")

    if conf is None and status != "not_in_scope":
        errs.append(f"{model}:{path}: confidence=null only allowed for not_in_scope")

    if status == "inferred":
        if not fv.get("inference_source") or not fv.get("inference_rule"):
            errs.append(f"{model}:{path}: inferred requires inference_source and inference_rule")
        rule = fv.get("inference_rule") or ""
        if rule and not INFERENCE_RULE_RE.match(rule):
            errs.append(f"{model}:{path}: inference_rule regex mismatch")
        if fv.get("applicable_firmware"):
            errs.append(f"{model}:{path}: inferred + applicable_firmware forbidden")

    if status == "not_documented" and fv.get("applicable_firmware"):
        errs.append(f"{model}:{path}: not_documented + applicable_firmware forbidden")

    if fv.get("applicable_firmware") and not fv.get("notes"):
        errs.append(f"{model}:{path}: applicable_firmware requires notes")

    if status == "conflict" and not fv.get("reason"):
        errs.append(f"{model}:{path}: conflict requires reason")

    if status == "not_in_scope" and not fv.get("reason"):
        errs.append(f"{model}:{path}: not_in_scope requires reason")

    sid = fv.get("source_id")
    if sid and sid not in sources_by_id:
        errs.append(f"{model}:{path}: source_id {sid} not in sources.yaml")

    inf_src = fv.get("inference_source")
    if inf_src and inf_src != "logical_rule" and inf_src not in sources_by_id:
        errs.append(f"{model}:{path}: inference_source {inf_src} not found")

    # Enum checks on documented values
    rel = _rel_path(path)
    if rel in ENUM_TABLES and status == "documented" and value is not None:
        allowed = {str(x) for x in ENUM_TABLES[rel]}
        if str(value) not in allowed:
            errs.append(f"{model}:{path}: value {value!r} not in enum {ENUM_TABLES[rel]}")

    return errs


def _check_supported_requirements(model: str, doc: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    caps = doc.get("capabilities", {}) or {}
    for cap_name, req_fields in SUPPORTED_REQUIRED.items():
        cap = caps.get(cap_name)
        if not isinstance(cap, dict):
            continue
        supported = cap.get("supported")
        if not isinstance(supported, dict):
            continue
        if supported.get("value") is True:
            for rf in req_fields:
                node = cap.get(rf)
                if not isinstance(node, dict):
                    errs.append(f"{model}:capabilities.{cap_name}.{rf}: required when supported.value is true")
                    continue
                if node.get("value") is None and node.get("status") not in {"not_supported", "not_documented", "not_in_scope", "conflict", "inferred"}:
                    errs.append(f"{model}:capabilities.{cap_name}.{rf}: value required when supported.value is true")
    return errs


def _check_conflicts(model: str, doc: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    conflicts = (doc.get("metadata") or {}).get("conflicts") or []

    seen_ids = set()
    for c in conflicts:
        cid = c.get("id")
        if cid in seen_ids:
            errs.append(f"{model}: duplicate conflict id {cid}")
        seen_ids.add(cid)

    conflict_fields = set()
    for path, fv in _iter_field_values(doc.get("capabilities", {})):
        if fv.get("status") == "conflict":
            conflict_fields.add(path)

    record_paths = {c.get("field_path") for c in conflicts}
    record_paths_base = {p[:-6] if p and p.endswith(".value") else p for p in record_paths}

    for p in conflict_fields:
        if p not in record_paths and p not in record_paths_base:
            errs.append(f"{model}:{p}: status=conflict but no matching metadata.conflicts record")

    conflict_base_paths = {p[:-6] if p.endswith(".value") else p for p in conflict_fields}
    for c in conflicts:
        if c.get("resolution") == "unresolved":
            fp = c.get("field_path") or ""
            fp_base = fp[:-6] if fp.endswith(".value") else fp
            if fp_base not in conflict_base_paths:
                errs.append(f"{model}: unresolved conflict {c.get('id')} for field {fp} has no status=conflict field")

    return errs