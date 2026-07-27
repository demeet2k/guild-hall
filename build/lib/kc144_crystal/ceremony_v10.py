from __future__ import annotations

import base64
import binascii
import re
import secrets
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .crosswalk import ACTIVE_EPOCH_ID
from .handoff_v9 import (
    GOVERNANCE_ID,
    GOVERNANCE_MEMBER_COUNT,
    GOVERNANCE_THRESHOLD,
    GovernanceMember,
    governance_registry_integrity,
    seal_governance_registry,
    threshold_governance_contract,
)
from .population import canonical_json, digest


CEREMONY_ID = "KC144.GOVERNANCE.CEREMONY.V10"
ENROLLMENT_DOMAIN = "KC144.V10.GOVERNANCE_ENROLLMENT"
RATIFICATION_DOMAIN = "KC144.V10.GOVERNANCE_RATIFICATION"
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
NONCE = re.compile(r"^[0-9a-f]{64}$")
ROLES = (
    "CUSTODIAN",
    "INDEPENDENT_REVIEWER",
    "REPLAY_WITNESS",
    "SOURCE_AUDITOR",
    "RETURN_AUDITOR",
)


@dataclass(frozen=True)
class GovernanceChallenge:
    challenge_id: str
    ceremony_id: str
    epoch_id: str
    role: str
    governance_contract_digest: str
    authority_registry_digest: str
    handoff_bundle_root: str
    nonce: str
    issued_at: str
    expires_at: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernanceChallenge":
        body = dict(value)
        body.pop("schema", None)
        body.pop("challenge_digest", None)
        return cls(**body)

    def to_dict(self) -> dict[str, Any]:
        body = {
            "schema": "KC144.GovernanceChallenge.V10",
            **asdict(self),
        }
        return {**body, "challenge_digest": digest(body)}


@dataclass(frozen=True)
class GovernanceEnrollmentResponse:
    response_id: str
    challenge: GovernanceChallenge
    member: GovernanceMember
    identity_claim_root: str
    institution_root: str
    lineage_root: str
    external_identity_verification_root: str
    conflict_disclosure_root: str
    conflict_status: str
    conflict_resolution_root: str | None
    consent_root: str
    boundary_claim: str
    signature_b64: str

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "GovernanceEnrollmentResponse":
        body = dict(value)
        body.pop("schema", None)
        body["challenge"] = GovernanceChallenge.from_dict(
            body["challenge"]
        )
        body["member"] = GovernanceMember.from_dict(body["member"])
        return cls(**body)

    def signing_body(self) -> dict[str, Any]:
        body = asdict(self)
        body["schema"] = "KC144.GovernanceEnrollmentResponse.V10"
        body["challenge"] = self.challenge.to_dict()
        body.pop("signature_b64")
        return body

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "KC144.GovernanceEnrollmentResponse.V10",
            **asdict(self),
            "challenge": self.challenge.to_dict(),
        }


@dataclass(frozen=True)
class ExternalCheckpointReceipt:
    anchor_id: str
    algorithm: str
    public_key_b64: str
    institution_root: str
    checkpoint_ref: str
    checkpoint_root: str
    observed_at: str
    signature_b64: str

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "ExternalCheckpointReceipt":
        return cls(**dict(value))


