from __future__ import annotations

import base64
import binascii
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .campaign_v8 import (
    AuthorityEnrollmentProof,
    campaign_manifest,
    campaign_state,
    run_to_barrier,
    verify_authority_enrollment,
)
from .crosswalk import ACTIVE_EPOCH_ID, compile_coordinate_crosswalk, graph_slice_registry
from .evidence_v7 import (
    AuthorityKey,
    SignedEvidenceEnvelope,
    authority_registry_integrity,
    seal_authority_registry,
)
from .population import canonical_json, digest
from .repair import verify_repair_ledger


GOVERNANCE_ID = "KC144.THRESHOLD.GOVERNANCE.V9"
HANDOFF_ID = "KC144.EXTERNAL.HANDOFF.V9"
GOVERNANCE_MEMBER_COUNT = 5
GOVERNANCE_THRESHOLD = 3
SHA256 = re.compile(r"^sha256:[0-9a-f]{64}$")
FORBIDDEN_PRODUCTION_MARKERS = (
    "synthetic",
    "fixture",
    "placeholder",
    "example",
    "tbd",
)


@dataclass(frozen=True)
class GovernanceMember:
    member_id: str
    algorithm: str
    public_key_b64: str
    role: str
    status: str
    independent: bool
    test_only: bool
    not_before: str | None = None
    not_after: str | None = None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernanceMember":
        return cls(**dict(value))


@dataclass(frozen=True)
class GovernanceApproval:
    member_id: str
    signature_b64: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GovernanceApproval":
        return cls(**dict(value))


@dataclass(frozen=True)
class AuthorityPinProposal:
    proposal_id: str
    epoch_id: str
    governance_registry_digest: str
    authority_registry_digest: str
    issued_at: str
    expires_at: str
    candidate_proof: AuthorityEnrollmentProof
    approvals: tuple[GovernanceApproval, ...]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuthorityPinProposal":
        body = dict(value)
        body.pop("schema", None)
        body["candidate_proof"] = AuthorityEnrollmentProof.from_dict(
            body["candidate_proof"]
        )
        body["approvals"] = tuple(
            GovernanceApproval.from_dict(approval)
            for approval in body.get("approvals", ())
        )
        return cls(**body)

    def signing_body(self) -> dict[str, Any]:
        body = asdict(self)
        body["schema"] = "KC144.AuthorityPinProposal.V9"
        body.pop("approvals")
        return body

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "KC144.AuthorityPinProposal.V9",
            **asdict(self),
        }


def governance_signing_bytes(proposal: AuthorityPinProposal) -> bytes:
    domain = {
        "signature_domain": "KC144.V9.AUTHORITY_PIN",
        "proposal": proposal.signing_body(),
    }
    return canonical_json(domain).encode("utf-8")


def empty_governance_registry() -> dict[str, Any]:
    body = {
        "schema": "KC144.ThresholdGovernanceRegistry.V9",
        "governance_id": GOVERNANCE_ID,
        "epoch_id": ACTIVE_EPOCH_ID,
        "required_members": GOVERNANCE_MEMBER_COUNT,
        "threshold": GOVERNANCE_THRESHOLD,
        "members": [],
        "revoked_member_ids": [],
        "revocation_log": [],
        "law": (
            "no single key, reviewer, witness, institution, or lineage may "
            "grant durable production authority"
        ),
    }
    return {**body, "registry_digest": digest(body)}


