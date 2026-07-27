from __future__ import annotations

import base64
import binascii
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from .crosswalk import ACTIVE_EPOCH_CENSUS, ACTIVE_EPOCH_ID
from .evidence_v7 import (
    AuthorityKey,
    SignedEvidenceEnvelope,
    admit_signed_envelope,
    authority_registry_integrity,
    seal_authority_registry,
    verify_signed_envelope,
)
from .population import canonical_json, digest
from .repair import (
    evidence_packet_contract,
    evidence_summary,
    verify_repair_ledger,
)


CAMPAIGN_ID = "KC144.M12.PARALLEL.CAMPAIGN.V8"
CAMPAIGN_PHASES = ("A_FRONTIER", "B_DEFECT", "C_PROMOTION")
ENROLLMENT_BOUNDARY = "POSSESSION_ONLY_NOT_AUTHORITY_APPROVAL"


@dataclass(frozen=True)
class AuthorityEnrollmentProof:
    request_id: str
    epoch_id: str
    nonce: str
    issued_at: str
    key: AuthorityKey
    boundary_claim: str
    signature_b64: str

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuthorityEnrollmentProof":
        body = dict(value)
        body.pop("schema", None)
        body["key"] = AuthorityKey.from_dict(body["key"])
        return cls(**body)

    def signing_body(self) -> dict[str, Any]:
        body = asdict(self)
        body["schema"] = "KC144.AuthorityEnrollmentProof.V8"
        body.pop("signature_b64")
        return body

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "KC144.AuthorityEnrollmentProof.V8",
            **asdict(self),
        }


def enrollment_signing_bytes(proof: AuthorityEnrollmentProof) -> bytes:
    return canonical_json(proof.signing_body()).encode("utf-8")


def authority_enrollment_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.AuthorityEnrollmentContract.V8",
        "epoch_id": ACTIVE_EPOCH_ID,
        "algorithm": "ED25519",
        "proof_fields": [
            "request_id",
            "epoch_id",
            "nonce",
            "issued_at",
            "key",
            "boundary_claim",
            "signature_b64",
        ],
        "required_boundary_claim": ENROLLMENT_BOUNDARY,
        "cryptographic_effect": "PROVES_PRIVATE_KEY_POSSESSION",
        "governance_effect": "NONE",
        "pinning_law": (
            "a valid proof of possession is necessary but never sufficient "
            "for authority enrollment; an external governance decision must "
            "pin the key into the production registry"
        ),
        "anti_self_authorization_law": (
            "the candidate key cannot approve its own independence, evidence "
            "standing, or production authority"
        ),
    }
    return {**body, "contract_digest": digest(body)}


