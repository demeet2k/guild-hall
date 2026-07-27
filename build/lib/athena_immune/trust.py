from __future__ import annotations

from typing import Any

from .canonical import content_hash, utc_now
from .models import TRUST_DIMENSIONS, TrustEvidence, TrustVector


class TrustRevisionError(ValueError):
    """Raised when a trust revision violates witness or range laws."""


class TrustRevisionEngine:
    """Witness-masked trust updates with append-only revision semantics."""

    def revise(
        self,
        *,
        revision_id: str,
        cycle_id: str,
        contradiction_id: str,
        subject_edge: str,
        prior: TrustVector,
        evidence: TrustEvidence,
        evidence_refs: list[str],
        repair_receipt_refs: list[str],
        replay_receipt_ref: str,
        residual_refs: list[str],
        proposer: str,
        reviewer: str,
        replay_auditor: str,
        previous_revision_hash: str | None = None,
    ) -> dict[str, Any]:
        prior_data = prior.to_dict()
        resulting = dict(prior_data)
        proposed_delta: dict[str, float] = {name: 0.0 for name in TRUST_DIMENSIONS}
        accepted_delta: dict[str, float] = {name: 0.0 for name in TRUST_DIMENSIONS}
        changed: list[str] = []
        unchanged: list[str] = []
        reason_codes: list[str] = []

        for name in TRUST_DIMENSIONS:
            if name not in evidence.outcome:
                unchanged.append(name)
                reason_codes.append(f"{name.upper()}::NO_OUTCOME")
                continue

            target = evidence.outcome[name]
            proposed = evidence.eta * (target - prior_data[name])
            proposed_delta[name] = round(proposed, 12)
            witnesses = evidence.witness_refs.get(name, [])
            if not witnesses:
                unchanged.append(name)
                reason_codes.append(f"{name.upper()}::UNWITNESSED_DELTA_ZEROED")
                continue

            resulting[name] = min(1.0, max(0.0, prior_data[name] + proposed))
            accepted_delta[name] = round(resulting[name] - prior_data[name], 12)
            if accepted_delta[name] != 0.0:
                changed.append(name)
                reason_codes.append(f"{name.upper()}::DELTA_WITNESSED")
            else:
                unchanged.append(name)
                reason_codes.append(f"{name.upper()}::NO_CHANGE")

        revision = {
            "schema_version": "TRUST_REVISION_ENTRY/1",
            "revision_id": revision_id,
            "cycle_id": cycle_id,
            "contradiction_id": contradiction_id,
            "subject_edge": subject_edge,
            "prior_trust_vector": prior_data,
            "proposed_delta": proposed_delta,
            "accepted_delta": accepted_delta,
            "resulting_trust_vector": resulting,
            "evidence_refs": sorted(set(evidence_refs)),
            "dimension_witness_refs": {
                name: sorted(set(evidence.witness_refs.get(name, [])))
                for name in TRUST_DIMENSIONS
            },
            "repair_receipt_refs": sorted(set(repair_receipt_refs)),
            "replay_receipt_ref": replay_receipt_ref,
            "residual_refs": sorted(set(residual_refs)),
            "dimensions_changed": changed,
            "dimensions_unchanged": unchanged,
            "reason_codes": reason_codes,
            "proposer": proposer,
            "reviewer": reviewer,
            "replay_auditor": replay_auditor,
            "authorization_status": "AUTHORIZED" if proposer != replay_auditor else "REFUSED",
            "previous_revision_hash": previous_revision_hash,
            "created_at": utc_now(),
        }
        if proposer == replay_auditor:
            revision["reason_codes"].append("ROLE_SEPARATION_FAILURE")
        revision["packet_hash"] = content_hash(revision)
        return revision

    @staticmethod
    def justified(revision: dict[str, Any]) -> bool:
        if revision.get("authorization_status") != "AUTHORIZED":
            return False
        witnesses = revision.get("dimension_witness_refs", {})
        for dimension in revision.get("dimensions_changed", []):
            if not witnesses.get(dimension):
                return False
        return True

