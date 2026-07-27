from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from .canonical import content_hash, utc_now


class GateVerdict(str, Enum):
    PASS = "PASS"
    NEAR = "NEAR"
    HOLD = "HOLD"
    FAIL = "FAIL"


class AdmissionClass(str, Enum):
    FULL = "FULL"
    LIMITED = "LIMITED"
    DEFERRED = "DEFERRED"
    QUARANTINED = "QUARANTINED"
    REFUSED = "REFUSED"


class RepairStatus(str, Enum):
    OPEN = "OPEN"
    SCHEDULED = "SCHEDULED"
    EXECUTED = "EXECUTED"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"


class RoundTripClass(str, Enum):
    EXACT = "EXACT"
    LAW_EQUIV = "LAW_EQUIV"
    RESIDUALIZED = "RESIDUALIZED"
    ILLEGAL = "ILLEGAL"


class Role(str, Enum):
    PROPOSER = "PROPOSER"
    SKEPTIC = "SKEPTIC"
    INTEGRATOR = "INTEGRATOR"
    IMMUNE_STEWARD = "IMMUNE_STEWARD"
    REPLAY_AUDITOR = "REPLAY_AUDITOR"
    META_OBSERVER = "META_OBSERVER"


TRUST_DIMENSIONS = (
    "epistemic",
    "procedural",
    "replay",
    "boundary",
    "correction",
    "relational",
)


@dataclass(slots=True)
class GateResult:
    gate_id: str
    verdict: GateVerdict
    reason_codes: list[str]
    witness_refs: list[str] = field(default_factory=list)
    residual_refs: list[str] = field(default_factory=list)
    required_repairs: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class RepairItem:
    repair_id: str
    contradiction_id: str
    residual_code: str
    damaged_layer: str
    required_operation: str
    required_witnesses: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    propagation_radius: int = 0
    severity: float = 0.0
    harm_sensitive: bool = False
    replay_blocking: bool = False
    reversible: bool = True
    assigned_role: str = Role.INTEGRATOR.value
    status: RepairStatus = RepairStatus.OPEN
    created_at: str = field(default_factory=utc_now)

    @property
    def priority_vector(self) -> tuple[int, int, int, int, float, str]:
        return (
            int(bool(self.blockers)),
            int(self.harm_sensitive),
            int(self.replay_blocking),
            self.propagation_radius,
            self.severity,
            self.created_at,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TrustVector:
    epistemic: float = 0.5
    procedural: float = 0.5
    replay: float = 0.5
    boundary: float = 0.5
    correction: float = 0.5
    relational: float = 0.5

    def __post_init__(self) -> None:
        for name in TRUST_DIMENSIONS:
            value = getattr(self, name)
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1], got {value}")

    def to_dict(self) -> dict[str, float]:
        return {name: getattr(self, name) for name in TRUST_DIMENSIONS}

    @classmethod
    def from_dict(cls, values: dict[str, float]) -> "TrustVector":
        return cls(**{name: float(values.get(name, 0.5)) for name in TRUST_DIMENSIONS})


@dataclass(slots=True)
class TrustEvidence:
    outcome: dict[str, float]
    witness_refs: dict[str, list[str]]
    eta: float = 0.5

    def __post_init__(self) -> None:
        if not 0.0 <= self.eta <= 1.0:
            raise ValueError("eta must be in [0, 1]")
        unknown = set(self.outcome) - set(TRUST_DIMENSIONS)
        if unknown:
            raise ValueError(f"unknown trust dimensions: {sorted(unknown)}")
        for name, value in self.outcome.items():
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"outcome {name} must be in [0, 1]")


@dataclass(slots=True)
class RoleAssignments:
    proposer: str
    skeptic: str
    integrator: str
    immune_steward: str
    replay_auditor: str
    meta_observer: str

    def separation_errors(self) -> list[str]:
        errors: list[str] = []
        if self.proposer == self.replay_auditor:
            errors.append("PROPOSER_EQUALS_REPLAY_AUDITOR")
        if self.proposer == self.immune_steward:
            errors.append("PROPOSER_EQUALS_IMMUNE_STEWARD")
        if self.integrator == self.replay_auditor:
            errors.append("INTEGRATOR_EQUALS_REPLAY_AUDITOR")
        return errors


@dataclass(slots=True)
class CycleResult:
    cycle_id: str
    contradiction_packet: dict[str, Any]
    repair_plan: dict[str, Any]
    trust_revision: dict[str, Any]
    gate_results: list[GateResult]
    reentry_permit: dict[str, Any]
    successor_seed: dict[str, Any] | None
    replay_certificate: dict[str, Any] | None
    kc54_receipt: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "contradiction_packet": self.contradiction_packet,
            "repair_plan": self.repair_plan,
            "trust_revision": self.trust_revision,
            "gate_results": [gate.to_dict() for gate in self.gate_results],
            "reentry_permit": self.reentry_permit,
            "successor_seed": self.successor_seed,
            "replay_certificate": self.replay_certificate,
            "kc54_receipt": self.kc54_receipt,
        }


def seal_packet(packet: dict[str, Any]) -> dict[str, Any]:
    sealed = dict(packet)
    sealed["packet_hash"] = content_hash(sealed)
    return sealed

