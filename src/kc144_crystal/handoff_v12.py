from __future__ import annotations

from typing import Any, Mapping, Sequence

from .ceremony_v10 import (
    ENROLLMENT_DOMAIN,
    ROLES,
    GovernanceEnrollmentResponse,
    governance_ceremony_contract,
    verify_enrollment_response,
)
from .dispatch_v11 import (
    DISPATCH_ID,
    challenge_batch_integrity,
    governance_dispatch_contract,
)
from .population import digest


HANDOFF_ID = "KC144.PARTICIPANT.HANDOFF.V12"
HANDOFF_BARRIER = "FIVE_EXTERNAL_PARTICIPANT_HANDOFFS_REQUIRED"

ROLE_PROFILES: dict[str, dict[str, Any]] = {
    "CUSTODIAN": {
        "mission": (
            "preserve governance-key custody, revocation continuity, and "
            "constitution-bound operational integrity"
        ),
        "required_capabilities": [
            "independent ED25519 key custody",
            "revocation and rollback execution",
            "long-lived governance record preservation",
        ],
    },
    "INDEPENDENT_REVIEWER": {
        "mission": (
            "audit governance decisions independently of implementers, "
            "evidence producers, and other governance institutions"
        ),
        "required_capabilities": [
            "independent technical and procedural review",
            "conflict disclosure and disposition",
            "signed dissent and challenge recording",
        ],
    },
    "REPLAY_WITNESS": {
        "mission": (
            "perform and attest independent reconstruction and replay "
            "without treating internal execution as external reproduction"
        ),
        "required_capabilities": [
            "independent execution environment",
            "replay-root capture",
            "difference and failure reporting",
        ],
    },
    "SOURCE_AUDITOR": {
        "mission": (
            "audit source identity, provenance, extraction lineage, and "
            "source-once fan-out claims"
        ),
        "required_capabilities": [
            "source provenance audit",
            "content-addressed claim verification",
            "missing-source and contradiction reporting",
        ],
    },
    "RETURN_AUDITOR": {
        "mission": (
            "audit return paths, rollback sufficiency, closure conditions, "
            "and preservation of rejected branches"
        ),
        "required_capabilities": [
            "forward/return route comparison",
            "rollback-root verification",
            "closure and residual-state audit",
        ],
    },
}


def participant_handoff_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.ParticipantHandoffContract.V12",
        "handoff_id": HANDOFF_ID,
        "parent_dispatch_id": DISPATCH_ID,
        "roles": list(ROLES),
        "packet_count": 5,
        "selection_law": (
            "recipient selection is external; no packet may name, infer, or "
            "claim a participant before identity and independence are "
            "actually established"
        ),
        "delivery_law": (
            "packet preparation is not addressing or delivery; delivery is "
            "observed only by a batch-matched signed enrollment response or "
            "separate external transport evidence"
        ),
        "private_key_law": (
            "participants generate and retain their own ED25519 private "
            "keys; private keys are never returned"
        ),
        "return_law": (
            "a return must contain the complete signed V10 enrollment "
            "response and exact issued challenge; partial attestations do "
            "not fill a governance seat"
        ),
        "decline_law": (
            "decline, conflict, expiration, malformed return, and silence "
            "remain distinct non-counting outcomes"
        ),
        "activation_law": (
            "V12 prepares and verifies handoffs only; governance activation "
            "still requires five responses, pending-society assembly, and "
            "two-anchor V10 ratification"
        ),
        "truth_effect": "NONE",
    }
    return {**body, "contract_digest": digest(body)}


def _packet_id(role: str, challenge_digest: str) -> str:
    seed = {
        "handoff_id": HANDOFF_ID,
        "role": role,
        "challenge_digest": challenge_digest,
    }
    return f"V12-PACKET::{role}::{digest(seed)[7:23]}"


def participant_handoff_packet(
    batch: Mapping[str, Any],
    role: str,
) -> dict[str, Any]:
    if not challenge_batch_integrity(batch):
        raise ValueError("challenge batch integrity failure")
    if role not in ROLES:
        raise ValueError(f"unknown governance role: {role}")
    challenge = next(
        value for value in batch["challenges"] if value["role"] == role
    )
    profile = ROLE_PROFILES[role]
    body = {
        "schema": "KC144.ParticipantHandoffPacket.V12",
        "handoff_id": HANDOFF_ID,
        "packet_id": _packet_id(
            role,
            challenge["challenge_digest"],
        ),
        "role": role,
        "batch_id": batch["batch_id"],
        "batch_root": batch["batch_root"],
        "challenge_id": challenge["challenge_id"],
        "challenge_digest": challenge["challenge_digest"],
        "challenge": challenge,
        "handoff_contract_digest": participant_handoff_contract()[
            "contract_digest"
        ],
        "dispatch_contract_digest": governance_dispatch_contract()[
            "contract_digest"
        ],
        "ceremony_contract_digest": governance_ceremony_contract()[
            "contract_digest"
        ],
        "mission": profile["mission"],
        "required_capabilities": profile["required_capabilities"],
        "universal_disqualifiers": [
            "TEST-only identity",
            "shared institution with another governance seat",
            "shared lineage with another governance seat",
            "shared public key or delegated private key",
            "undisposed conflict",
            "self-ratification claim",
        ],
        "required_attestation_roots": [
            "identity_claim_root",
            "institution_root",
            "lineage_root",
            "external_identity_verification_root",
            "conflict_disclosure_root",
            "consent_root",
        ],
        "response_schema": "KC144.GovernanceEnrollmentResponse.V10",
        "signature_algorithm": "ED25519",
        "signature_domain": ENROLLMENT_DOMAIN,
        "canonicalization": (
            "KC144 canonical JSON: UTF-8, sorted keys, compact separators"
        ),
        "boundary_claim": (
            "PARTICIPANT_CONSENT_NOT_SELF_RATIFICATION"
        ),
        "private_key_instruction": (
            "generate and retain the private key externally; return only "
            "the raw 32-byte public key encoded as base64 and the detached "
            "base64 signature"
        ),
        "return_routes": {
            "signed_response": (
                "route through governance-response-route against the full "
                "immutable V11 batch"
            ),
            "decline": "record DECLINED without filling the seat",
            "conflict": (
                "record CONFLICT_PENDING until a signed resolution root "
                "exists"
            ),
            "expired": (
                "preserve this packet and issue a new immutable batch"
            ),
            "malformed": (
                "preserve the rejected bytes and verification report"
            ),
        },
        "delivery_state": "READY_UNADDRESSED_UNDELIVERED",
        "recipient_identity_root": None,
        "delivery_receipt_root": None,
        "governance_activated": False,
        "truth_effect": "NONE",
    }
    return {**body, "packet_digest": digest(body)}


