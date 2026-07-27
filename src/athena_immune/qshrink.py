from __future__ import annotations

from typing import Any

from .canonical import content_hash, merkle_root, sha256_hex, utc_now
from .models import RoundTripClass


class QShrinkCodec:
    """Compress a full immune cycle into a replay-checkable successor seed."""

    COMPONENTS = (
        "act",
        "contradiction",
        "repair_plan",
        "repair_receipts",
        "replay_receipt",
        "trust_revision",
        "reentry_permit",
    )

    def build_seed(
        self,
        *,
        seed_id: str,
        cycle_id: str,
        full_cycle: dict[str, Any],
        gate_vector: dict[str, str],
        residual_vector: dict[str, Any],
        source_addresses: list[str],
        next_route: str,
    ) -> dict[str, Any]:
        component_hashes = {
            name: content_hash(full_cycle.get(name), omit=("packet_hash",))
            for name in self.COMPONENTS
        }
        witness_refs = self._witness_refs(full_cycle)
        seed = {
            "schema_version": "ATHENA_QSHRINK_SEED/1",
            "seed_id": seed_id,
            "cycle_id": cycle_id,
            "component_hashes": component_hashes,
            "witness_merkle_root": merkle_root(witness_refs),
            "gate_vector": dict(sorted(gate_vector.items())),
            "residual_vector": residual_vector,
            "source_addresses": sorted(set(source_addresses)),
            "next_route": next_route,
            "reconstruction_contract": list(self.COMPONENTS),
        }
        seed["packet_hash"] = content_hash(seed)
        return seed

    def replay(
        self,
        *,
        certificate_id: str,
        seed: dict[str, Any],
        full_cycle: dict[str, Any],
    ) -> dict[str, Any]:
        rebuilt = self.build_seed(
            seed_id=str(seed["seed_id"]),
            cycle_id=str(seed["cycle_id"]),
            full_cycle=full_cycle,
            gate_vector=dict(seed["gate_vector"]),
            residual_vector=dict(seed["residual_vector"]),
            source_addresses=list(seed["source_addresses"]),
            next_route=str(seed["next_route"]),
        )
        exact = rebuilt["packet_hash"] == seed.get("packet_hash")
        certificate = {
            "schema_version": "REPLAY_CERTIFICATE/1",
            "certificate_id": certificate_id,
            "cycle_id": seed["cycle_id"],
            "seed_id": seed["seed_id"],
            "declared_seed_hash": seed.get("packet_hash"),
            "rebuilt_seed_hash": rebuilt["packet_hash"],
            "classification": (
                RoundTripClass.EXACT.value if exact else RoundTripClass.ILLEGAL.value
            ),
            "component_match": {
                name: rebuilt["component_hashes"][name]
                == seed.get("component_hashes", {}).get(name)
                for name in self.COMPONENTS
            },
            "created_at": utc_now(),
        }
        certificate["packet_hash"] = content_hash(certificate)
        return certificate

    @staticmethod
    def _witness_refs(full_cycle: dict[str, Any]) -> list[str]:
        refs: set[str] = set()
        contradiction = full_cycle.get("contradiction") or {}
        refs.update(contradiction.get("witness_refs", []))
        refs.update(contradiction.get("counterwitness_refs", []))
        trust = full_cycle.get("trust_revision") or {}
        refs.update(trust.get("evidence_refs", []))
        for values in trust.get("dimension_witness_refs", {}).values():
            refs.update(values)
        permit = full_cycle.get("reentry_permit") or {}
        if permit.get("witness_root"):
            refs.add(str(permit["witness_root"]))
        return sorted(refs)