def verify_authority_enrollment(
    proof: AuthorityEnrollmentProof,
) -> dict[str, Any]:
    signature_valid = False
    public_key_valid = False
    try:
        public_bytes = base64.b64decode(
            proof.key.public_key_b64,
            validate=True,
        )
        public_key_valid = len(public_bytes) == 32
        signature = base64.b64decode(proof.signature_b64, validate=True)
        if public_key_valid:
            Ed25519PublicKey.from_public_bytes(public_bytes).verify(
                signature,
                enrollment_signing_bytes(proof),
            )
            signature_valid = True
    except (
        ValueError,
        TypeError,
        binascii.Error,
        InvalidSignature,
    ):
        signature_valid = False

    try:
        candidate_registry_valid = authority_registry_integrity(
            seal_authority_registry([proof.key])
        )
    except ValueError:
        candidate_registry_valid = False
    issued_at_valid = False
    issued_inside_key_interval = False
    try:
        issued = datetime.fromisoformat(
            proof.issued_at.replace("Z", "+00:00")
        )
        if issued.tzinfo is None:
            raise ValueError("timezone required")
        not_before = (
            datetime.fromisoformat(
                proof.key.not_before.replace("Z", "+00:00")
            )
            if proof.key.not_before is not None
            else None
        )
        not_after = (
            datetime.fromisoformat(
                proof.key.not_after.replace("Z", "+00:00")
            )
            if proof.key.not_after is not None
            else None
        )
        issued_at_valid = True
        issued_inside_key_interval = (
            (not_before is None or issued >= not_before)
            and (not_after is None or issued <= not_after)
        )
    except (AttributeError, TypeError, ValueError):
        issued_at_valid = False
    checks = {
        "request_id_present": bool(proof.request_id.strip()),
        "epoch_exact": proof.epoch_id == ACTIVE_EPOCH_ID,
        "nonce_bounded": len(proof.nonce.strip()) >= 16,
        "issued_at_valid": issued_at_valid,
        "issued_inside_key_interval": issued_inside_key_interval,
        "boundary_exact": proof.boundary_claim == ENROLLMENT_BOUNDARY,
        "candidate_key_well_formed": candidate_registry_valid,
        "candidate_active": proof.key.status == "ACTIVE",
        "candidate_independence_claim": proof.key.independent,
        "candidate_production_namespace": "PRODUCTION"
        in proof.key.namespaces,
        "candidate_not_test_only": not proof.key.test_only,
        "public_key_valid": public_key_valid,
        "proof_of_possession": signature_valid,
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.AuthorityEnrollmentVerification.V8",
        "request_id": proof.request_id,
        "key_id": proof.key.key_id,
        "verdict": verdict,
        "status": (
            "PROOF_VALID_AWAITING_EXTERNAL_GOVERNANCE_PIN"
            if verdict == "PASS"
            else "INELIGIBLE"
        ),
        "checks": checks,
        "registry_mutated": False,
        "authority_granted": False,
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def _shard(
    shard_id: str,
    phase: str,
    evidence_kind: str,
    coordinate: str,
    subjects: list[str],
    dependencies: list[str],
) -> dict[str, Any]:
    return {
        "shard_id": shard_id,
        "phase": phase,
        "evidence_kind": evidence_kind,
        "coordinate": coordinate,
        "subject_ids": subjects,
        "packet_count": len(subjects),
        "dependencies": dependencies,
        "execution": (
            "PARALLEL_READY_SUBGRAPH"
            if phase == "A_FRONTIER"
            else "DEPENDENCY_BOUND"
        ),
        "atomicity": "SHARD_ENVELOPE_ALL_PACKETS_OR_NONE",
    }


def _campaign_shards() -> list[dict[str, Any]]:
    targets = evidence_packet_contract()["targets"]
    domain = targets["DOMAIN_POPULATION"]["subject_ids"]
    conflict_ids = {"GID063", "GID070", "GID073"}
    frontier = [
        _shard(
            "A_BRIDGE_ALL",
            "A_FRONTIER",
            "BRIDGE_CERTIFICATION",
            "BR28",
            targets["BRIDGE_CERTIFICATION"]["subject_ids"],
            [],
        ),
        _shard(
            "A_DOMAIN_F37_CLEAR",
            "A_FRONTIER",
            "DOMAIN_POPULATION",
            "F37:CLEAR",
            [
                subject
                for subject in domain
                if 55 <= int(subject[3:]) <= 79
                and subject not in conflict_ids
            ],
            [],
        ),
        _shard(
            "A_DOMAIN_F37_ADJUDICATED",
            "A_FRONTIER",
            "DOMAIN_POPULATION",
            "F37:ADJUDICATED",
            sorted(conflict_ids),
            [],
        ),
        _shard(
            "A_DOMAIN_KC15",
            "A_FRONTIER",
            "DOMAIN_POPULATION",
            "KC15",
            [
                subject
                for subject in domain
                if 91 <= int(subject[3:]) <= 105
            ],
            [],
        ),
        _shard(
            "A_DOMAIN_KC27",
            "A_FRONTIER",
            "DOMAIN_POPULATION",
            "KC27",
            [
                subject
                for subject in domain
                if 106 <= int(subject[3:]) <= 132
            ],
            [],
        ),
        _shard(
            "A_DOMAIN_SSN12",
            "A_FRONTIER",
            "DOMAIN_POPULATION",
            "SSN12",
            [
                subject
                for subject in domain
                if 133 <= int(subject[3:]) <= 144
            ],
            [],
        ),
    ]
    replay_ranges = (
        ("H6", 1, 6),
        ("X16", 7, 22),
        ("O21", 23, 43),
        ("F37", 44, 80),
        ("C10", 81, 90),
        ("KC15", 91, 105),
        ("KC27", 106, 132),
        ("SSN12", 133, 144),
    )
    frontier.extend(
        _shard(
            f"A_REPLAY_{name}",
            "A_FRONTIER",
            "INDEPENDENT_REPLAY",
            name,
            [f"GID{gid:03d}" for gid in range(start, end + 1)],
            [],
        )
        for name, start, end in replay_ranges
    )
    frontier_ids = [row["shard_id"] for row in frontier]
    defect = _shard(
        "B_DEFECT_CLOSURE",
        "B_DEFECT",
        "DEFECT_CLOSURE",
        "M12:DEFECT",
        targets["DEFECT_CLOSURE"]["subject_ids"],
        frontier_ids,
    )
    promotion = _shard(
        "C_IC10_PROMOTION",
        "C_PROMOTION",
        "IC10_PROMOTION",
        "SSN12:IC10",
        targets["IC10_PROMOTION"]["subject_ids"],
        [defect["shard_id"]],
    )
    return [*frontier, defect, promotion]


def campaign_manifest() -> dict[str, Any]:
    shards = _campaign_shards()
    topology = {
        "campaign_id": CAMPAIGN_ID,
        "epoch_id": ACTIVE_EPOCH_ID,
        "epoch_census": ACTIVE_EPOCH_CENSUS,
        "phases": list(CAMPAIGN_PHASES),
        "shards": shards,
    }
    topology_root = digest(topology)
    body = {
        "schema": "KC144.ParallelCampaignManifest.V8",
        **topology,
        "topology_root": topology_root,
        "shard_count": len(shards),
        "packet_count": sum(row["packet_count"] for row in shards),
        "maximum_parallel_width": sum(
            row["phase"] == "A_FRONTIER" for row in shards
        ),
        "packet_binding": {
            "campaign_id": CAMPAIGN_ID,
            "campaign_topology_root": topology_root,
            "campaign_shard_id": "EXACT_SHARD_ID",
        },
        "hologram": {
            "ID": CAMPAIGN_ID,
            "Coordinate": ACTIVE_EPOCH_ID,
            "Kernel": "KC144.PRODUCTION.EVIDENCE.KERNEL.V7",
            "Delta": "SIGNED_APPEND_ONLY_EVIDENCE_OVERLAY",
            "Routes": list(CAMPAIGN_PHASES),
            "Boundary": "EXTERNAL_AUTHORITY_AND_INDEPENDENT_EVIDENCE",
            "Return": "V7_ENVELOPE_RECEIPTS_PLUS_SUBJECT_RECEIPTS",
            "Seed": "KC144.V8::RUN-READY-SUBGRAPH-TO-BARRIER",
        },
        "laws": [
            "run every ready shard in parallel and stop only at a true barrier",
            "sources may fan out but every subject retains an individual receipt",
            "a shard envelope is atomic and cannot straddle campaign shards",
            "TEST completion never changes production truth",
            "IC10 alone may record successor promotion",
        ],
    }
    return {**body, "manifest_digest": digest(body)}


def _eligible_authority_ids(
    registry: Mapping[str, Any],
    namespace: str,
) -> list[str]:
    if not authority_registry_integrity(registry):
        return []
    revoked = set(registry.get("revoked_key_ids", ()))
    return sorted(
        key["key_id"]
        for key in registry.get("keys", ())
        if key.get("status") == "ACTIVE"
        and key.get("key_id") not in revoked
        and key.get("independent") is True
        and namespace in key.get("namespaces", ())
        and not (namespace == "PRODUCTION" and key.get("test_only"))
    )


def campaign_state(
    ledger: Mapping[str, Any],
    authority_registry: Mapping[str, Any],
) -> dict[str, Any]:
    manifest = campaign_manifest()
    shard_by_id = {
        shard["shard_id"]: shard for shard in manifest["shards"]
    }
    admitted = {
        (
            record.get("packet", {}).get("kind"),
            record.get("packet", {}).get("subject_id"),
        )
        for record in ledger.get("records", ())
    }
    complete_ids: set[str] = set()
    shard_states = []
    eligible_keys = _eligible_authority_ids(
        authority_registry,
        str(ledger.get("namespace")),
    )
    for phase in CAMPAIGN_PHASES:
        for shard in manifest["shards"]:
            if shard["phase"] != phase:
                continue
            expected = {
                (shard["evidence_kind"], subject)
                for subject in shard["subject_ids"]
            }
            complete = expected <= admitted
            dependencies_complete = set(shard["dependencies"]) <= complete_ids
            if complete:
                status = "COMPLETE"
                complete_ids.add(shard["shard_id"])
            elif not dependencies_complete:
                status = "BLOCKED_BY_DEPENDENCY"
            elif not eligible_keys:
                status = "EXTERNAL_AUTHORITY_BARRIER"
            else:
                status = "AWAITING_SIGNED_ENVELOPE"
            shard_states.append(
                {
                    "shard_id": shard["shard_id"],
                    "phase": phase,
                    "status": status,
                    "admitted_packets": len(expected & admitted),
                    "required_packets": len(expected),
                    "remaining_packets": len(expected - admitted),
                    "dependencies": shard["dependencies"],
                }
            )

    complete = len(complete_ids) == manifest["shard_count"]
    structurally_ready = [
        row["shard_id"]
        for row in shard_states
        if row["status"]
        in {"EXTERNAL_AUTHORITY_BARRIER", "AWAITING_SIGNED_ENVELOPE"}
    ]
    actionable = [
        row["shard_id"]
        for row in shard_states
        if row["status"] == "AWAITING_SIGNED_ENVELOPE"
    ]
    if verify_repair_ledger(ledger)["verdict"] != "PASS":
        barrier = "INVALID_REPAIR_LEDGER"
    elif not authority_registry_integrity(authority_registry):
        barrier = "INVALID_AUTHORITY_REGISTRY"
    elif complete:
        barrier = (
            "PRODUCTION_CAMPAIGN_COMPLETE"
            if ledger.get("namespace") == "PRODUCTION"
            else "TEST_CAMPAIGN_COMPLETE_NO_PRODUCTION_EFFECT"
        )
    elif structurally_ready and not eligible_keys:
        barrier = "EXTERNAL_AUTHORITY_PIN_REQUIRED"
    else:
        barrier = "SIGNED_EVIDENCE_REQUIRED"
    summary = evidence_summary(ledger)
    body = {
        "schema": "KC144.ParallelCampaignState.V8",
        "campaign_id": CAMPAIGN_ID,
        "campaign_manifest_digest": manifest["manifest_digest"],
        "namespace": ledger.get("namespace"),
        "ledger_digest": ledger.get("ledger_digest"),
        "authority_registry_digest": authority_registry.get(
            "registry_digest"
        ),
        "eligible_authority_ids": eligible_keys,
        "completed_shards": len(complete_ids),
        "total_shards": manifest["shard_count"],
        "admitted_campaign_packets": sum(
            row["admitted_packets"] for row in shard_states
        ),
        "total_campaign_packets": manifest["packet_count"],
        "structurally_ready_shards": structurally_ready,
        "actionable_shards": actionable,
        "shards": shard_states,
        "barrier": barrier,
        "observed_state": summary["observed_state"],
        "production_effective_state": summary["production_effective_state"],
        "production_truth_effect": summary["production_truth_effect"],
        "frozen_crystal_mutated": False,
        "next_seed": (
            "KC144.V2::POPULATE_MATH144"
            if barrier == "PRODUCTION_CAMPAIGN_COMPLETE"
            else "KC144.V8::TEST-CAMPAIGN-COMPLETE-NO-PROMOTION"
            if barrier == "TEST_CAMPAIGN_COMPLETE_NO_PRODUCTION_EFFECT"
            else "KC144.V8::PIN-EXTERNAL-GOVERNANCE-TRUST-ANCHOR"
            if barrier == "EXTERNAL_AUTHORITY_PIN_REQUIRED"
            else "KC144.V8::SUPPLY-READY-SHARD-ENVELOPES"
        ),
    }
    return {**body, "state_digest": digest(body)}


def validate_campaign_envelope(
    shard_id: str,
    envelope: SignedEvidenceEnvelope,
    ledger: Mapping[str, Any],
    authority_registry: Mapping[str, Any],
) -> dict[str, Any]:
    manifest = campaign_manifest()
    shard = next(
        (
            row
            for row in manifest["shards"]
            if row["shard_id"] == shard_id
        ),
        None,
    )
    state = campaign_state(ledger, authority_registry)
    state_by_id = {row["shard_id"]: row for row in state["shards"]}
    packet_ids = [packet.packet_id for packet in envelope.packets]
    evidence_roots = [packet.evidence_root for packet in envelope.packets]
    actual_subjects = [packet.subject_id for packet in envelope.packets]
    expected_subjects = shard["subject_ids"] if shard else []
    v7_verification = verify_signed_envelope(
        envelope,
        authority_registry,
        ledger,
    )
    checks = {
        "shard_known": shard is not None,
        "shard_ready": bool(
            shard
            and state_by_id[shard_id]["status"]
            == "AWAITING_SIGNED_ENVELOPE"
        ),
        "packet_count_exact": bool(
            shard and len(envelope.packets) == shard["packet_count"]
        ),
        "evidence_kind_exact": bool(
            shard
            and all(
                packet.kind == shard["evidence_kind"]
                for packet in envelope.packets
            )
        ),
        "subjects_exact": bool(
            shard
            and len(actual_subjects) == len(set(actual_subjects))
            and set(actual_subjects) == set(expected_subjects)
        ),
        "packet_ids_unique": len(packet_ids) == len(set(packet_ids)),
        "evidence_roots_unique": len(evidence_roots)
        == len(set(evidence_roots)),
        "campaign_packet_binding": bool(
            shard
            and all(
                packet.payload.get("campaign_id") == CAMPAIGN_ID
                and packet.payload.get("campaign_topology_root")
                == manifest["topology_root"]
                and packet.payload.get("campaign_shard_id") == shard_id
                for packet in envelope.packets
            )
        ),
        "v7_envelope_verification": v7_verification["verdict"] == "PASS",
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.CampaignEnvelopeVerification.V8",
        "campaign_id": CAMPAIGN_ID,
        "shard_id": shard_id,
        "envelope_id": envelope.envelope_id,
        "verdict": verdict,
        "checks": checks,
        "v7_verification": v7_verification,
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def _numeric_delta(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: (
            int(after[key]) - int(before[key])
            if isinstance(before[key], (int, bool))
            and isinstance(after[key], (int, bool))
            else {"before": before[key], "after": after[key]}
        )
        for key in before
    }


def run_to_barrier(
    ledger: Mapping[str, Any],
    authority_registry: Mapping[str, Any],
    envelopes: Mapping[str, SignedEvidenceEnvelope],
) -> dict[str, Any]:
    manifest = campaign_manifest()
    known_shards = {
        shard["shard_id"] for shard in manifest["shards"]
    }
    working = dict(ledger)
    before = evidence_summary(working)
    pending = dict(envelopes)
    unknown_shards = sorted(set(pending) - known_shards)
    for shard_id in unknown_shards:
        pending.pop(shard_id)
    receipts = []

    for phase in CAMPAIGN_PHASES:
        phase_shards = [
            shard["shard_id"]
            for shard in manifest["shards"]
            if shard["phase"] == phase
        ]
        state = campaign_state(working, authority_registry)
        state_by_id = {row["shard_id"]: row for row in state["shards"]}
        for shard_id in phase_shards:
            envelope = pending.get(shard_id)
            if envelope is None:
                continue
            if (
                state_by_id[shard_id]["status"]
                != "AWAITING_SIGNED_ENVELOPE"
            ):
                continue
            verification = validate_campaign_envelope(
                shard_id,
                envelope,
                working,
                authority_registry,
            )
            if verification["verdict"] != "PASS":
                receipts.append(
                    {
                        "shard_id": shard_id,
                        "status": "HOLD",
                        "verification": verification,
                        "records_admitted": 0,
                    }
                )
                pending.pop(shard_id)
                continue
            admission = admit_signed_envelope(
                working,
                envelope,
                authority_registry,
            )
            receipts.append(
                {
                    "shard_id": shard_id,
                    "status": admission["status"],
                    "verification": verification,
                    "records_admitted": admission["records_admitted"],
                    **(
                        {"envelope_digest": admission["envelope_digest"]}
                        if admission["status"] == "ADMITTED"
                        else {}
                    ),
                }
            )
            pending.pop(shard_id)
            if admission["status"] == "ADMITTED":
                working = admission["ledger"]

    after = evidence_summary(working)
    final_state = campaign_state(working, authority_registry)
    held = [row["shard_id"] for row in receipts if row["status"] == "HOLD"]
    deferred = sorted(pending)
    body = {
        "schema": "KC144.RunToBarrierReport.V8",
        "campaign_id": CAMPAIGN_ID,
        "campaign_manifest_digest": manifest["manifest_digest"],
        "status": (
            "COMPLETE"
            if final_state["completed_shards"] == manifest["shard_count"]
            else "BARRIER"
        ),
        "initial_ledger_digest": ledger.get("ledger_digest"),
        "final_ledger_digest": working.get("ledger_digest"),
        "receipts": receipts,
        "admitted_shards": [
            row["shard_id"]
            for row in receipts
            if row["status"] == "ADMITTED"
        ],
        "held_shards": held,
        "unknown_shards": unknown_shards,
        "deferred_shards": deferred,
        "net_delta": {
            "observed_state": _numeric_delta(
                before["observed_state"],
                after["observed_state"],
            ),
            "production_effective_state": _numeric_delta(
                before["production_effective_state"],
                after["production_effective_state"],
            ),
        },
        "barrier": final_state["barrier"],
        "next_seed": final_state["next_seed"],
        "production_truth_effect": after["production_truth_effect"],
        "frozen_crystal_mutated": False,
    }
    return {
        **body,
        "report_digest": digest(body),
        "ledger": working,
        "campaign_state": final_state,
    }
