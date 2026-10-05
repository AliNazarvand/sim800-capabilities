"""Command-line interface for sim800-capabilities."""
from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from typing import Any, List

import yaml

from . import __version__
from .audit import audit, conflicts_report
from .compare import compare
from .generate import write_capabilities
from .cpp import render_from_root, write_cpp_header
from .loader import load_all_models
from .query import find, get_path, is_excluded, list_models, resolve_model
from .validator import validate

ROOT_DEFAULT = Path(__file__).resolve().parents[2]


def _print_yaml(obj: Any) -> None:
    sys.stdout.write(yaml.safe_dump(obj, sort_keys=False, allow_unicode=True, default_flow_style=False))


def _print_json(obj: Any) -> None:
    sys.stdout.write(json.dumps(obj, ensure_ascii=False, indent=2) + "\n")


def _emit(obj: Any, fmt: str) -> None:
    if fmt == "json":
        _print_json(obj)
    else:
        _print_yaml(obj)


def _iter_leaves(node: Any, prefix: str = "capabilities"):
    if isinstance(node, dict):
        if "status" in node and "value" in node:
            yield prefix, node
            return
        for k, v in node.items():
            yield from _iter_leaves(v, f"{prefix}.{k}")


def cmd_validate(args: Any, root: Path) -> int:
    try:
        errors = validate(root)
    except OSError as e:
        print(f"I/O error: {e}", file=sys.stderr)
        return 2
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print("OK")
    return 0


def cmd_list(args: Any, root: Path) -> int:
    _emit(list_models(root), args.format)
    return 0


def cmd_show(args: Any, root: Path) -> int:
    excluded = is_excluded(root, args.model)
    if excluded is not None:
        reason = excluded.get("reason") or ""
        print(f"model is out of scope: {args.model} ({reason})", file=sys.stderr)
        return 1
    doc = resolve_model(root, args.model)
    if doc is None:
        print(f"model not found: {args.model}", file=sys.stderr)
        return 1
    _emit(doc, args.format)
    return 0


def cmd_find(args: Any, root: Path) -> int:
    _emit(find(root, args.query), args.format)
    return 0


def cmd_get(args: Any, root: Path) -> int:
    doc = resolve_model(root, args.model)
    if doc is None:
        print(f"model not found: {args.model}", file=sys.stderr)
        return 1
    try:
        node = get_path(doc, args.path)
    except KeyError:
        print(f"path not found: {args.path}", file=sys.stderr)
        return 1
    if args.value_only:
        if isinstance(node, dict) and "value" in node:
            _emit(node["value"], args.format)
            return 0
        print("path is not a leaf FieldValue", file=sys.stderr)
        return 1
    _emit(node, args.format)
    return 0


def cmd_compare(args: Any, root: Path) -> int:
    try:
        rows = compare(root, args.model1, args.model2)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1
    _emit(rows, args.format)
    return 0


def cmd_export(args: Any, root: Path) -> int:
    fmt = args.format
    if fmt == "cpp":
        try:
            sys.stdout.write(render_from_root(root))
        except Exception as e:  # noqa: BLE001
            print(f"export cpp failed: {e}", file=sys.stderr)
            return 2
        return 0
    rows: List[dict] = []
    for doc in load_all_models(root):
        for path, fv in _iter_leaves(doc.get("capabilities", {})):
            ref = fv.get("source_ref") or {}
            rows.append({
                "model": doc["model"],
                "field_path": path,
                "value": _serialize_value(fv.get("value")),
                "status": fv.get("status"),
                "source_id": fv.get("source_id"),
                "source_ref.page": ref.get("page"),
                "source_ref.section": ref.get("section"),
                "source_ref.table": ref.get("table"),
                "source_ref.figure": ref.get("figure"),
                "confidence": fv.get("confidence"),
                "reason": fv.get("reason"),
                "notes": fv.get("notes"),
                "inference_source": fv.get("inference_source"),
                "inference_rule": fv.get("inference_rule"),
                "applicable_firmware": fv.get("applicable_firmware"),
            })
    if fmt == "csv":
        buf = io.StringIO()
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()) if rows else [])
        writer.writeheader()
        for r in rows:
            writer.writerow(r)
        sys.stdout.write(buf.getvalue())
    elif fmt == "json":
        _print_json(rows)
    else:
        _print_yaml(rows)
    return 0