@dataclass(frozen=True)
class GovernanceRatification:
    ratification_id: str
    ceremony_root: str
    constitution_root_before: str
    constitution_root_after: str
    rollback_root: str
    challenge_window_closed_at: str
    challenge_disposition_root: str
    ratified_at: str
    anchors: tuple[ExternalCheckpointReceipt, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernanceRatification":
        body = dict(value)
        body.pop("schema", None)
        body["anchors"] = tuple(
            ExternalCheckpointReceipt.from_dict(anchor)
            for anchor in body.get("anchors", ())
        )
        return cls(**body)

    def anchor_signing_body(
        self,
        anchor: ExternalCheckpointReceipt,
    ) -> dict[str, Any]:
        return {
            "signature_domain": RATIFICATION_DOMAIN,
            "ratification_id": self.ratification_id,
            "ceremony_root": self.ceremony_root,
            "constitution_root_before": self.constitution_root_before,
            "constitution_root_after": self.constitution_root_after,
            "rollback_root": self.rollback_root,
            "challenge_window_closed_at": self.challenge_window_closed_at,
            "challenge_disposition_root": self.challenge_disposition_root,
            "ratified_at": self.ratified_at,
            "anchor_id": anchor.anchor_id,
            "institution_root": anchor.institution_root,
            "checkpoint_ref": anchor.checkpoint_ref,
            "checkpoint_root": anchor.checkpoint_root,
            "observed_at": anchor.observed_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "KC144.GovernanceRatification.V10",
            **asdict(self),
        }


def enrollment_signing_bytes(
    response: GovernanceEnrollmentResponse,
) -> bytes:
    domain = {
        "signature_domain": ENROLLMENT_DOMAIN,
        "response": response.signing_body(),
    }
    return canonical_json(domain).encode("utf-8")


def ratification_signing_bytes(
    ratification: GovernanceRatification,
    anchor: ExternalCheckpointReceipt,
) -> bytes:
    return canonical_json(
        ratification.anchor_signing_body(anchor)
    ).encode("utf-8")


def _challenge_id(role: str, nonce: str, issued_at: str) -> str:
    challenge_seed = {
        "ceremony_id": CEREMONY_ID,
        "role": role,
        "nonce": nonce,
        "issued_at": issued_at,
    }
    return f"V10-CHALLENGE::{digest(challenge_seed)[7:31]}"


def governance_ceremony_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.GovernanceCeremonyContract.V10",
        "ceremony_id": CEREMONY_ID,
        "epoch_id": ACTIVE_EPOCH_ID,
        "roles": list(ROLES),
        "member_count": GOVERNANCE_MEMBER_COUNT,
        "authority_threshold": GOVERNANCE_THRESHOLD,
        "enrollment_signature_domain": ENROLLMENT_DOMAIN,
        "ratification_signature_domain": RATIFICATION_DOMAIN,
        "challenge_nonce": "32_RANDOM_BYTES_HEX",
        "independence_law": (
            "member IDs, public keys, institutions, and lineages are unique "
            "across all five seats"
        ),
        "conflict_law": (
            "every conflict is disclosed and either CLEAR or accompanied by "
            "a signed resolution root before society assembly"
        ),
        "activation_law": (
            "five verified participant responses form only a pending society; "
            "activation additionally requires a closed challenge window, "
            "challenge disposition, constitution transition, rollback root, "
            "and two independent signed external checkpoints"
        ),
        "fixture_law": "LOCAL_OR_TEST_PROOFS_NEVER_ACTIVATE_PRODUCTION",
        "truth_effect": "NONE_UNTIL_EXTERNAL_RATIFICATION",
    }
    return {**body, "contract_digest": digest(body)}


def governance_ratification_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.GovernanceRatificationContract.V10",
        "ceremony_id": CEREMONY_ID,
        "minimum_external_anchors": 2,
        "signature_algorithm": "ED25519",
        "signature_domain": RATIFICATION_DOMAIN,
        "required_roots": [
            "ceremony_root",
            "constitution_root_before",
            "constitution_root_after",
            "rollback_root",
            "challenge_disposition_root",
            "checkpoint_root",
        ],
        "anchor_independence_law": (
            "anchor IDs, keys, institutions, checkpoint references, and "
            "checkpoint roots are unique; anchor institutions are external "
            "to all participant institutions"
        ),
        "historical_law": (
            "activation never rewrites prior signatures; later revocation is "
            "evaluated against its effective time"
        ),
        "truth_effect": "GOVERNANCE_REGISTRY_ONLY",
    }
    return {**body, "contract_digest": digest(body)}