def seal_governance_registry(
    members: list[GovernanceMember] | tuple[GovernanceMember, ...],
    *,
    revoked_member_ids: list[str] | tuple[str, ...] = (),
    revocation_log: list[Mapping[str, Any]]
    | tuple[Mapping[str, Any], ...] = (),
) -> dict[str, Any]:
    if len(members) not in {0, GOVERNANCE_MEMBER_COUNT}:
        raise ValueError("governance registry requires zero or five members")
    member_ids = [member.member_id for member in members]
    public_keys = [member.public_key_b64 for member in members]
    if (
        any(not member_id for member_id in member_ids)
        or len(member_ids) != len(set(member_ids))
        or len(public_keys) != len(set(public_keys))
    ):
        raise ValueError("governance identities and public keys must be unique")
    revoked = sorted(set(revoked_member_ids))
    body = {
        "schema": "KC144.ThresholdGovernanceRegistry.V9",
        "governance_id": GOVERNANCE_ID,
        "epoch_id": ACTIVE_EPOCH_ID,
        "required_members": GOVERNANCE_MEMBER_COUNT,
        "threshold": GOVERNANCE_THRESHOLD,
        "members": [asdict(member) for member in members],
        "revoked_member_ids": revoked,
        "revocation_log": [dict(row) for row in revocation_log],
        "law": (
            "no single key, reviewer, witness, institution, or lineage may "
            "grant durable production authority"
        ),
    }
    return {**body, "registry_digest": digest(body)}


def threshold_governance_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.ThresholdGovernanceContract.V9",
        "governance_id": GOVERNANCE_ID,
        "epoch_id": ACTIVE_EPOCH_ID,
        "member_count": GOVERNANCE_MEMBER_COUNT,
        "threshold": GOVERNANCE_THRESHOLD,
        "signature_algorithm": "ED25519",
        "signature_domain": "KC144.V9.AUTHORITY_PIN",
        "roles": [
            "CUSTODIAN",
            "INDEPENDENT_REVIEWER",
            "REPLAY_WITNESS",
            "SOURCE_AUDITOR",
            "RETURN_AUDITOR",
        ],
        "revocation": "APPEND_ONLY_TRANSPARENT_LOG",
        "candidate_law": (
            "the candidate must first pass V8 proof-of-possession and cannot "
            "sign a governance approval for itself"
        ),
        "quorum_law": (
            "three distinct active independent non-test governance members "
            "must sign the same domain-separated proposal bytes"
        ),
        "truth_effect": "NONE_UNTIL_QUORUM_AND_PIN",
    }
    return {**body, "contract_digest": digest(body)}


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def _member_well_formed(member: GovernanceMember) -> bool:
    try:
        public = base64.b64decode(member.public_key_b64, validate=True)
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
    except (ValueError, TypeError, binascii.Error):
        return False
    return (
        bool(member.member_id)
        and member.algorithm == "ED25519"
        and len(public) == 32
        and bool(member.role)
        and member.status in {"ACTIVE", "REVOKED", "EXPIRED"}
        and isinstance(member.independent, bool)
        and isinstance(member.test_only, bool)
        and (
            not_before is None
            or not_after is None
            or not_before <= not_after
        )
    )


def governance_registry_integrity(registry: Mapping[str, Any]) -> bool:
    body = {
        key: value
        for key, value in registry.items()
        if key != "registry_digest"
    }
    raw_members = registry.get("members", ())
    revoked = registry.get("revoked_member_ids", ())
    log = registry.get("revocation_log", ())
    if (
        not isinstance(raw_members, (list, tuple))
        or not isinstance(revoked, (list, tuple))
        or not isinstance(log, (list, tuple))
    ):
        return False
    try:
        members = [
            GovernanceMember.from_dict(member) for member in raw_members
        ]
    except (TypeError, ValueError):
        return False
    member_ids = [member.member_id for member in members]
    public_keys = [member.public_key_b64 for member in members]
    revoked_set = set(revoked)
    log_ids = [row.get("event_id") for row in log if isinstance(row, Mapping)]
    return (
        registry.get("schema")
        == "KC144.ThresholdGovernanceRegistry.V9"
        and registry.get("governance_id") == GOVERNANCE_ID
        and registry.get("epoch_id") == ACTIVE_EPOCH_ID
        and registry.get("required_members") == GOVERNANCE_MEMBER_COUNT
        and registry.get("threshold") == GOVERNANCE_THRESHOLD
        and len(members) in {0, GOVERNANCE_MEMBER_COUNT}
        and all(_member_well_formed(member) for member in members)
        and len(member_ids) == len(set(member_ids))
        and len(public_keys) == len(set(public_keys))
        and len(revoked) == len(revoked_set)
        and len(log_ids) == len(log)
        and len(log_ids) == len(set(log_ids))
        and all(
            (member.member_id in revoked_set)
            == (member.status == "REVOKED")
            for member in members
        )
        and registry.get("registry_digest") == digest(body)
    )


