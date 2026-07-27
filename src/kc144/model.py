from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

ACTIVE_EPOCH = "EPOCH-B-EIGHT-BLOCK"
LEGACY_EPOCH = "EPOCH-A-EXPLICIT-DUPLEX"


class Block(str, Enum):
    H6 = "H6"
    X16 = "X16"
    BR21 = "BR21"
    F37 = "F37"
    IC10 = "IC10"
    KC15 = "KC15"
    KC27 = "KC27"
    SSN12 = "SSN12"
    KC27_PLUS = "KC27+"
    KC27_STAR = "KC27*"


@dataclass(frozen=True)
class Seat:
    gid: int
    row: int
    col: int
    block: str
    station: str
    title: str
    epoch: str = ACTIVE_EPOCH
    status: str = "FROZEN"
    aliases: tuple[str, ...] = ()
    metadata: dict[str, Any] | None = None

    @property
    def grid(self) -> str:
        return f"R{self.row:02d}C{self.col:02d}"

    @property
    def lookup_key(self) -> str:
        return f"KC144.V1::GID{self.gid:03d}::{self.station}"


def gid_to_grid(gid: int) -> tuple[int, int]:
    if not isinstance(gid, int) or isinstance(gid, bool) or not 1 <= gid <= 144:
        raise ValueError("gid must be an integer in [1, 144]")
    return (gid - 1) // 12 + 1, (gid - 1) % 12 + 1


def grid_to_gid(row: int, col: int) -> int:
    if not all(isinstance(x, int) and not isinstance(x, bool) for x in (row, col)):
        raise ValueError("row and col must be integers")
    if not 1 <= row <= 12 or not 1 <= col <= 12:
        raise ValueError("row and col must be in [1, 12]")
    return 12 * (row - 1) + col


def kc27_coordinate(p: int) -> tuple[int, int, int]:
    if not isinstance(p, int) or isinstance(p, bool) or not 0 <= p <= 26:
        raise ValueError("KC27 index must be an integer in [0, 26]")
    return p // 9, (p % 9) // 3, p % 3

