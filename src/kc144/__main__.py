from __future__ import annotations

import argparse
import json
from pathlib import Path

from .model import ACTIVE_EPOCH, LEGACY_EPOCH, gid_to_grid
from .registry import by_gid, load_atlas
from .validate import validate_atlas_file


def main() -> int:
    parser = argparse.ArgumentParser(prog="kc144")
    sub = parser.add_subparsers(dest="command", required=True)

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("atlas")

    p_resolve = sub.add_parser("resolve")
    p_resolve.add_argument("gid", type=int)
    p_resolve.add_argument("--epoch", default=ACTIVE_EPOCH)
    p_resolve.add_argument("--atlas", default="registry/atlas.json")

    args = parser.parse_args()
    if args.command == "validate":
        errors = validate_atlas_file(args.atlas)
        if errors:
            print(json.dumps({"status": "FAIL", "errors": errors}, indent=2))
            return 1
        print(json.dumps({"status": "PASS", "atlas": args.atlas}, indent=2))
        return 0

    if args.epoch == ACTIVE_EPOCH:
        seat = by_gid(load_atlas(args.atlas), args.gid)
        print(
            json.dumps(
                {
                    "epoch": seat.epoch,
                    "gid": seat.gid,
                    "grid": seat.grid,
                    "block": seat.block,
                    "station": seat.station,
                    "title": seat.title,
                    "lookup_key": seat.lookup_key,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if args.epoch == LEGACY_EPOCH:
        row, col = gid_to_grid(args.gid)
        print(
            json.dumps(
                {
                    "epoch": LEGACY_EPOCH,
                    "gid": args.gid,
                    "grid": f"R{row:02d}C{col:02d}",
                    "status": "USE registry/epochs.json CROSSWALK",
                },
                indent=2,
            )
        )
        return 0

    raise SystemExit(f"unknown epoch: {args.epoch}")


if __name__ == "__main__":
    raise SystemExit(main())