def verify_authority_pin_proposal(
    proposal: AuthorityPinProposal,
    governance_registry: Mapping[str, Any],
    authority_registry: Mapping[str, Any],
    *,
    verified_at: str,
) -> dict[str, Any]:
    candidate_report = verify_authority_enrollment(
        proposal.candidate_proof
    )
    members = {
        member.member_id: member
        for member in (
            GovernanceMember.from_dict(row)
            for row in governance_registry.get("members", ())
        )
    }
    revoked = set(governance_registry.get("revoked_member_ids", ()))
    valid_approvers: list[str] = []
    approval_reports = []
    signing_bytes = governance_signing_bytes(proposal)
    for approval in proposal.approvals:
        member = members.get(approval.member_id)
        signature_valid = False
        time_valid = False
        if member is not None:
            try:
                public = base64.b64decode(
                    member.public_key_b64,
                    validate=True,
                )
                signature = base64.b64decode(
                    approval.signature_b64,
                    validate=True,
                )
                Ed25519PublicKey.from_public_bytes(public).verify(
                    signature,
                    signing_bytes,
                )
                signature_valid = True
                checked = _parse_time(verified_at)
                time_valid = (
                    (
                        member.not_before is None
                        or checked >= _parse_time(member.not_before)
                    )
                    and (
                        member.not_after is None
                        or checked <= _parse_time(member.not_after)
                    )
                )
            except (
                ValueError,
                TypeError,
                binascii.Error,
                InvalidSignature,
            ):
                signature_valid = False
        valid = bool(
            member
            and member.status == "ACTIVE"
            and member.member_id not in revoked
            and member.independent
            and not member.test_only
            and member.member_id
            != proposal.candidate_proof.key.key_id
            and signature_valid
            and time_valid
        )
        if valid and approval.member_id not in valid_approvers:
            valid_approvers.append(approval.member_id)
        approval_reports.append(
            {
                "member_id": approval.member_id,
                "resolved": member is not None,
                "signature_valid": signature_valid,
                "time_valid": time_valid,
                "counted": valid
                and approval.member_id in valid_approvers,
            }
        )
    try:
        issued = _parse_time(proposal.issued_at)
        expires = _parse_time(proposal.expires_at)
        checked = _parse_time(verified_at)
        proposal_time_valid = issued <= checked <= expires
    except (ValueError, TypeError):
        proposal_time_valid = False
    checks = {
        "governance_registry_integrity": governance_registry_integrity(
            governance_registry
        ),
        "authority_registry_integrity": authority_registry_integrity(
            authority_registry
        ),
        "proposal_id_present": bool(proposal.proposal_id.strip()),
        "epoch_exact": proposal.epoch_id == ACTIVE_EPOCH_ID,
        "governance_registry_bound": proposal.governance_registry_digest
        == governance_registry.get("registry_digest"),
        "authority_registry_bound": proposal.authority_registry_digest
        == authority_registry.get("registry_digest"),
        "candidate_possession_verified": candidate_report["verdict"]
        == "PASS",
        "proposal_time_valid": proposal_time_valid,
        "approval_member_ids_unique": len(proposal.approvals)
        == len({approval.member_id for approval in proposal.approvals}),
        "threshold_met": len(valid_approvers) >= GOVERNANCE_THRESHOLD,
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.AuthorityPinVerification.V9",
        "proposal_id": proposal.proposal_id,
        "candidate_key_id": proposal.candidate_proof.key.key_id,
        "verdict": verdict,
        "status": (
            "AUTHORIZED_TO_PIN"
            if verdict == "PASS"
            else "THRESHOLD_OR_POLICY_HOLD"
        ),
        "checks": checks,
        "valid_approvers": sorted(valid_approvers),
        "approval_reports": approval_reports,
        "candidate_verification": candidate_report,
        "threshold": GOVERNANCE_THRESHOLD,
        "authority_registry_mutated": False,
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def pin_authority_from_proposal(
    proposal: AuthorityPinProposal,
    governance_registry: Mapping[str, Any],
    authority_registry: Mapping[str, Any],
    *,
    verified_at: str,
) -> dict[str, Any]:
    verification = verify_authority_pin_proposal(
        proposal,
        governance_registry,
        authority_registry,
        verified_at=verified_at,
    )
    if verification["verdict"] != "PASS":
        return {
            "schema": "KC144.AuthorityPinAdmission.V9",
            "status": "HOLD",
            "verification": verification,
            "registry": dict(authority_registry),
            "authority_pinned": False,
            "truth_effect": "NONE",
        }
    existing = [
        AuthorityKey.from_dict(key)
        for key in authority_registry.get("keys", ())
    ]
    candidate = proposal.candidate_proof.key
    if any(key.key_id == candidate.key_id for key in existing):
        return {
            "schema": "KC144.AuthorityPinAdmission.V9",
            "status": "HOLD",
            "verification": verification,
            "reason": "DUPLICATE_AUTHORITY_KEY_ID",
            "registry": dict(authority_registry),
            "authority_pinned": False,
            "truth_effect": "NONE",
        }
    registry = seal_authority_registry(
        [*existing, candidate],
        revoked_key_ids=authority_registry.get("revoked_key_ids", ()),
    )
    body = {
        "schema": "KC144.AuthorityPinAdmission.V9",
        "status": "PINNED",
        "verification": verification,
        "registry": registry,
        "authority_pinned": True,
        "pinned_key_id": candidate.key_id,
        "truth_effect": "AUTHORITY_REGISTRY_ONLY",
    }
    return {
        **body,
        "admission_digest": digest(
            {key: value for key, value in body.items() if key != "registry"}
        ),
    }


def source_harvest_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.SourceHarvestContract.V9",
        "harvest_law": (
            "one immutable source object is acquired and hashed once, then "
            "fanned out through individually witnessed subject claims"
        ),
        "source_fields": [
            "source_id",
            "source_ref",
            "content_digest",
            "acquired_at",
            "provenance_root",
            "independent",
        ],
        "claim_fields": [
            "subject_id",
            "extraction_digest",
            "relevance_digest",
            "residual_state",
        ],
        "residual_states": [
            "NONE",
            "VALUE_MISSING",
            "CARRIER_UNRESOLVED",
            "SEMANTICS_CONTESTED",
            "SOURCE_INACCESSIBLE",
            "BOUNDARY_UNTESTED",
            "RETURN_UNVERIFIED",
            "ORDER_UNTESTED",
        ],
        "contamination_laws": [
            "LATEST_WINS_FORBIDDEN",
            "NO_BRANCH_ERASURE",
            "NO_SOURCE_INFLATION",
            "NO_AESTHETIC_PROMOTION",
            "NO_MISSING_MEASUREMENT_AS_ZERO",
            "NO_PRODUCTION_FIXTURE_OR_PLACEHOLDER",
        ],
        "truth_effect": "NONE_UNTIL_SIGNED_ENVELOPE_ADMISSION",
    }
    return {**body, "contract_digest": digest(body)}