def participant_handoff_packet_integrity(
    batch: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> bool:
    try:
        role = str(packet["role"])
        expected = participant_handoff_packet(batch, role)
    except (KeyError, TypeError, ValueError, StopIteration):
        return False
    return dict(packet) == expected


def participant_handoff_manifest(
    batch: Mapping[str, Any],
    packets: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not challenge_batch_integrity(batch):
        raise ValueError("challenge batch integrity failure")
    ordered = sorted(
        (dict(packet) for packet in packets),
        key=lambda packet: ROLES.index(str(packet["role"])),
    )
    if len(ordered) != 5 or not all(
        participant_handoff_packet_integrity(batch, packet)
        for packet in ordered
    ):
        raise ValueError("five integral role packets required")
    rows = [
        {
            "role": packet["role"],
            "packet_id": packet["packet_id"],
            "packet_digest": packet["packet_digest"],
            "challenge_id": packet["challenge_id"],
            "challenge_digest": packet["challenge_digest"],
            "state": packet["delivery_state"],
        }
        for packet in ordered
    ]
    body = {
        "schema": "KC144.ParticipantHandoffManifest.V12",
        "handoff_id": HANDOFF_ID,
        "parent_batch_id": batch["batch_id"],
        "parent_batch_root": batch["batch_root"],
        "handoff_contract_digest": participant_handoff_contract()[
            "contract_digest"
        ],
        "packet_rows": rows,
        "packet_count": len(rows),
        "addressed_count": 0,
        "delivered_count": 0,
        "returned_response_count": 0,
        "status": "READY_FOR_EXTERNAL_RECIPIENT_SELECTION_AND_DELIVERY",
        "barrier": HANDOFF_BARRIER,
        "parallelism": "ALL_FIVE_PACKETS_MAY_BE_DELIVERED_IN_PARALLEL",
        "governance_activated": False,
        "production_certificate_issued": False,
        "truth_effect": "NONE",
        "next_seed": (
            "KC144.V12::SELECT-INDEPENDENT-RECIPIENTS_DELIVER-FIVE-"
            "PACKETS_AND-ROUTE-SIGNED-RETURNS"
        ),
    }
    return {**body, "manifest_root": digest(body)}


def participant_handoff_manifest_integrity(
    batch: Mapping[str, Any],
    manifest: Mapping[str, Any],
    packets: Sequence[Mapping[str, Any]],
) -> bool:
    try:
        expected = participant_handoff_manifest(batch, packets)
    except (KeyError, TypeError, ValueError, StopIteration):
        return False
    return dict(manifest) == expected


def verify_response_for_handoff_packet(
    batch: Mapping[str, Any],
    packet: Mapping[str, Any],
    response: GovernanceEnrollmentResponse,
    *,
    verified_at: str,
) -> dict[str, Any]:
    packet_integral = participant_handoff_packet_integrity(batch, packet)
    exact_role = response.member.role == packet.get("role")
    exact_challenge = (
        packet_integral
        and response.challenge.to_dict() == packet.get("challenge")
    )
    enrollment = verify_enrollment_response(
        response,
        verified_at=verified_at,
    )
    checks = {
        "batch_integrity": challenge_batch_integrity(batch),
        "packet_integrity": packet_integral,
        "role_exact": exact_role,
        "challenge_exact": exact_challenge,
        "enrollment_verification_pass": enrollment["verdict"] == "PASS",
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.ParticipantHandoffReturnVerification.V12",
        "handoff_id": HANDOFF_ID,
        "packet_id": packet.get("packet_id"),
        "response_id": response.response_id,
        "role": response.member.role,
        "verdict": verdict,
        "status": (
            "RETURN_VERIFIED_FOR_V11_PARALLEL_ROUTER"
            if verdict == "PASS"
            else "RETURN_HOLD"
        ),
        "checks": checks,
        "enrollment_verification": enrollment,
        "governance_activated": False,
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}
