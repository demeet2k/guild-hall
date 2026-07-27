from __future__ import annotations

from typing import Any

from .canonical import canonical_data, content_hash, sha256_hex, utc_now
from .models import RoundTripClass


class KC54Auditor:
    """Compare a constructive route with its conjugate reconstruction."""

    TRANSIENT_FIELDS = {
        "packet_hash",
        "entry_hash",
        "previous_hash",
        "created_at",
        "sequence",
    }
    DEFECT_DIMENSIONS = (
        "identity",
        "route",
        "witness",
        "repair",
        "replay",
        "trust",
        "boundary",
        "seed",
    )

    def _projection(self, event: dict[str, Any]) -> dict[str, Any]:
        return canonical_data(event, omit=self.TRANSIENT_FIELDS)

    def audit(
        self,
        *,
        receipt_id: str,
        cycle_id: str,
        forward_route: list[dict[str, Any]],
        reconstructed_inverse_route: list[dict[str, Any]],
        preserved_invariants: list[str],
        irreversible_changes: list[str] | None = None,
        alternate_branches: list[str] | None = None,
        unresolved_frontier: list[str] | None = None,
        invalidating_conditions: list[str] | None = None,
    ) -> dict[str, Any]:
        forward_hash = sha256_hex(forward_route)
        inverse_hash = sha256_hex(reconstructed_inverse_route)
        forward_projection = [self._projection(event) for event in forward_route]
        inverse_projection = [self._projection(event) for event in reconstructed_inverse_route]
        projected_forward_hash = sha256_hex(forward_projection)
        projected_inverse_hash = sha256_hex(inverse_projection)
        unresolved = unresolved_frontier or []

        if forward_hash == inverse_hash:
            classification = RoundTripClass.EXACT
        elif projected_forward_hash == projected_inverse_hash:
            classification = RoundTripClass.LAW_EQUIV
        elif unresolved:
            classification = RoundTripClass.RESIDUALIZED
        else:
            classification = RoundTripClass.ILLEGAL

        forward_types = [str(event.get("packet_type", event.get("schema_version", ""))) for event in forward_route]
        inverse_types = [
            str(event.get("packet_type", event.get("schema_version", "")))
            for event in reconstructed_inverse_route
        ]
        type_set = set(forward_types) | set(inverse_types)
        keywords = {
            "identity": ("ACT", "CONTRADICTION"),
            "route": ("ROUTE", "PLAN"),
            "witness": ("WITNESS",),
            "repair": ("REPAIR",),
            "replay": ("REPLAY",),
            "trust": ("TRUST",),
            "boundary": ("PERMIT", "RESIDUAL"),
            "seed": ("SEED", "QSHRINK"),
        }
        mismatch = forward_types != inverse_types
        defect_vector = {
            dimension: int(
                mismatch
                and any(token in " ".join(type_set).upper() for token in tokens)
            )
            for dimension, tokens in keywords.items()
        }

        receipt = {
            "schema_version": "KC54_CONJUGATE_RECEIPT/1",
            "receipt_id": receipt_id,
            "cycle_id": cycle_id,
            "classification": classification.value,
            "forward_route_hash": forward_hash,
            "inverse_route_hash": inverse_hash,
            "projected_forward_hash": projected_forward_hash,
            "projected_inverse_hash": projected_inverse_hash,
            "preserved_invariants": sorted(set(preserved_invariants)),
            "irreversible_changes": sorted(set(irreversible_changes or [])),
            "alternate_branches": sorted(set(alternate_branches or [])),
            "unresolved_frontier": sorted(set(unresolved)),
            "invalidating_conditions": invalidating_conditions
            or [
                "SOURCE_DIGEST_CHANGED",
                "MISSING_LEDGER_ENTRY",
                "HASH_CHAIN_BROKEN",
                "UNDECLARED_RESIDUAL",
            ],
            "return_defect_vector": defect_vector,
            "created_at": utc_now(),
        }
        receipt["packet_hash"] = content_hash(receipt)
        return receipt

