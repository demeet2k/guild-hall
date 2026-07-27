from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class Seat:
    gid: int
    grid: str
    band: str
    station: str
    structural_role: str
    evidence_status: str
    coordinates: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, order=True)
class Edge:
    source: int
    target: int
    edge_class: str
    semantics: str

    def __post_init__(self) -> None:
        if self.source >= self.target:
            raise ValueError("edges must be stored in canonical source < target order")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TransformReceipt:
    transform: str
    source_gid: int
    target_gid: int
    identity_effect: str
    truth_effect: str = "NONE"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