def handoff_bundle(ledger: Mapping[str, Any]) -> dict[str, Any]:
    manifest = campaign_manifest()
    crosswalk = compile_coordinate_crosswalk()
    graph = graph_slice_registry()
    algebra = next(
        row
        for row in graph["slices"]
        if row["slice_id"] == graph["active_frozen_slice"]
    )
    payload_fields = {
        "BRIDGE_CERTIFICATION": [
            "bridge_id",
            "standing",
            "commit_digest",
            "transport_evaluation_digest",
            "return_witness_root",
        ],
        "DOMAIN_POPULATION": [
            "gid",
            "source_object_id",
            "content_digest",
            "carrier",
            "coordinate_binding",
        ],
        "INDEPENDENT_REPLAY": [
            "gid",
            "expected_state_root",
            "replayed_state_root",
            "result",
        ],
        "DEFECT_CLOSURE": [
            "defect_id",
            "result",
            "closure_root",
        ],
        "IC10_PROMOTION": [
            "candidate_id",
            "decision",
            "state_root",
            "gate_vector",
            "constitutional_gate_vector",
            "immune_gate_vector",
            "successor_seed",
        ],
    }
    requests = []
    for shard in manifest["shards"]:
        request_body = {
            "schema": "KC144.ExternalHandoffRequest.V9",
            "request_id": f"V9-REQUEST::{shard['shard_id']}",
            "handoff_id": HANDOFF_ID,
            "campaign_id": manifest["campaign_id"],
            "campaign_topology_root": manifest["topology_root"],
            "campaign_shard_id": shard["shard_id"],
            "phase": shard["phase"],
            "namespace": ledger.get("namespace"),
            "epoch_id": ACTIVE_EPOCH_ID,
            "frozen_base_root": ledger.get("frozen_base", {}).get(
                "state_root"
            ),
            "crosswalk_digest": crosswalk["crosswalk_digest"],
            "graph_slice": graph["active_frozen_slice"],
            "graph_slice_digest": algebra["slice_digest"],
            "evidence_kind": shard["evidence_kind"],
            "subject_ids": shard["subject_ids"],
            "packet_count": shard["packet_count"],
            "dependencies": shard["dependencies"],
            "required_payload_fields": [
                *payload_fields[shard["evidence_kind"]],
                *(
                    [
                        "adjudication_status",
                        "adjudication_receipt_root",
                    ]
                    if shard["shard_id"]
                    == "A_DOMAIN_F37_ADJUDICATED"
                    else []
                ),
                "campaign_id",
                "campaign_topology_root",
                "campaign_shard_id",
                "handoff_bundle_root",
                "handoff_request_digest",
                "source_manifest_root",
                "source_claim_root",
            ],
            "source_requirement": (
                "HARVEST_ONCE_FAN_OUT_WITH_INDIVIDUAL_CLAIM_RECEIPTS"
            ),
            "return_format": "SIGNED_V7_ENVELOPE_BOUND_TO_V9_REQUEST",
            "truth_effect": "NONE",
        }
        requests.append(
            {
                **request_body,
                "request_digest": digest(request_body),
            }
        )
    bundle_index = {
        "handoff_id": HANDOFF_ID,
        "campaign_manifest_digest": manifest["manifest_digest"],
        "ledger_digest": ledger.get("ledger_digest"),
        "request_digests": [
            request["request_digest"] for request in requests
        ],
    }
    bundle_root = digest(bundle_index)
    body = {
        "schema": "KC144.ExternalHandoffBundle.V9",
        "handoff_id": HANDOFF_ID,
        "campaign_id": manifest["campaign_id"],
        "campaign_manifest_digest": manifest["manifest_digest"],
        "campaign_topology_root": manifest["topology_root"],
        "namespace": ledger.get("namespace"),
        "ledger_digest": ledger.get("ledger_digest"),
        "request_count": len(requests),
        "packet_count": sum(
            request["packet_count"] for request in requests
        ),
        "requests": requests,
        "bundle_root": bundle_root,
        "signing_instruction": (
            "populate only from independently acquired evidence, bind every "
            "packet to this bundle and its request digest, then sign the V7 "
            "envelope with a threshold-pinned authority key"
        ),
        "return_instruction": (
            "return envelopes by campaign shard ID; failed or missing claims "
            "must return typed residuals, never guessed values"
        ),
    }
    return {**body, "bundle_digest": digest(body)}