def create_governance_challenge(
    role: str,
    *,
    authority_registry_digest: str,
    handoff_bundle_root: str,
    issued_at: str,
    expires_at: str,
    nonce: str | None = None,
) -> GovernanceChallenge:
    if role not in ROLES:
        raise ValueError(f"unknown governance role: {role}")
    challenge_nonce = nonce or secrets.token_hex(32)
    if not NONCE.fullmatch(challenge_nonce):
        raise ValueError("challenge nonce must be 32 random bytes in hex")
    if _parse_time(issued_at) >= _parse_time(expires_at):
        raise ValueError("challenge expiry must follow issuance")
    if not SHA256.fullmatch(authority_registry_digest):
        raise ValueError("invalid authority registry digest")
    if not SHA256.fullmatch(handoff_bundle_root):
        raise ValueError("invalid handoff bundle root")
    return GovernanceChallenge(
        challenge_id=_challenge_id(role, challenge_nonce, issued_at),
        ceremony_id=CEREMONY_ID,
        epoch_id=ACTIVE_EPOCH_ID,
        role=role,
        governance_contract_digest=governance_ceremony_contract()[
            "contract_digest"
        ],
        authority_registry_digest=authority_registry_digest,
        handoff_bundle_root=handoff_bundle_root,
        nonce=challenge_nonce,
        issued_at=issued_at,
        expires_at=expires_at,
    )


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def verify_enrollment_response(
    response: GovernanceEnrollmentResponse,
    *,
    verified_at: str,
) -> dict[str, Any]:
    challenge = response.challenge
    member = response.member
    signature_valid = False
    public_key_valid = False
    time_valid = False
    try:
        checked = _parse_time(verified_at)
        issued = _parse_time(challenge.issued_at)
        expires = _parse_time(challenge.expires_at)
        member_before = (
            _parse_time(member.not_before)
            if member.not_before is not None
            else None
        )
        member_after = (
            _parse_time(member.not_after)
            if member.not_after is not None
            else None
        )
        time_valid = (
            issued < expires
            and issued <= checked <= expires
            and (member_before is None or checked >= member_before)
            and (member_after is None or checked <= member_after)
        )
        public = base64.b64decode(member.public_key_b64, validate=True)
        public_key_valid = len(public) == 32
        signature = base64.b64decode(
            response.signature_b64,
            validate=True,
        )
        if public_key_valid:
            Ed25519PublicKey.from_public_bytes(public).verify(
                signature,
                enrollment_signing_bytes(response),
            )
            signature_valid = True
    except (
        ValueError,
        TypeError,
        binascii.Error,
        InvalidSignature,
    ):
        signature_valid = False
    roots = (
        response.identity_claim_root,
        response.institution_root,
        response.lineage_root,
        response.external_identity_verification_root,
        response.conflict_disclosure_root,
        response.consent_root,
    )
    conflict_resolved = (
        response.conflict_status == "CLEAR"
        and response.conflict_resolution_root is None
    ) or (
        response.conflict_status == "RESOLVED"
        and response.conflict_resolution_root is not None
        and bool(SHA256.fullmatch(response.conflict_resolution_root))
    )
    checks = {
        "response_id_present": bool(response.response_id.strip()),
        "challenge_identity_exact": (
            challenge.ceremony_id == CEREMONY_ID
            and challenge.epoch_id == ACTIVE_EPOCH_ID
            and challenge.governance_contract_digest
            == governance_ceremony_contract()["contract_digest"]
        ),
        "challenge_nonce_valid": bool(NONCE.fullmatch(challenge.nonce)),
        "challenge_id_exact": challenge.challenge_id
        == _challenge_id(
            challenge.role,
            challenge.nonce,
            challenge.issued_at,
        ),
        "challenge_roots_valid": bool(
            SHA256.fullmatch(challenge.authority_registry_digest)
        )
        and bool(SHA256.fullmatch(challenge.handoff_bundle_root)),
        "challenge_time_and_member_time_valid": time_valid,
        "role_exact": challenge.role in ROLES
        and member.role == challenge.role,
        "member_active": member.status == "ACTIVE",
        "member_independent": member.independent,
        "member_not_test_only": not member.test_only,
        "member_algorithm": member.algorithm == "ED25519",
        "public_key_valid": public_key_valid,
        "attestation_roots_valid": all(
            bool(SHA256.fullmatch(root)) for root in roots
        ),
        "conflict_disposed": conflict_resolved,
        "boundary_exact": response.boundary_claim
        == "PARTICIPANT_CONSENT_NOT_SELF_RATIFICATION",
        "proof_of_possession": signature_valid,
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.GovernanceEnrollmentVerification.V10",
        "response_id": response.response_id,
        "challenge_id": challenge.challenge_id,
        "member_id": member.member_id,
        "role": member.role,
        "verdict": verdict,
        "status": (
            "VERIFIED_PENDING_SOCIETY_ASSEMBLY"
            if verdict == "PASS"
            else "ENROLLMENT_HOLD"
        ),
        "checks": checks,
        "governance_activated": False,
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def assemble_pending_society(
    responses: list[GovernanceEnrollmentResponse]
    | tuple[GovernanceEnrollmentResponse, ...],
    *,
    verified_at: str,
) -> dict[str, Any]:
    ordered_responses = sorted(
        responses,
        key=lambda response: ROLES.index(response.member.role)
        if response.member.role in ROLES
        else len(ROLES),
    )
    reports = [
        verify_enrollment_response(response, verified_at=verified_at)
        for response in ordered_responses
    ]
    members = [response.member for response in ordered_responses]
    roles = [member.role for member in members]
    challenge_ids = [
        response.challenge.challenge_id for response in ordered_responses
    ]
    nonces = [response.challenge.nonce for response in ordered_responses]
    response_ids = [
        response.response_id for response in ordered_responses
    ]
    member_ids = [member.member_id for member in members]
    public_keys = [member.public_key_b64 for member in members]
    institutions = [
        response.institution_root for response in ordered_responses
    ]
    lineages = [response.lineage_root for response in ordered_responses]
    checks = {
        "five_responses_exact": len(responses) == GOVERNANCE_MEMBER_COUNT,
        "all_responses_verified": len(reports) == GOVERNANCE_MEMBER_COUNT
        and all(report["verdict"] == "PASS" for report in reports),
        "roles_exact": set(roles) == set(ROLES)
        and len(roles) == len(set(roles)),
        "challenge_ids_unique": len(challenge_ids)
        == len(set(challenge_ids)),
        "challenge_nonces_unique": len(nonces) == len(set(nonces)),
        "response_ids_unique": len(response_ids) == len(set(response_ids)),
        "member_ids_unique": len(member_ids) == len(set(member_ids)),
        "public_keys_unique": len(public_keys) == len(set(public_keys)),
        "institutions_unique": len(institutions)
        == len(set(institutions)),
        "lineages_unique": len(lineages) == len(set(lineages)),
        "authority_registry_bound": len(
            {
                response.challenge.authority_registry_digest
                for response in ordered_responses
            }
        )
        == 1,
        "handoff_bundle_bound": len(
            {
                response.challenge.handoff_bundle_root
                for response in ordered_responses
            }
        )
        == 1,
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    response_digests = [
        digest(response.to_dict()) for response in ordered_responses
    ]
    pending_registry = (
        seal_governance_registry(members) if verdict == "PASS" else None
    )
    authority_registry_digest = (
        ordered_responses[0].challenge.authority_registry_digest
        if verdict == "PASS"
        else None
    )
    handoff_bundle_root = (
        ordered_responses[0].challenge.handoff_bundle_root
        if verdict == "PASS"
        else None
    )
    assembled_at = verified_at
    ceremony_body = {
        "ceremony_id": CEREMONY_ID,
        "epoch_id": ACTIVE_EPOCH_ID,
        "response_digests": response_digests,
        "roles": list(ROLES),
        "authority_registry_digest": authority_registry_digest,
        "handoff_bundle_root": handoff_bundle_root,
        "participant_institution_roots": institutions,
        "participant_lineage_roots": lineages,
        "governance_registry_digest": (
            pending_registry["registry_digest"]
            if pending_registry is not None
            else None
        ),
        "assembled_at": assembled_at,
    }
    ceremony_root = digest(ceremony_body)
    body = {
        "schema": "KC144.PendingGovernanceSociety.V10",
        "ceremony_id": CEREMONY_ID,
        "epoch_id": ACTIVE_EPOCH_ID,
        "verdict": verdict,
        "status": (
            "READY_FOR_EXTERNAL_RATIFICATION"
            if verdict == "PASS"
            else "ASSEMBLY_HOLD"
        ),
        "checks": checks,
        "response_reports": reports,
        "response_digests": response_digests,
        "authority_registry_digest": authority_registry_digest,
        "handoff_bundle_root": handoff_bundle_root,
        "participant_institution_roots": institutions,
        "participant_lineage_roots": lineages,
        "ceremony_root": ceremony_root,
        "pending_registry": pending_registry,
        "governance_registry_digest": (
            pending_registry["registry_digest"]
            if pending_registry is not None
            else None
        ),
        "assembled_at": assembled_at,
        "governance_activated": False,
        "truth_effect": "NONE",
    }
    return {**body, "assembly_digest": digest(body)}


def pending_society_integrity(
    pending_society: Mapping[str, Any],
) -> bool:
    try:
        registry = pending_society["pending_registry"]
        response_digests = list(pending_society["response_digests"])
        institutions = list(
            pending_society["participant_institution_roots"]
        )
        lineages = list(pending_society["participant_lineage_roots"])
        members = [
            GovernanceMember.from_dict(value)
            for value in registry["members"]
        ]
        _parse_time(pending_society["assembled_at"])
    except (KeyError, TypeError, ValueError):
        return False
    assembly_body = {
        key: value
        for key, value in pending_society.items()
        if key != "assembly_digest"
    }
    ceremony_body = {
        "ceremony_id": pending_society.get("ceremony_id"),
        "epoch_id": pending_society.get("epoch_id"),
        "response_digests": response_digests,
        "roles": list(ROLES),
        "authority_registry_digest": pending_society.get(
            "authority_registry_digest"
        ),
        "handoff_bundle_root": pending_society.get(
            "handoff_bundle_root"
        ),
        "participant_institution_roots": institutions,
        "participant_lineage_roots": lineages,
        "governance_registry_digest": pending_society.get(
            "governance_registry_digest"
        ),
        "assembled_at": pending_society.get("assembled_at"),
    }
    return (
        pending_society.get("schema")
        == "KC144.PendingGovernanceSociety.V10"
        and pending_society.get("ceremony_id") == CEREMONY_ID
        and pending_society.get("epoch_id") == ACTIVE_EPOCH_ID
        and pending_society.get("verdict") == "PASS"
        and pending_society.get("status")
        == "READY_FOR_EXTERNAL_RATIFICATION"
        and pending_society.get("governance_activated") is False
        and pending_society.get("truth_effect") == "NONE"
        and governance_registry_integrity(registry)
        and len(response_digests) == GOVERNANCE_MEMBER_COUNT
        and len(response_digests) == len(set(response_digests))
        and all(bool(SHA256.fullmatch(root)) for root in response_digests)
        and len(institutions) == GOVERNANCE_MEMBER_COUNT
        and len(institutions) == len(set(institutions))
        and all(bool(SHA256.fullmatch(root)) for root in institutions)
        and len(lineages) == GOVERNANCE_MEMBER_COUNT
        and len(lineages) == len(set(lineages))
        and all(bool(SHA256.fullmatch(root)) for root in lineages)
        and len(members) == GOVERNANCE_MEMBER_COUNT
        and [member.role for member in members] == list(ROLES)
        and all(
            member.status == "ACTIVE"
            and member.independent
            and not member.test_only
            for member in members
        )
        and bool(
            SHA256.fullmatch(
                str(pending_society.get("authority_registry_digest"))
            )
        )
        and bool(
            SHA256.fullmatch(
                str(pending_society.get("handoff_bundle_root"))
            )
        )
        and pending_society.get("governance_registry_digest")
        == registry.get("registry_digest")
        and pending_society.get("ceremony_root") == digest(ceremony_body)
        and pending_society.get("assembly_digest") == digest(assembly_body)
    )


def _members_current(
    pending_society: Mapping[str, Any],
    checked: datetime,
) -> bool:
    try:
        members = [
            GovernanceMember.from_dict(value)
            for value in pending_society["pending_registry"]["members"]
        ]
        for member in members:
            not_before = (
                _parse_time(member.not_before)
                if member.not_before is not None
                else None
            )
            not_after = (
                _parse_time(member.not_after)
                if member.not_after is not None
                else None
            )
            if (
                (not_before is not None and checked < not_before)
                or (not_after is not None and checked > not_after)
            ):
                return False
    except (KeyError, TypeError, ValueError):
        return False
    return True


def verify_governance_ratification(
    pending_society: Mapping[str, Any],
    ratification: GovernanceRatification,
    *,
    verified_at: str,
) -> dict[str, Any]:
    anchor_reports = []
    valid_anchors = []
    participant_institutions = set(
        pending_society.get("participant_institution_roots", ())
    )
    for anchor in ratification.anchors:
        signature_valid = False
        time_valid = False
        public_key_valid = False
        try:
            public = base64.b64decode(
                anchor.public_key_b64,
                validate=True,
            )
            public_key_valid = len(public) == 32
            checked = _parse_time(verified_at)
            observed = _parse_time(anchor.observed_at)
            ratified = _parse_time(ratification.ratified_at)
            time_valid = ratified <= observed <= checked
            signature = base64.b64decode(
                anchor.signature_b64,
                validate=True,
            )
            if public_key_valid:
                Ed25519PublicKey.from_public_bytes(public).verify(
                    signature,
                    ratification_signing_bytes(ratification, anchor),
                )
                signature_valid = True
        except (
            ValueError,
            TypeError,
            binascii.Error,
            InvalidSignature,
        ):
            signature_valid = False
        valid = (
            anchor.algorithm == "ED25519"
            and public_key_valid
            and signature_valid
            and time_valid
            and bool(anchor.anchor_id)
            and bool(anchor.checkpoint_ref)
            and bool(SHA256.fullmatch(anchor.institution_root))
            and bool(SHA256.fullmatch(anchor.checkpoint_root))
            and anchor.institution_root not in participant_institutions
        )
        if valid:
            valid_anchors.append(anchor)
        anchor_reports.append(
            {
                "anchor_id": anchor.anchor_id,
                "public_key_valid": public_key_valid,
                "signature_valid": signature_valid,
                "time_valid": time_valid,
                "external_to_participants": anchor.institution_root
                not in participant_institutions,
                "counted": valid,
            }
        )
    anchor_ids = [anchor.anchor_id for anchor in valid_anchors]
    anchor_keys = [anchor.public_key_b64 for anchor in valid_anchors]
    anchor_institutions = [
        anchor.institution_root for anchor in valid_anchors
    ]
    anchor_checkpoint_refs = [
        anchor.checkpoint_ref for anchor in valid_anchors
    ]
    anchor_checkpoint_roots = [
        anchor.checkpoint_root for anchor in valid_anchors
    ]
    try:
        closed = _parse_time(ratification.challenge_window_closed_at)
        ratified = _parse_time(ratification.ratified_at)
        checked = _parse_time(verified_at)
        assembled = _parse_time(str(pending_society["assembled_at"]))
        window_valid = assembled <= closed <= ratified <= checked
        members_current = _members_current(pending_society, checked)
    except (KeyError, ValueError, TypeError):
        window_valid = False
        members_current = False
    checks = {
        "pending_society_integrity": pending_society_integrity(
            pending_society
        ),
        "ratification_id_present": bool(
            ratification.ratification_id.strip()
        ),
        "ceremony_root_exact": ratification.ceremony_root
        == pending_society.get("ceremony_root"),
        "members_current": members_current,
        "constitution_transition": bool(
            SHA256.fullmatch(ratification.constitution_root_before)
        )
        and bool(SHA256.fullmatch(ratification.constitution_root_after))
        and ratification.constitution_root_before
        != ratification.constitution_root_after,
        "rollback_root_valid": bool(
            SHA256.fullmatch(ratification.rollback_root)
        ),
        "challenge_disposition_valid": bool(
            SHA256.fullmatch(ratification.challenge_disposition_root)
        ),
        "challenge_window_closed": window_valid,
        "two_external_anchors": len(valid_anchors) >= 2,
        "anchor_ids_unique": len(anchor_ids) == len(set(anchor_ids)),
        "anchor_keys_unique": len(anchor_keys) == len(set(anchor_keys)),
        "anchor_institutions_unique": len(anchor_institutions)
        == len(set(anchor_institutions)),
        "anchor_checkpoint_refs_unique": len(anchor_checkpoint_refs)
        == len(set(anchor_checkpoint_refs)),
        "anchor_checkpoint_roots_unique": len(anchor_checkpoint_roots)
        == len(set(anchor_checkpoint_roots)),
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.GovernanceRatificationVerification.V10",
        "ratification_id": ratification.ratification_id,
        "verdict": verdict,
        "status": (
            "RATIFIED_FOR_ACTIVATION"
            if verdict == "PASS"
            else "RATIFICATION_HOLD"
        ),
        "checks": checks,
        "valid_anchor_ids": sorted(anchor_ids),
        "anchor_reports": anchor_reports,
        "governance_activated": False,
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def activate_governance_society(
    pending_society: Mapping[str, Any],
    ratification: GovernanceRatification,
    *,
    verified_at: str,
) -> dict[str, Any]:
    verification = verify_governance_ratification(
        pending_society,
        ratification,
        verified_at=verified_at,
    )
    if verification["verdict"] != "PASS":
        return {
            "schema": "KC144.GovernanceActivation.V10",
            "status": "HOLD",
            "verification": verification,
            "governance_registry": None,
            "governance_activated": False,
            "truth_effect": "NONE",
        }
    registry = pending_society["pending_registry"]
    body = {
        "schema": "KC144.GovernanceActivation.V10",
        "status": "ACTIVATED",
        "verification": verification,
        "governance_registry": registry,
        "governance_registry_digest": registry["registry_digest"],
        "constitution_root": ratification.constitution_root_after,
        "rollback_root": ratification.rollback_root,
        "ratification": ratification.to_dict(),
        "governance_activated": True,
        "truth_effect": "GOVERNANCE_REGISTRY_ONLY",
    }
    return {
        **body,
        "activation_digest": digest(
            {
                key: value
                for key, value in body.items()
                if key != "governance_registry"
            }
        ),
    }


def governance_ceremony_plan(
    *,
    authority_registry_digest: str,
    handoff_bundle_root: str,
) -> dict[str, Any]:
    contract = governance_ceremony_contract()
    seats = [
        {
            "seat": index,
            "role": role,
            "status": "AWAITING_EXTERNAL_PARTICIPANT",
            "challenge_command": (
                f"governance-challenge --role {role} "
                f"--authority-registry-digest "
                f"{authority_registry_digest} "
                f"--handoff-bundle-root {handoff_bundle_root} "
                "--issued-at <RFC3339> --expires-at <RFC3339>"
            ),
            "required_response": (
                "SIGNED_GOVERNANCE_ENROLLMENT_RESPONSE_V10"
            ),
        }
        for index, role in enumerate(ROLES, start=1)
    ]
    body = {
        "schema": "KC144.GovernanceCeremonyPlan.V10",
        "ceremony_id": CEREMONY_ID,
        "ceremony_contract_digest": contract["contract_digest"],
        "governance_contract_digest": threshold_governance_contract()[
            "contract_digest"
        ],
        "authority_registry_digest": authority_registry_digest,
        "handoff_bundle_root": handoff_bundle_root,
        "seats": seats,
        "filled_seats": 0,
        "required_seats": GOVERNANCE_MEMBER_COUNT,
        "status": "AWAITING_EXTERNAL_PARTICIPANTS",
        "barrier": "FIVE_INDEPENDENT_PARTICIPANT_RESPONSES_REQUIRED",
        "next_seed": "KC144.V10::ISSUE-FIVE-ROLE-BOUND-CHALLENGES",
    }
    return {**body, "plan_digest": digest(body)}
