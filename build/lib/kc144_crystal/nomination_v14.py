from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)

from .ceremony_v10 import ROLES
from .dispatch_v11 import challenge_batch_integrity
from .handoff_v12 import (
    ROLE_PROFILES,
    participant_handoff_packet,
)
from .population import canonical_json, digest
from .selection_v13 import (
    CandidateNomination,
    candidate_registry,
    candidate_selection_contract,
    verify_candidate_nomination,
)


INTAKE_ID = "KC144.CANDIDATE.NOMINATION.INTAKE.V14"
SIGNATURE_DOMAIN = "KC144.V14.CANDIDATE_NOMINATION"
NOMINATION_FIELDS = (
    "nomination_id",
    "candidate_id",
    "status",
    "test_only",
    "algorithm",
    "public_key_b64",
    "eligible_roles",
    "identity_claim_root",
    "external_identity_verification_root",
    "external_independence_verification_root",
    "institution_root",
    "lineage_root",
    "jurisdiction_root",
    "primary_domain_root",
    "authority_root",
    "funding_root",
    "data_control_root",
    "staff_control_root",
    "technology_control_root",
    "conflict_disclosure_root",
    "conflict_status",
    "conflict_resolution_root",
    "nomination_evidence_root",
    "not_before",
    "not_after",
)


@dataclass(frozen=True)
class SignedCandidateNomination:
    envelope_id: str
    nomination: CandidateNomination
    signature_domain: str
    signature_b64: str

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "SignedCandidateNomination":
        body = dict(value)
        body.pop("schema", None)
        body["nomination"] = CandidateNomination.from_dict(
            body["nomination"]
        )
        return cls(**body)

    def signing_body(self) -> dict[str, Any]:
        return {
            "schema": "KC144.SignedCandidateNomination.V14",
            "envelope_id": self.envelope_id,
            "nomination": self.nomination.to_dict(),
            "signature_domain": self.signature_domain,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.signing_body(),
            "signature_b64": self.signature_b64,
        }


def nomination_signing_bytes(
    envelope: SignedCandidateNomination,
) -> bytes:
    return canonical_json(envelope.signing_body()).encode("utf-8")


def nomination_intake_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.NominationIntakeContract.V14",
        "intake_id": INTAKE_ID,
        "roles": list(ROLES),
        "role_call_count": 5,
        "submission_schema": "KC144.SignedCandidateNomination.V14",
        "signature_algorithm": "ED25519",
        "signature_domain": SIGNATURE_DOMAIN,
        "required_nomination_fields": list(NOMINATION_FIELDS),
        "publication_law": (
            "role-call preparation is not publication, addressing, "
            "delivery, nomination, or consent"
        ),
        "signature_law": (
            "a submission enters the V13 cohort solver only when its "
            "candidate key verifies the complete canonical V14 envelope"
        ),
        "evidence_law": (
            "signature verification proves control of the declared key; "
            "it does not independently prove identity, affiliation, "
            "independence, evidence roots, or fitness"
        ),
        "routing_law": (
            "all valid signed declarations enter the bounded V13 solver; "
            "held declarations remain recorded and have no solver effect"
        ),
        "assignment_law": (
            "only one unique ten-edge provisional cohort may bind the five "
            "immutable V12 packets; ambiguous and absent cohorts bind none"
        ),
        "delivery_law": (
            "packet binding is not addressing or delivery and grants no "
            "governance authority"
        ),
        "truth_effect": "NONE",
    }
    return {**body, "contract_digest": digest(body)}


