from __future__ import annotations

import argparse
import json
from pathlib import Path

from .core import compile_route, validate_registry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="athena-git-brain")
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("validate")
    route = sub.add_parser("route")
    route.add_argument("source")
    route.add_argument("target")
    args = parser.parse_args(argv)

    if args.command == "validate":
        result = validate_registry(args.root)
    else:
        result = compile_route(args.root, args.source, args.target)
    print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False))
    return 0 if result.get("status") == "PASS" or result.get("verdict") in {
        "FOUND",
        "PARTIAL",
    } else 1

