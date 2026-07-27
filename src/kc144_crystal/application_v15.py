from __future__ import annotations

import base64
import binascii
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PublicKey,
)

from .ceremony_v10 import ROLES
from .dispatch_v11 import challenge_batch_integrity
from .nomination_v14 import (
    SignedCandidateNomination,
    nomination_call_manifest,
    nomination_call_manifest_integrity,
    nomination_role_call_integrity,
    verify_signed_candidate_nomination,
)
from .population import canonical_json, digest


TRANSPORT_ID = "KC144.CANDIDATE.APPLICATION.TRANSPORT.V15"
APPLICATION_SIGNATURE_DOMAIN = (
    "KC144.V15.BATCH_BOUND_CANDIDATE_APPLICATION"
)


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


@dataclass(frozen=True)
class CandidateCallBinding:
    role: str
    call_id: str
    call_digest: str

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "CandidateCallBinding":
        return cls(**dict(value))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BatchBoundCandidateApplication:
    application_id: str
    nomination_envelope: SignedCandidateNomination
    batch_id: str
    batch_root: str
    call_manifest_root: str
    target_calls: tuple[CandidateCallBinding, ...]
    submitted_at: str
    signature_domain: str
    signature_b64: str

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
    ) -> "BatchBoundCandidateApplication":
        body = dict(value)
        body.pop("schema", None)
        body["nomination_envelope"] = (
            SignedCandidateNomination.from_dict(
                body["nomination_envelope"]
            )
        )
        body["target_calls"] = tuple(
            CandidateCallBinding.from_dict(binding)
            for binding in body["target_calls"]
        )
        return cls(**body)

    def signing_body(self) -> dict[str, Any]:
        return {
            "schema": "KC144.BatchBoundCandidateApplication.V15",
            "application_id": self.application_id,
            "nomination_envelope": self.nomination_envelope.to_dict(),
            "batch_id": self.batch_id,
            "batch_root": self.batch_root,
            "call_manifest_root": self.call_manifest_root,
            "target_calls": [
                binding.to_dict() for binding in self.target_calls
            ],
            "submitted_at": self.submitted_at,
            "signature_domain": self.signature_domain,
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.signing_body(),
            "signature_b64": self.signature_b64,
        }


def application_signing_bytes(
    application: BatchBoundCandidateApplication,
) -> bytes:
    return canonical_json(application.signing_body()).encode("utf-8")


def application_transport_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.ApplicationTransportContract.V15",
        "transport_id": TRANSPORT_ID,
        "roles": list(ROLES),
        "publication_payload_count": 5,
        "application_schema": (
            "KC144.BatchBoundCandidateApplication.V15"
        ),
        "signature_algorithm": "ED25519",
        "signature_domain": APPLICATION_SIGNATURE_DOMAIN,
        "double_signature_law": (
            "the inner V14 signature binds the nomination declaration and "
            "the outer V15 signature binds that exact signed declaration "
            "to one immutable batch, manifest, role-call set, and time"
        ),
        "role_binding_law": (
            "the application target roles must equal the declared eligible "
            "roles and every call identifier and digest must equal the "
            "canonical V14 call for the active batch"
        ),
        "replay_law": (
            "an otherwise valid application from another batch, call "
            "manifest, or role-call digest is non-counting"
        ),
        "publication_law": (
            "payload compilation is not external publication; publication "
            "requires independently observed transport evidence"
        ),
        "evidence_law": (
            "both signatures establish key control and byte integrity only, "
            "not identity, independence, publication, fitness, or authority"
        ),
        "routing_law": (
            "only unique valid applications release their inner envelopes "
            "to V14; every rejected application remains in the V15 ledger"
        ),
        "truth_effect": "NONE",
    }
    return {**body, "contract_digest": digest(body)}


