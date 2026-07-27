from __future__ import annotations

import hashlib
import json
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

from .model import ACTIVE_EPOCH, gid_to_grid, grid_to_gid

STRUCTURAL_STATES = {"OK", "NEAR", "AMBIG", "FAIL"}
CLAIM_VERDICTS = {"PASS", "FAIL", "UNKNOWN", "OUT_OF_SCOPE"}
RETURN_CLASSES = {
    "EXACT",
    "PARTIAL",
    "LOSSY",
    "MULTIVALUED",
    "CONDITIONAL",
    "COMPENSATING",
    "MODEL",
    "ONE_WAY",
    "OBSTRUCTED",
}


def canonical_json(value: Any) -> str:
    normalized = _normalize(value)
    return json.dumps(
        normalized,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _normalize(value: Any) -> Any:
    if isinstance(value, str):
        return unicodedata.normalize("NFC", value)
    if isinstance(value, list):
        return [_normalize(x) for x in value]
    if isinstance(value, dict):
        return {
            unicodedata.normalize("NFC", str(k)): _normalize(v)
            for k, v in value.items()
        }
    return value


def validate_atlas_document(doc: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if doc.get("atlas_epoch") != ACTIVE_EPOCH:
        errors.append("atlas_epoch is not the active epoch")
    seats = doc.get("seats")
    if not isinstance(seats, list):
        return errors + ["seats must be an array"]
    if len(seats) != 144:
        errors.append(f"expected 144 seats; found {len(seats)}")

    gids = Counter(item.get("gid") for item in seats if isinstance(item, dict))
    duplicates = sorted(gid for gid, count in gids.items() if count > 1)
    if duplicates:
        errors.append(f"duplicate gids: {duplicates}")
    missing = sorted(set(range(1, 145)) - set(gids))
    if missing:
        errors.append(f"missing gids: {missing}")

    for item in seats:
        if not isinstance(item, dict):
            errors.append("seat is not an object")
            continue
        gid = item.get("gid")
        try:
            row, col = gid_to_grid(gid)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        if item.get("row") != row or item.get("col") != col:
            errors.append(f"GID{gid:03d} has incorrect row/col")
        if grid_to_gid(row, col) != gid:
            errors.append(f"GID{gid:03d} failed grid round trip")
        for key in ("block", "station", "title"):
            if not isinstance(item.get(key), str) or not item[key].strip():
                errors.append(f"GID{gid:03d} missing {key}")
    return errors


def validate_atlas_file(path: str | Path) -> list[str]:
    return validate_atlas_document(json.loads(Path(path).read_text(encoding="utf-8")))


def validate_route(route: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required = {
        "route_id",
        "source",
        "target",
        "edge_type",
        "source_carrier",
        "target_carrier",
        "corridor",
        "preserved_invariants",
        "defect",
        "return_class",
        "witness",
    }
    for key in sorted(required - set(route)):
        errors.append(f"missing route field: {key}")
    if route.get("return_class") not in RETURN_CLASSES:
        errors.append("invalid return_class")
    if route.get("return_class") == "ONE_WAY" and not route.get("irreversibility_witness"):
        errors.append("ONE_WAY route requires irreversibility_witness")
    if route.get("return_class") not in {"ONE_WAY", "OBSTRUCTED"} and not route.get("return"):
        errors.append("route requires return map/contract")
    return errors
