from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from .navigation import DECLARED_BRIDGES, adjacency, navigation_relations
from .population import digest


@dataclass(frozen=True)
class WitnessAttestation:
    witness_id: str
    evidence_root: str
    author_id: str
    verifier_id: str
    replay_class: str
    signature_status: str
    authority: bool

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "WitnessAttestation":
        return cls(**dict(value))


@dataclass(frozen=True)
class BridgeWitnessPacket:
    packet_id: str
    bridge_id: str
    source: int
    target: int
    transport: str
    preserved_invariants: tuple[str, ...]
    declared_loss: str
    corridor: str
    return_path: tuple[int, ...]
    attestations: tuple[WitnessAttestation, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BridgeWitnessPacket":
        data = dict(value)
        data["preserved_invariants"] = tuple(data.get("preserved_invariants", ()))
        data["return_path"] = tuple(data.get("return_path", ()))
        data["attestations"] = tuple(
            WitnessAttestation.from_dict(row) for row in data.get("attestations", ())
        )
        return cls(**data)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def bridge_witness_contract() -> dict[str, Any]:
    return {
        "schema": "KC144.BridgeWitnessContract.V4",
        "notation": (
            "beta_ij=<F_i,F_j,T_ij,K_preserved,Delta_ij,R_ji,W_ij>"
        ),
        "required_replay_classes": ["B3", "B4"],
        "required_signature_status": "VERIFIED",
        "laws": [
            "adjacency does not certify transport",
            "returnability is checked on the declared graph",
            "the verifier must be distinct from the author",
            "bridge certification has no station-promotion effect",
            "test fixtures never enter the production witness ledger",
        ],
    }


def evaluate_bridge_witness(packet: BridgeWitnessPacket) -> dict[str, Any]:
    bridge_by_id = {bridge.bridge_id: bridge for bridge in DECLARED_BRIDGES}
    declared = bridge_by_id.get(packet.bridge_id)
    graph = adjacency(navigation_relations())
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: str) -> None:
        checks.append(
            {"check": name, "verdict": "PASS" if passed else "FAIL", "detail": detail}
        )

    check(
        "DECLARED_BRIDGE",
        declared is not None,
        "bridge_id must resolve in the frozen 28-bridge registry",
    )
    identity_match = bool(
        declared
        and packet.source == declared.source
        and packet.target == declared.target
    )
    check(
        "ENDPOINT_IDENTITY",
        identity_match,
        "packet endpoints must exactly match the declared bridge",
    )
    check("TYPED_TRANSPORT", bool(packet.transport.strip()), "T_ij must be declared")
    check(
        "PRESERVED_INVARIANTS",
        bool(packet.preserved_invariants)
        and all(item.strip() for item in packet.preserved_invariants),
        "K_preserved must contain at least one exact invariant",
    )
    check(
        "DECLARED_LOSS",
        bool(packet.declared_loss.strip()),
        "Delta_ij must be explicit, including an explicit NONE",
    )
    check("CORRIDOR", bool(packet.corridor.strip()), "the validity corridor is required")
    return_endpoints = bool(
        packet.return_path
        and packet.return_path[0] == packet.target
        and packet.return_path[-1] == packet.source
    )
    check(
        "RETURN_ENDPOINTS",
        return_endpoints,
        "R_ji must begin at target and terminate at source",
    )
    return_traversable = bool(
        return_endpoints
        and all(
            right in graph[left]
            for left, right in zip(packet.return_path, packet.return_path[1:])
        )
    )
    check(
        "RETURN_TRAVERSABLE",
        return_traversable,
        "every R_ji segment must exist in the declared graph",
    )
    independent = [
        attestation
        for attestation in packet.attestations
        if attestation.author_id != attestation.verifier_id
        and attestation.replay_class in {"B3", "B4"}
        and attestation.signature_status == "VERIFIED"
        and attestation.authority
        and bool(attestation.evidence_root.strip())
    ]
    check(
        "INDEPENDENT_WITNESS",
        bool(independent),
        "W_ij needs an authoritative B3/B4 signed verifier distinct from the author",
    )
    roots = [attestation.evidence_root for attestation in packet.attestations]
    unique_roots = bool(roots) and len(roots) == len(set(roots))
    check(
        "EVIDENCE_ROOT_IDENTITY",
        unique_roots,
        "attestations may not duplicate an evidence root",
    )

    verdict = "CERTIFIED" if all(row["verdict"] == "PASS" for row in checks) else "HOLD"
    report = {
        "schema": "KC144.BridgeWitnessEvaluation.V4",
        "packet_id": packet.packet_id,
        "bridge_id": packet.bridge_id,
        "verdict": verdict,
        "checks": checks,
        "independent_witness_count": len(independent),
        "bridge_truth_effect": (
            "TRANSPORT_CERTIFIED_INSIDE_DECLARED_CORRIDOR"
            if verdict == "CERTIFIED"
            else "NONE"
        ),
        "station_promotion_effect": "NONE",
        "production_registry_mutated": False,
    }
    report["evaluation_digest"] = digest(report)
    return report