def application_publication_payload(
    batch: Mapping[str, Any],
    call: Mapping[str, Any],
    call_manifest: Mapping[str, Any],
) -> dict[str, Any]:
    if not challenge_batch_integrity(batch):
        raise ValueError("challenge batch integrity failure")
    if not nomination_role_call_integrity(batch, call):
        raise ValueError("role call integrity failure")
    role = str(call["role"])
    row = next(
        (
            value
            for value in call_manifest["call_rows"]
            if value["role"] == role
        ),
        None,
    )
    if (
        row is None
        or row["call_id"] != call["call_id"]
        or row["call_digest"] != call["call_digest"]
    ):
        raise ValueError("call manifest binding failure")
    seed = {
        "transport_id": TRANSPORT_ID,
        "batch_root": batch["batch_root"],
        "call_manifest_root": call_manifest["manifest_root"],
        "call_digest": call["call_digest"],
    }
    body = {
        "schema": "KC144.ApplicationPublicationPayload.V15",
        "transport_id": TRANSPORT_ID,
        "payload_id": (
            f"V15-PAYLOAD::{role}::{digest(seed)[7:23]}"
        ),
        "role": role,
        "batch_id": batch["batch_id"],
        "batch_root": batch["batch_root"],
        "call_manifest_root": call_manifest["manifest_root"],
        "call_id": call["call_id"],
        "call_digest": call["call_digest"],
        "call": dict(call),
        "transport_contract_digest": application_transport_contract()[
            "contract_digest"
        ],
        "application_schema": (
            "KC144.BatchBoundCandidateApplication.V15"
        ),
        "signature_algorithm": "ED25519",
        "signature_domain": APPLICATION_SIGNATURE_DOMAIN,
        "audience": "EXTERNAL_INDEPENDENT_CANDIDATE_POOL",
        "content_type": "application/vnd.kc144.role-call+json",
        "response_instruction": (
            "return one double-signed V15 application bound to this batch, "
            "manifest, and every eligible-role call"
        ),
        "boundary_claim": (
            "PREPARED_PAYLOAD_IS_NOT_PUBLICATION_OR_DELIVERY"
        ),
        "publication_state": "READY_UNPUBLISHED",
        "external_locator_root": None,
        "publication_receipt_root": None,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {**body, "payload_digest": digest(body)}


def application_publication_payload_integrity(
    batch: Mapping[str, Any],
    call: Mapping[str, Any],
    call_manifest: Mapping[str, Any],
    payload: Mapping[str, Any],
) -> bool:
    try:
        expected = application_publication_payload(
            batch,
            call,
            call_manifest,
        )
    except (KeyError, TypeError, ValueError, StopIteration):
        return False
    return dict(payload) == expected


def application_publication_manifest(
    batch: Mapping[str, Any],
    call_manifest: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
    payloads: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not nomination_call_manifest_integrity(
        batch,
        call_manifest,
        calls,
    ):
        raise ValueError("call manifest integrity failure")
    calls_by_role = {str(call["role"]): call for call in calls}
    ordered = sorted(
        (dict(payload) for payload in payloads),
        key=lambda payload: ROLES.index(str(payload["role"])),
    )
    if (
        len(ordered) != 5
        or [payload["role"] for payload in ordered] != list(ROLES)
        or not all(
            application_publication_payload_integrity(
                batch,
                calls_by_role[str(payload["role"])],
                call_manifest,
                payload,
            )
            for payload in ordered
        )
    ):
        raise ValueError("five integral publication payloads required")
    rows = [
        {
            "role": payload["role"],
            "payload_id": payload["payload_id"],
            "payload_digest": payload["payload_digest"],
            "call_id": payload["call_id"],
            "call_digest": payload["call_digest"],
            "state": payload["publication_state"],
        }
        for payload in ordered
    ]
    body = {
        "schema": "KC144.ApplicationPublicationManifest.V15",
        "transport_id": TRANSPORT_ID,
        "parent_batch_id": batch["batch_id"],
        "parent_batch_root": batch["batch_root"],
        "call_manifest_root": call_manifest["manifest_root"],
        "transport_contract_digest": application_transport_contract()[
            "contract_digest"
        ],
        "payload_rows": rows,
        "prepared_payload_count": 5,
        "published_payload_count": 0,
        "publication_receipt_count": 0,
        "status": "READY_FOR_EXTERNAL_PUBLICATION",
        "publication_claimed": False,
        "delivery_claimed": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {**body, "manifest_root": digest(body)}


def application_publication_manifest_integrity(
    batch: Mapping[str, Any],
    call_manifest: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
    payloads: Sequence[Mapping[str, Any]],
    manifest: Mapping[str, Any],
) -> bool:
    try:
        expected = application_publication_manifest(
            batch,
            call_manifest,
            calls,
            payloads,
        )
    except (KeyError, TypeError, ValueError, StopIteration):
        return False
    return dict(manifest) == expected


def verify_batch_bound_application(
    batch: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
    call_manifest: Mapping[str, Any],
    application: BatchBoundCandidateApplication,
    *,
    checked_at: str,
) -> dict[str, Any]:
    calls_by_role = {
        str(call["role"]): dict(call)
        for call in calls
        if nomination_role_call_integrity(batch, call)
    }
    inner = verify_signed_candidate_nomination(
        application.nomination_envelope,
        checked_at=checked_at,
    )
    target_roles = [binding.role for binding in application.target_calls]
    eligible_roles = list(
        application.nomination_envelope.nomination.eligible_roles
    )
    target_order_exact = target_roles == [
        role for role in ROLES if role in set(eligible_roles)
    ]
    target_set_exact = (
        bool(target_roles)
        and len(target_roles) == len(set(target_roles))
        and set(target_roles) == set(eligible_roles)
    )
    exact_call_bindings = (
        target_set_exact
        and all(
            binding.role in calls_by_role
            and binding.call_id
            == calls_by_role[binding.role]["call_id"]
            and binding.call_digest
            == calls_by_role[binding.role]["call_digest"]
            for binding in application.target_calls
        )
    )
    timing_valid = False
    observed_by_check = False
    try:
        submitted = _parse_time(application.submitted_at)
        checked = _parse_time(checked_at)
        batch_start = _parse_time(str(batch["issued_at"]))
        batch_end = _parse_time(str(batch["expires_at"]))
        nomination_start = _parse_time(
            application.nomination_envelope.nomination.not_before
        )
        nomination_end = _parse_time(
            application.nomination_envelope.nomination.not_after
        )
        timing_valid = (
            batch_start <= submitted <= batch_end
            and nomination_start <= submitted <= nomination_end
        )
        observed_by_check = submitted <= checked
    except (KeyError, TypeError, ValueError):
        pass
    signature_well_formed = False
    signature_valid = False
    try:
        public_key = base64.b64decode(
            application.nomination_envelope.nomination.public_key_b64,
            validate=True,
        )
        signature = base64.b64decode(
            application.signature_b64,
            validate=True,
        )
        signature_well_formed = len(public_key) == 32 and len(signature) == 64
        if signature_well_formed:
            Ed25519PublicKey.from_public_bytes(public_key).verify(
                signature,
                application_signing_bytes(application),
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
        "application_id_present": bool(
            application.application_id.strip()
        ),
        "batch_integrity": challenge_batch_integrity(batch),
        "call_manifest_integrity": nomination_call_manifest_integrity(
            batch,
            call_manifest,
            calls,
        ),
        "inner_v14_signature_valid": inner["verdict"] == "PASS",
        "batch_id_exact": application.batch_id == batch.get("batch_id"),
        "batch_root_exact": application.batch_root
        == batch.get("batch_root"),
        "call_manifest_root_exact": (
            application.call_manifest_root
            == call_manifest.get("manifest_root")
        ),
        "target_role_set_exact": target_set_exact,
        "target_role_order_canonical": target_order_exact,
        "exact_call_bindings": exact_call_bindings,
        "submitted_within_batch_and_nomination_windows": timing_valid,
        "submission_observed_by_checked_at": observed_by_check,
        "signature_domain_exact": (
            application.signature_domain
            == APPLICATION_SIGNATURE_DOMAIN
        ),
        "outer_signature_well_formed": signature_well_formed,
        "candidate_key_outer_signature_valid": signature_valid,
    }
    verdict = "PASS" if all(checks.values()) else "HOLD"
    body = {
        "schema": "KC144.BatchBoundCandidateApplicationVerification.V15",
        "transport_id": TRANSPORT_ID,
        "application_id": application.application_id,
        "envelope_id": application.nomination_envelope.envelope_id,
        "nomination_id": (
            application.nomination_envelope.nomination.nomination_id
        ),
        "candidate_id": (
            application.nomination_envelope.nomination.candidate_id
        ),
        "target_roles": target_roles,
        "verdict": verdict,
        "status": (
            "BATCH_BOUND_APPLICATION_ADMITTED_TO_V14"
            if verdict == "PASS"
            else "BATCH_BOUND_APPLICATION_HOLD"
        ),
        "checks": checks,
        "inner_verification_digest": inner["verification_digest"],
        "cross_batch_replay_admitted": False,
        "publication_proven": False,
        "identity_independence_externally_proven": False,
        "governance_authority_granted": False,
        "truth_effect": "NONE",
    }
    return {**body, "verification_digest": digest(body)}


def application_receipt_ledger(
    batch: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
    call_manifest: Mapping[str, Any],
    applications: Sequence[BatchBoundCandidateApplication],
    *,
    checked_at: str,
) -> dict[str, Any]:
    ordered = sorted(
        applications,
        key=lambda application: (
            application.nomination_envelope.nomination.candidate_id,
            application.nomination_envelope.nomination.nomination_id,
            application.application_id,
        ),
    )
    identifier_fields = {
        "application_id": [
            item.application_id for item in ordered
        ],
        "envelope_id": [
            item.nomination_envelope.envelope_id for item in ordered
        ],
        "nomination_id": [
            item.nomination_envelope.nomination.nomination_id
            for item in ordered
        ],
        "candidate_id": [
            item.nomination_envelope.nomination.candidate_id
            for item in ordered
        ],
    }
    duplicates = {
        field: sorted(
            {
                value
                for value in values
                if values.count(value) > 1
            }
        )
        for field, values in identifier_fields.items()
    }
    receipts = []
    admitted_envelopes = []
    for application in ordered:
        verification = verify_batch_bound_application(
            batch,
            calls,
            call_manifest,
            application,
            checked_at=checked_at,
        )
        duplicate_collision = any(
            value in duplicates[field]
            for field, value in (
                ("application_id", application.application_id),
                (
                    "envelope_id",
                    application.nomination_envelope.envelope_id,
                ),
                (
                    "nomination_id",
                    application.nomination_envelope.nomination.nomination_id,
                ),
                (
                    "candidate_id",
                    application.nomination_envelope.nomination.candidate_id,
                ),
            )
        )
        admitted = (
            verification["verdict"] == "PASS"
            and not duplicate_collision
        )
        if admitted:
            admitted_envelopes.append(application.nomination_envelope)
        receipt_body = {
            "application_id": application.application_id,
            "envelope_id": application.nomination_envelope.envelope_id,
            "nomination_id": (
                application.nomination_envelope.nomination.nomination_id
            ),
            "candidate_id": (
                application.nomination_envelope.nomination.candidate_id
            ),
            "target_roles": [
                binding.role for binding in application.target_calls
            ],
            "verification_digest": verification[
                "verification_digest"
            ],
            "application_verdict": verification["verdict"],
            "duplicate_collision": duplicate_collision,
            "routing_verdict": "PASS" if admitted else "HOLD",
            "status": (
                "INNER_V14_ENVELOPE_RELEASED"
                if admitted
                else "PRESERVED_NONCOUNTING_APPLICATION"
            ),
            "authority_effect": "NONE",
        }
        receipts.append(
            {
                **receipt_body,
                "receipt_digest": digest(receipt_body),
            }
        )
    admitted_set_root = digest(
        [envelope.to_dict() for envelope in admitted_envelopes]
    )
    body = {
        "schema": "KC144.ApplicationReceiptLedger.V15",
        "transport_id": TRANSPORT_ID,
        "batch_id": batch["batch_id"],
        "batch_root": batch["batch_root"],
        "call_manifest_root": call_manifest["manifest_root"],
        "checked_at": checked_at,
        "application_count": len(ordered),
        "admitted_application_count": len(admitted_envelopes),
        "held_application_count": len(ordered)
        - len(admitted_envelopes),
        "duplicate_application_ids": duplicates["application_id"],
        "duplicate_envelope_ids": duplicates["envelope_id"],
        "duplicate_nomination_ids": duplicates["nomination_id"],
        "duplicate_candidate_ids": duplicates["candidate_id"],
        "receipts": receipts,
        "admitted_v14_envelope_set_root": admitted_set_root,
        "publication_effect": "NONE",
        "authority_effect": "NONE",
        "truth_effect": "NONE",
    }
    return {
        **body,
        "ledger_root": digest(body),
        "_admitted_envelopes": tuple(admitted_envelopes),
    }


def public_application_receipt_ledger(
    ledger: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        key: value
        for key, value in ledger.items()
        if key != "_admitted_envelopes"
    }


def application_receipt_ledger_integrity(
    batch: Mapping[str, Any],
    calls: Sequence[Mapping[str, Any]],
    call_manifest: Mapping[str, Any],
    applications: Sequence[BatchBoundCandidateApplication],
    ledger: Mapping[str, Any],
    *,
    checked_at: str,
) -> bool:
    try:
        expected = public_application_receipt_ledger(
            application_receipt_ledger(
                batch,
                calls,
                call_manifest,
                applications,
                checked_at=checked_at,
            )
        )
    except (KeyError, TypeError, ValueError, StopIteration):
        return False
    return dict(ledger) == expected
