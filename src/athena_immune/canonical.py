from __future__ import annotations

import dataclasses
import hashlib
import json
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Iterable


def _jsonable(value: Any) -> Any:
    if dataclasses.is_dataclass(value):
        return {field.name: _jsonable(getattr(value, field.name)) for field in dataclasses.fields(value)}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, set):
        return sorted((_jsonable(item) for item in value), key=canonical_dumps)
    return value


def canonical_data(value: Any, *, omit: Iterable[str] = ()) -> Any:
    data = _jsonable(value)
    if isinstance(data, dict):
        for key in omit:
            data.pop(key, None)
    return data


def canonical_dumps(value: Any) -> str:
    return json.dumps(
        _jsonable(value),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def sha256_hex(value: Any) -> str:
    raw = value if isinstance(value, bytes) else canonical_dumps(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def content_hash(value: Any, *, omit: Iterable[str] = ("packet_hash",)) -> str:
    return sha256_hex(canonical_data(value, omit=omit))


def utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def merkle_root(items: Iterable[str]) -> str:
    leaves = [sha256_hex({"leaf": item}) for item in sorted(items)]
    if not leaves:
        return sha256_hex({"empty": True})
    while len(leaves) > 1:
        if len(leaves) % 2:
            leaves.append(leaves[-1])
        leaves = [
            sha256_hex({"left": leaves[index], "right": leaves[index + 1]})
            for index in range(0, len(leaves), 2)
        ]
    return leaves[0]

