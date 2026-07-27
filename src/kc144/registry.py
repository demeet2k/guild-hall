from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from .model import ACTIVE_EPOCH, Seat


def load_atlas(path: str | Path) -> list[Seat]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    epoch = data["atlas_epoch"]
    return [
        Seat(
            gid=item["gid"],
            row=item["row"],
            col=item["col"],
            block=item["block"],
            station=item["station"],
            title=item["title"],
            epoch=epoch,
            status=item.get("status", "FROZEN"),
            aliases=tuple(item.get("aliases", [])),
            metadata=item.get("metadata"),
        )
        for item in data["seats"]
    ]


def by_gid(seats: Iterable[Seat], gid: int) -> Seat:
    matches = [seat for seat in seats if seat.gid == gid]
    if len(matches) != 1:
        raise LookupError(f"expected one seat for GID{gid:03d}; found {len(matches)}")
    return matches[0]


def default_atlas_path() -> Path:
    return Path(__file__).resolve().parents[2] / "registry" / "atlas.json"


def load_default_atlas() -> list[Seat]:
    seats = load_atlas(default_atlas_path())
    if seats and seats[0].epoch != ACTIVE_EPOCH:
        raise ValueError("default atlas is not the active epoch")
    return seats