def verify_source_harvest(
    source_manifest: Mapping[str, Any],
    bundle: Mapping[str, Any],
) -> dict[str, Any]:
    allowed_subjects = {
        subject
        for request in bundle.get("requests", ())
        for subject in request.get("subject_ids", ())
    }
    claims = source_manifest.get("claims", ())
    claim_subjects = [
        claim.get("subject_id")
        for claim in claims
        if isinstance(claim, Mapping)
    ]
    source_ref = str(source_manifest.get("source_ref", ""))
    production = bundle.get("namespace") == "PRODUCTION"
    checks = {
        "schema_exact": source_manifest.get("schema")
        == "KC144.SourceHarvestManifest.V9",
        "source_id_present": bool(
            str(source_manifest.get("source_id", "")).strip()
        ),
        "source_ref_present": bool(source_ref.strip()),
        "content_digest": bool(
            SHA256.fullmatch(
                str(source_manifest.get("content_digest", ""))
            )
        ),
        "acquired_at_present": bool(
            str(source_manifest.get("acquired_at", "")).strip()
        ),
        "provenance_root": bool(
            SHA256.fullmatch(
                str(source_manifest.get("provenance_root", ""))
            )
        ),
        "independent": source_manifest.get("independent") is True,
        "claims_present": isinstance(claims, (list, tuple))
        and bool(claims),
        "claim_subjects_unique": len(claim_subjects)
        == len(set(claim_subjects)),
        "claim_subjects_allowed": bool(claim_subjects)
        and set(claim_subjects) <= allowed_subjects,
        "claims_typed": all(
            isinstance(claim, Mapping)
            and bool(
                SHA256.fullmatch(
                    str(claim.get("extraction_digest", ""))
                )
            )
            and bool(
                SHA256.fullmatch(
                    str(claim.get("relevance_digest", ""))
                )
            )
            and claim.get("residual_state")
            in source_harvest_contract()["residual_states"]
            for claim in claims
        ),
        "production_contamination_absent": not production
        or not any(
            marker in source_ref.lower()
            for marker in FORBIDDEN_PRODUCTION_MARKERS
        ),
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.SourceHarvestVerification.V9",
        "source_id": source_manifest.get("source_id"),
        "verdict": verdict,
        "checks": checks,
        "source_claim_count": len(claims),
        "source_object_count": 1,
        "fanout_preserved": len(claims),
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def _handoff_binding_checks(
    shard_id: str,
    envelope: SignedEvidenceEnvelope,
    bundle: Mapping[str, Any],
) -> dict[str, bool]:
    request = next(
        (
            row
            for row in bundle.get("requests", ())
            if row.get("campaign_shard_id") == shard_id
        ),
        None,
    )
    production = bundle.get("namespace") == "PRODUCTION"
    return {
        "request_known": request is not None,
        "packet_count_exact": bool(
            request
            and len(envelope.packets) == request["packet_count"]
        ),
        "subjects_exact": bool(
            request
            and {packet.subject_id for packet in envelope.packets}
            == set(request["subject_ids"])
            and len(envelope.packets)
            == len({packet.subject_id for packet in envelope.packets})
        ),
        "handoff_binding_exact": bool(
            request
            and all(
                packet.payload.get("handoff_bundle_root")
                == bundle.get("bundle_root")
                and packet.payload.get("handoff_request_digest")
                == request["request_digest"]
                for packet in envelope.packets
            )
        ),
        "source_roots_present": all(
            bool(
                SHA256.fullmatch(
                    str(packet.payload.get("source_manifest_root", ""))
                )
            )
            and bool(
                SHA256.fullmatch(
                    str(packet.payload.get("source_claim_root", ""))
                )
            )
            for packet in envelope.packets
        ),
        "production_source_refs_clean": not production
        or all(
            not any(
                marker in packet.source_ref.lower()
                for marker in FORBIDDEN_PRODUCTION_MARKERS
            )
            for packet in envelope.packets
        ),
    }


def run_handoff_to_barrier(
    ledger: Mapping[str, Any],
    authority_registry: Mapping[str, Any],
    envelopes: Mapping[str, SignedEvidenceEnvelope],
) -> dict[str, Any]:
    bundle = handoff_bundle(ledger)
    valid_envelopes: dict[str, SignedEvidenceEnvelope] = {}
    handoff_receipts = []
    for shard_id, envelope in envelopes.items():
        checks = _handoff_binding_checks(shard_id, envelope, bundle)
        status = "PASS" if all(checks.values()) else "HOLD"
        handoff_receipts.append(
            {
                "shard_id": shard_id,
                "envelope_id": envelope.envelope_id,
                "status": status,
                "checks": checks,
            }
        )
        if status == "PASS":
            valid_envelopes[shard_id] = envelope
    campaign_report = run_to_barrier(
        ledger,
        authority_registry,
        valid_envelopes,
    )
    handoff_holds = sorted(
        row["shard_id"]
        for row in handoff_receipts
        if row["status"] == "HOLD"
    )
    body = {
        "schema": "KC144.ExternalHandoffRunReport.V9",
        "handoff_id": HANDOFF_ID,
        "bundle_root": bundle["bundle_root"],
        "bundle_digest": bundle["bundle_digest"],
        "status": (
            "COMPLETE"
            if campaign_report["status"] == "COMPLETE"
            and not handoff_holds
            else "BARRIER"
        ),
        "handoff_receipts": handoff_receipts,
        "handoff_held_shards": handoff_holds,
        "campaign_report_digest": campaign_report["report_digest"],
        "campaign_barrier": campaign_report["barrier"],
        "final_ledger_digest": campaign_report["final_ledger_digest"],
        "production_truth_effect": campaign_report[
            "production_truth_effect"
        ],
        "frozen_crystal_mutated": False,
        "next_seed": campaign_report["next_seed"],
    }
    return {
        **body,
        "report_digest": digest(body),
        "ledger": campaign_report["ledger"],
        "campaign_report": campaign_report,
    }


def handoff_state(
    ledger: Mapping[str, Any],
    authority_registry: Mapping[str, Any],
    governance_registry: Mapping[str, Any],
) -> dict[str, Any]:
    bundle = handoff_bundle(ledger)
    campaign = campaign_state(ledger, authority_registry)
    governance_valid = governance_registry_integrity(
        governance_registry
    )
    active_governors = [
        member
        for member in governance_registry.get("members", ())
        if member.get("status") == "ACTIVE"
        and member.get("member_id")
        not in governance_registry.get("revoked_member_ids", ())
        and member.get("independent") is True
        and member.get("test_only") is False
    ]
    if verify_repair_ledger(ledger)["verdict"] != "PASS":
        barrier = "INVALID_REPAIR_LEDGER"
    elif not governance_valid:
        barrier = "INVALID_GOVERNANCE_REGISTRY"
    elif len(active_governors) < GOVERNANCE_MEMBER_COUNT:
        barrier = "THRESHOLD_GOVERNANCE_MEMBERS_REQUIRED"
    elif not authority_registry_integrity(authority_registry):
        barrier = "INVALID_AUTHORITY_REGISTRY"
    elif not campaign["eligible_authority_ids"]:
        barrier = "THRESHOLD_AUTHORITY_PIN_REQUIRED"
    else:
        barrier = campaign["barrier"]
    body = {
        "schema": "KC144.ExternalHandoffState.V9",
        "handoff_id": HANDOFF_ID,
        "bundle_root": bundle["bundle_root"],
        "bundle_digest": bundle["bundle_digest"],
        "namespace": ledger.get("namespace"),
        "ledger_digest": ledger.get("ledger_digest"),
        "governance_registry_digest": governance_registry.get(
            "registry_digest"
        ),
        "authority_registry_digest": authority_registry.get(
            "registry_digest"
        ),
        "active_governance_members": len(active_governors),
        "governance_threshold": GOVERNANCE_THRESHOLD,
        "eligible_campaign_authorities": campaign[
            "eligible_authority_ids"
        ],
        "campaign_completed_shards": campaign["completed_shards"],
        "campaign_total_shards": campaign["total_shards"],
        "barrier": barrier,
        "production_truth_effect": campaign["production_truth_effect"],
        "frozen_crystal_mutated": False,
        "next_seed": (
            "KC144.V9::ENROLL-FIVE-INDEPENDENT-GOVERNANCE-MEMBERS"
            if barrier == "THRESHOLD_GOVERNANCE_MEMBERS_REQUIRED"
            else "KC144.V9::THRESHOLD-PIN-PRODUCTION-AUTHORITY"
            if barrier == "THRESHOLD_AUTHORITY_PIN_REQUIRED"
            else campaign["next_seed"]
        ),
    }
    return {**body, "state_digest": digest(body)}