def verify_signed_candidate_nomination(
    envelope: SignedCandidateNomination,
    *,
    checked_at: str,
) -> dict[str, Any]:
    nomination_report = verify_candidate_nomination(
        envelope.nomination,
        checked_at=checked_at,
    )
    signature_well_formed = False
    signature_valid = False
    try:
        public_key = base64.b64decode(
            envelope.nomination.public_key_b64,
            validate=True,
        )
        signature = base64.b64decode(
            envelope.signature_b64,
            validate=True,
        )
        signature_well_formed = len(public_key) == 32 and len(signature) == 64
        if signature_well_formed:
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                signature,
                nomination_signing_bytes(envelope),
            )
            signature_valid = True
    except (
        ValueError,
        TypeError,
        binascii.Error,
        InvalidSignature,
    ):
        pass
    checks = {
        "envelope_id_present": bool(envelope.envelope_id.strip()),
        "signature_domain_exact": (
            envelope.signature_domain == SIGNATURE_DOMAIN
        ),
        "nomination_verification_pass": (
            nomination_report["verdict"] == "PASS"
        ),
        "signature_well_formed": signature_well_formed,
        "candidate_key_signature_valid": signature_valid,
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.SignedCandidateNominationVerification.V14",
        "intake_id": INTAKE_ID,
        "envelope_id": envelope.envelope_id,
        "nomination_id": envelope.nomination.nomination_id,
        "candidate_id": envelope.nomination.candidate_id,
        "eligible_roles": list(envelope.nomination.eligible_roles),
        "verdict": verdict,
        "status": (
            "SIGNED_DECLARATION_ADMITTED_TO_V13_SOLVER"
            if verdict == "PASS"
            else "SIGNED_DECLARATION_HOLD"
        ),
        "checks": checks,
        "nomination_verification": nomination_report,
        "identity_independence_externally_proven": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def nomination_role_call(
    batch: Mapping[str, Any],
    role: str,
) -> dict[str, Any]:
    if not challenge_batch_integrity(batch):
        raise ValueError("challenge batch integrity failure")
    if role not in ROLES:
        raise ValueError(f"unknown governance role: {role}")
    handoff_packet = participant_handoff_packet(batch, role)
    profile = ROLE_PROFILES[role]
    seed = {
        "intake_id": INTAKE_ID,
        "batch_root": batch["batch_root"],
        "role": role,
        "participant_packet_digest": handoff_packet["packet_digest"],
    }
    body = {
        "schema": "KC144.NominationRoleCall.V14",
        "intake_id": INTAKE_ID,
        "call_id": f"V14-CALL::{role}::{digest(seed)[7:23]}",
        "role": role,
        "batch_id": batch["batch_id"],
        "batch_root": batch["batch_root"],
        "challenge_id": handoff_packet["challenge_id"],
        "challenge_digest": handoff_packet["challenge_digest"],
        "participant_packet_id": handoff_packet["packet_id"],
        "participant_packet_digest": handoff_packet["packet_digest"],
        "intake_contract_digest": nomination_intake_contract()[
            "contract_digest"
        ],
        "selection_contract_digest": candidate_selection_contract()[
            "contract_digest"
        ],
        "mission": profile["mission"],
        "required_capabilities": profile["required_capabilities"],
        "required_nomination_fields": list(NOMINATION_FIELDS),
        "required_independence_dimensions": candidate_selection_contract()[
            "independence_dimensions"
        ],
        "submission_schema": "KC144.SignedCandidateNomination.V14",
        "signature_algorithm": "ED25519",
        "signature_domain": SIGNATURE_DOMAIN,
        "private_key_instruction": (
            "generate and retain the private key externally; sign the "
            "canonical V14 envelope and return only public material"
        ),
        "boundary_claim": (
            "NOMINATION_IS_NOT_SELECTION_DELIVERY_ENROLLMENT_OR_AUTHORITY"
        ),
        "call_state": "READY_UNADDRESSED_UNPUBLISHED",
        "publication_receipt_root": None,
        "recipient_identity_root": None,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {**body, "call_digest": digest(body)}


def nomination_role_call_integrity(
    batch: Mapping[str, Any],
    call: Mapping[str, Any],
) -> bool:
    try:
        expected = nomination_role_call(batch, str(call["role"]))
    except (KeyError, TypeError, ValueError, StopIteration):
        return False
    return dict(call) == expected


def nomination_call_manifest(
    batch: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not challenge_batch_integrity(batch):
        raise ValueError("challenge batch integrity failure")
    ordered = sorted(
        (dict(call) for call in calls),
        key=lambda call: ROLES.index(str(call["role"])),
    )
    if (
        len(ordered) != 5
        or [call["role"] for call in ordered] != list(ROLES)
        or not all(
            nomination_role_call_integrity(batch, call)
            for call in ordered
        )
    ):
        raise ValueError("five integral role calls required")
    rows = [
        {
            "role": call["role"],
            "call_id": call["call_id"],
            "call_digest": call["call_digest"],
            "participant_packet_id": call["participant_packet_id"],
            "participant_packet_digest": call[
                "participant_packet_digest"
            ],
            "state": call["call_state"],
        }
        for call in ordered
    ]
    body = {
        "schema": "KC144.NominationCallManifest.V14",
        "intake_id": INTAKE_ID,
        "parent_batch_id": batch["batch_id"],
        "parent_batch_root": batch["batch_root"],
        "intake_contract_digest": nomination_intake_contract()[
            "contract_digest"
        ],
        "call_rows": rows,
        "call_count": 5,
        "published_count": 0,
        "addressed_count": 0,
        "status": "READY_FOR_EXTERNAL_PUBLICATION",
        "parallelism": "ALL_FIVE_ROLE_CALLS_MAY_BE_PUBLISHED_IN_PARALLEL",
        "publication_claimed": False,
        "delivery_claimed": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {**body, "manifest_root": digest(body)}


def nomination_call_manifest_integrity(
    batch: Mapping[str, Any],
    manifest: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
) -> bool:
    try:
        expected = nomination_call_manifest(batch, calls)
    except (KeyError, TypeError, ValueError, StopIteration):
        return False
    return dict(manifest) == expected


def nomination_receipt_ledger(
    envelopes: Sequence[SignedCandidateNomination],
    *,
    checked_at: str,
) -> dict[str, Any]:
    ordered = sorted(
        envelopes,
        key=lambda envelope: (
            envelope.nomination.candidate_id,
            envelope.nomination.nomination_id,
            envelope.envelope_id,
        ),
    )
    duplicate_envelope_ids = {
        envelope_id
        for envelope_id in {item.envelope_id for item in ordered}
        if sum(item.envelope_id == envelope_id for item in ordered) > 1
    }
    duplicate_nomination_ids = {
        nomination_id
        for nomination_id in {
            item.nomination.nomination_id for item in ordered
        }
        if sum(
            item.nomination.nomination_id == nomination_id
            for item in ordered
        )
        > 1
    }
    duplicate_candidate_ids = {
        candidate_id
        for candidate_id in {
            item.nomination.candidate_id for item in ordered
        }
        if sum(
            item.nomination.candidate_id == candidate_id
            for item in ordered
        )
        > 1
    }
    rows = []
    admitted_nominations = []
    for envelope in ordered:
        verification = verify_signed_candidate_nomination(
            envelope,
            checked_at=checked_at,
        )
        duplicate_collision = (
            envelope.envelope_id in duplicate_envelope_ids
            or envelope.nomination.nomination_id
            in duplicate_nomination_ids
            or envelope.nomination.candidate_id
            in duplicate_candidate_ids
        )
        admitted = (
            verification["verdict"] == "PASS"
            and not duplicate_collision
        )
        if admitted:
            admitted_nominations.append(envelope.nomination)
        row_body = {
            "envelope_id": envelope.envelope_id,
            "nomination_id": envelope.nomination.nomination_id,
            "candidate_id": envelope.nomination.candidate_id,
            "eligible_roles": list(
                envelope.nomination.eligible_roles
            ),
            "verification_digest": verification[
                "verification_digest"
            ],
            "signature_verdict": verification["verdict"],
            "duplicate_collision": duplicate_collision,
            "intake_verdict": "PASS" if admitted else "HOLD",
            "status": (
                "ADMITTED_TO_V13_SOLVER"
                if admitted
                else "PRESERVED_NONCOUNTING_SUBMISSION"
            ),
            "authority_effect": "NONE",
        }
        rows.append({**row_body, "receipt_digest": digest(row_body)})
    registry = candidate_registry(admitted_nominations)
    body = {
        "schema": "KC144.NominationReceiptLedger.V14",
        "intake_id": INTAKE_ID,
        "checked_at": checked_at,
        "submission_count": len(ordered),
        "admitted_count": len(admitted_nominations),
        "held_count": len(ordered) - len(admitted_nominations),
        "duplicate_envelope_ids": sorted(duplicate_envelope_ids),
        "duplicate_nomination_ids": sorted(duplicate_nomination_ids),
        "duplicate_candidate_ids": sorted(duplicate_candidate_ids),
        "receipts": rows,
        "admitted_candidate_registry_root": registry["registry_root"],
        "authority_effect": "NONE",
        "truth_effect": "NONE",
    }
    return {
        **body,
        "ledger_root": digest(body),
        "_admitted_nominations": tuple(admitted_nominations),
    }


def public_nomination_receipt_ledger(
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in ledger.items()
        if key != "_admitted_nominations"
    }


def nomination_receipt_ledger_integrity(
    envelopes: Sequence[SignedCandidateNomination],
    ledger: Mapping[str, Any],
    *,
    checked_at: str,
) -> bool:
    expected = public_nomination_receipt_ledger(
        nomination_receipt_ledger(
            envelopes,
            checked_at=checked_at,
        )
    )
    return dict(ledger) == expected


def cohort_packet_assignment_manifest(
    batch: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
    nominations: Sequence[CandidateNomination],
    solver: Mapping[str, Any],
) -> dict[str, Any]:
    if not challenge_batch_integrity(batch):
        raise ValueError("challenge batch integrity failure")
    call_manifest = nomination_call_manifest(batch, calls)
    calls_by_role = {str(call["role"]): dict(call) for call in calls}
    nominations_by_candidate = {
        nomination.candidate_id: nomination
        for nomination in nominations
    }
    bindings: list[dict[str, Any]] = []
    if solver["solution_status"] == "UNIQUE_PROVISIONAL_COHORT":
        selected = solver["selected_cohort"]
        if not isinstance(selected, Mapping):
            raise ValueError("unique cohort must contain a selection")
        for role in ROLES:
            candidate_id = str(selected[role])
            nomination = nominations_by_candidate[candidate_id]
            call = calls_by_role[role]
            binding_body = {
                "role": role,
                "call_id": call["call_id"],
                "candidate_id": candidate_id,
                "nomination_id": nomination.nomination_id,
                "participant_packet_id": call["participant_packet_id"],
                "participant_packet_digest": call[
                    "participant_packet_digest"
                ],
                "binding_state": (
                    "PROVISIONAL_UNADDRESSED_UNDELIVERED"
                ),
            }
            bindings.append(
                {**binding_body, "binding_digest": digest(binding_body)}
            )
        state = "UNIQUE_PROVISIONAL_COHORT_BOUND"
        barrier = "FIVE_PACKET_DELIVERIES_REQUIRED"
    else:
        state = {
            "NO_COHORT": "NO_COHORT_NO_BINDING",
            "MULTIPLE_COHORTS": "AMBIGUOUS_COHORT_NO_BINDING",
            "SOLVER_BUDGET_EXHAUSTED": "SOLVER_HOLD_NO_BINDING",
        }.get(str(solver["solution_status"]), "SOLVER_HOLD_NO_BINDING")
        barrier = str(solver["barrier"])
    body = {
        "schema": "KC144.CohortPacketAssignmentManifest.V14",
        "intake_id": INTAKE_ID,
        "parent_batch_id": batch["batch_id"],
        "parent_batch_root": batch["batch_root"],
        "call_manifest_root": call_manifest["manifest_root"],
        "solver_digest": solver["solver_digest"],
        "solution_status": solver["solution_status"],
        "assignment_state": state,
        "bindings": bindings,
        "assigned_count": len(bindings),
        "required_pairwise_audits": 10,
        "selected_pairwise_audits": solver[
            "selected_pairwise_audits"
        ],
        "selected_pair_audit_digests": [
            audit["audit_digest"]
            for audit in solver["selected_pair_audits"]
        ],
        "addressed_packets": 0,
        "delivered_packets": 0,
        "barrier": barrier,
        "selection_authority": "V13_UNIQUE_SOLUTION_ONLY",
        "governance_authority_granted": False,
        "production_certificate_issued": False,
        "truth_effect": "NONE",
    }
    return {**body, "assignment_root": digest(body)}


def cohort_packet_assignment_manifest_integrity(
    batch: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
    nominations: Sequence[CandidateNomination],
    solver: Mapping[str, Any],
    manifest: Mapping[str, Any],
) -> bool:
    try:
        expected = cohort_packet_assignment_manifest(
            batch,
            calls,
            nominations,
            solver,
        )
    except (KeyError, TypeError, ValueError, StopIteration):
        return False
    return dict(manifest) == expected