def _serialize_value(v: Any) -> Any:
    if isinstance(v, (dict, list)):
        return json.dumps(v, ensure_ascii=False)
    return v


def cmd_generate(args: Any, root: Path) -> int:
    try:
        errors = validate(root)
    except OSError as e:
        print(f"I/O error: {e}", file=sys.stderr)
        return 2
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    target_kind = getattr(args, "target", "yaml")
    out_path = getattr(args, "out", None)
    if target_kind in ("yaml", "all"):
        try:
            target = write_capabilities(root)
        except Exception as e:  # noqa: BLE001
            print(f"generate yaml failed: {e}", file=sys.stderr)
            return 2
        print(f"wrote {target}")
    if target_kind in ("cpp", "all"):
        try:
            cpp_out = Path(out_path) if out_path else None
            target = write_cpp_header(root, cpp_out)
        except Exception as e:  # noqa: BLE001
            print(f"generate cpp failed: {e}", file=sys.stderr)
            return 2
        print(f"wrote {target}")
    return 0


def cmd_audit(args: Any, root: Path) -> int:
    _emit(audit(root, args.model), args.format)
    return 0


def cmd_conflicts(args: Any, root: Path) -> int:
    _emit(conflicts_report(root, args.model, args.unresolved_only), args.format)
    return 0


def build_parser():
    import argparse
    p = argparse.ArgumentParser(prog="sim800-capabilities")
    p.add_argument("--root", default=str(ROOT_DEFAULT))
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="command", required=True)

    sp = sub.add_parser("validate"); sp.set_defaults(func=cmd_validate)

    sp = sub.add_parser("list"); sp.add_argument("--format", choices=["yaml", "json"], default="yaml"); sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show"); sp.add_argument("model"); sp.add_argument("--format", choices=["yaml", "json"], default="yaml"); sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("find"); sp.add_argument("query"); sp.add_argument("--format", choices=["yaml", "json"], default="yaml"); sp.set_defaults(func=cmd_find)

    sp = sub.add_parser("get"); sp.add_argument("model"); sp.add_argument("path"); sp.add_argument("--value-only", action="store_true"); sp.add_argument("--format", choices=["yaml", "json"], default="yaml"); sp.set_defaults(func=cmd_get)

    sp = sub.add_parser("compare"); sp.add_argument("model1"); sp.add_argument("model2"); sp.add_argument("--format", choices=["yaml", "json"], default="yaml"); sp.set_defaults(func=cmd_compare)

    sp = sub.add_parser("export"); sp.add_argument("--format", choices=["yaml", "json", "csv", "cpp"], default="yaml"); sp.set_defaults(func=cmd_export)

    sp = sub.add_parser("generate"); sp.add_argument("--target", choices=["yaml", "cpp", "all"], default="yaml"); sp.add_argument("--out", default=None); sp.set_defaults(func=cmd_generate)

    sp = sub.add_parser("audit"); sp.add_argument("--model", default=None); sp.add_argument("--format", choices=["yaml", "json"], default="yaml"); sp.set_defaults(func=cmd_audit)

    sp = sub.add_parser("conflicts"); sp.add_argument("--model", default=None); sp.add_argument("--unresolved-only", action="store_true"); sp.add_argument("--format", choices=["yaml", "json"], default="yaml"); sp.set_defaults(func=cmd_conflicts)

    return p


def main(argv: List[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    try:
        return args.func(args, root)
    except KeyboardInterrupt:
        return 2


if __name__ == "__main__":
    sys.exit(main())