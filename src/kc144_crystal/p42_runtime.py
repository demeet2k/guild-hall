from __future__ import annotations

import base64
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .agent_receipts import canonical_bytes, content_address
from .p39_runtime import GIT_SHA_RE
from .p41_runtime import (
    P41_NEXT_SEED,
    THIRD_EDGE,
    freeze_heldout_cohort,
    p41_repository_forest,
    p41_source_manifest,
)


P42_LOOKUP_KEY = P41_NEXT_SEED
P42_NEXT_SEED = (
    "KC144.V4.4::MATH144.P43::ADMIT_EXACT_SOURCE_ENUMERATION_WITNESS_"
    "COMPLETE_NONLEAKING_HELDOUT_COHORT_RECEIVE_INDEPENDENT_IC10_"
    "AUTHORIZATION_EXECUTE_P41_EDGE_003_EXACTLY_ONCE_AND_EVALUATE_FORWARD_"
    "POST_EDGE_WATCH_MACROCYCLE_12"
)
P42_FREEZE = "2026-07-28T08:45:00.000000Z"
P42_ROUTE = (
    "KC144.V1::GID005::H05",
    "KC144.V1::GID084::I04",
    "KC144.V1::GID047::F04",
    "KC144.V1::GID090::IC10",
    "KC144.V1::GID141::M09",
    "KC144.V1::GID144::M12",
)
P42_LANES = (
    "PUBLIC_P41_PARENT_BIND",
    "EXACT_SOURCE_ENUMERATION_WITNESS_INTAKE",
    "CUMULATIVE_NONLEAKING_OUTCOME_INTAKE",
    "HELDOUT_COHORT_FREEZE",
    "INDEPENDENT_IC10_EDGE_AUTHORIZATION",
    "EXACTLY_ONCE_EDGE_TRANSACTION_PREPARE",
    "THIRD_EDGE_EXECUTE_OR_HOLD",
    "FORWARD_POST_EDGE_WATCH",
    "PARALLEL_P42_NONCOLLAPSE",
    "M12_RETURN",
)

PUBLIC_P41_RESULT_ID = "KC144.P41.CANDIDATE::482d03a3ff02af3e5656468d"
PUBLIC_P41_RELEASE_DIGEST = (
    "sha256:482d03a3ff02af3e5656468d345e6ece6fb40f2daaaa0a508d38b6042a4eb1c9"
)
PUBLIC_P41_RELEASE_COMMIT = "82b1b5b9e76ae49180d2e36182cadc31e2de5862"
PUBLIC_P41_RELEASE_TREE = "0d7d06492bbee838626f0191f3ccad68f2a1452c"

ROLE_ENUMERATOR = "SOURCE_ENUMERATION_CUSTODIAN"
ROLE_IC10 = "IC10_EDGE_AUTHORIZER"
_ENROLLMENT_DOMAIN = b"KC144.P42.SIGNER-ENROLLMENT.V1\0"
_ENUMERATION_DOMAIN = b"KC144.P42.ENUMERATION-WITNESS.V1\0"
_AUTHORIZATION_DOMAIN = b"KC144.P42.EDGE-AUTHORIZATION.V1\0"


class P42RuntimeError(ValueError):
    pass


def _b64(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def p42_public_parent() -> dict[str, Any]:
    body = {
        "schema": "KC144.P42.PublicParentBinding.V1",
        "result_id": PUBLIC_P41_RESULT_ID,
        "release_digest": PUBLIC_P41_RELEASE_DIGEST,
        "release_commit": PUBLIC_P41_RELEASE_COMMIT,
        "release_tree": PUBLIC_P41_RELEASE_TREE,
        "relation": "EXACT_PUBLIC_PARENT",
        "verification": "PINNED_RELEASE_IDENTITY",
    }
    return {**body, "binding_digest": content_address("kc144.p42.parent", body)}


def p42_parallel_lineage() -> dict[str, Any]:
    body = {
        "schema": "KC144.P42.ParallelLineage.V1",
        "parallel_label": "ATHENA_GIT_BRAIN_V2.P42",
        "relation": "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED",
        "this_p42_role": (
            "ENUMERATION_OUTCOME_AUTHORIZATION_EDGE_TRANSACTION_AND_POST_EDGE_WATCH"
        ),
        "private_semantic_role": "PRESERVED_OPAQUE_NOT_INFERRED",
        "private_repository_locator_published": False,
        "private_receipt_embedded": False,
        "merge_executed": False,
        "renumbering_executed": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "lineage_digest": content_address("kc144.p42.parallel-lineage", body),
    }


def p42_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.P42.Contract.V1",
        "lookup_key": P42_LOOKUP_KEY,
        "public_parent": p42_public_parent(),
        "route": list(P42_ROUTE),
        "lanes": [
            {
                "lane_id": f"P42.L{index:02d}",
                "lane": lane,
                "parallel_group": 1 if index <= 4 else 2 if index <= 8 else 3,
                "return": P42_ROUTE[-1],
            }
            for index, lane in enumerate(P42_LANES, 1)
        ],
        "required_external_roles": [ROLE_ENUMERATOR, ROLE_IC10],
        "role_independence": (
            "ENUMERATION_CUSTODIAN_AND_IC10_AUTHORIZER_MUST_HAVE_DISTINCT_"
            "SIGNERS_ORGANIZATIONS_AND_CONTROL_ROOTS"
        ),
        "enumeration_law": (
            "EXACT_29_SLOT_ORDER_AND_EVERY_LOCATOR_AND_BODY_COMMITMENT_MUST_MATCH_"
            "THE_PINNED_P41_SOURCE_MANIFEST"
        ),
        "cohort_law": (
            "AT_LEAST_FIVE_POST_FREEZE_SEALED_TASK_OR_EMPIRICAL_OUTCOMES_TWO_"
            "EVENT_TYPES_THREE_SURFACES_THREE_ROUTES_NO_CONTINUATION_SUBSTITUTION"
        ),
        "transaction_law": (
            "ALL_ROOTS_AND_EXTERNAL_ROLES_READY_AND_EXECUTION_LEDGER_EMPTY_THEN_"
            "EXECUTE_P41_EDGE_003_EXACTLY_ONCE"
        ),
        "watch_law": (
            "ARM_ONLY_AFTER_PRODUCTION_EXECUTION_AND_ACCEPT_ONLY_STRICTLY_LATER_"
            "OUTCOMES_NOT_REUSED_FROM_THE_AUTHORIZATION_COHORT"
        ),
        "noncollapse": [
            "P41_COMMITMENT_COHORT_IS_NOT_EXACT_ORIGINAL_ENUMERATION_WITNESS",
            "CONTINUATION_CHOICE_IS_NOT_HELDOUT_CALIBRATION_OUTCOME",
            "ENUMERATION_CUSTODIAN_IS_NOT_IC10_EDGE_AUTHORIZER",
            "SIGNED_WITNESS_IS_NOT_VALID_WITHOUT_ENROLLED_CONTROL_PROOF",
            "EDGE_AUTHORIZATION_IS_NOT_GENERAL_GOVERNANCE_AUTHORITY",
            "TEST_SIMULATION_IS_NOT_PRODUCTION_EXECUTION",
            "EDGE_EXECUTION_IS_NOT_TRUTH_PROMOTION",
            "POST_EDGE_WATCH_CANNOT_AUTHORIZE_ITS_OWN_CAUSAL_PREDECESSOR",
            "REPLAY_IS_NOT_INDEPENDENT_EVIDENCE",
            "PARALLEL_P42_LABEL_IS_NOT_THIS_P42_LINEAGE",
            "PUBLICATION_IS_NOT_DEPLOYMENT_OR_MODEL_WEIGHT_MUTATION",
        ],
        "default_state": "HOLD_EXTERNAL_ENUMERATION_OUTCOMES_AND_IC10_ABSENT",
        "next_seed": P42_NEXT_SEED,
    }
    return {**body, "contract_digest": content_address("kc144.p42.contract", body)}


def empty_p42_signer_registry() -> dict[str, Any]:
    body = {
        "schema": "KC144.P42.SignerRegistry.V1",
        "entries": [],
        "authority": "EXTERNAL_REGISTRY_REQUIRED",
    }
    return {
        **body,
        "registry_root": content_address("kc144.p42.signer-registry", body),
    }


def build_p42_signer_enrollment(
    *,
    signer_id: str,
    organization_id: str,
    control_root: str,
    role: str,
    public_key: Ed25519PublicKey,
    valid_from: str,
    valid_until: str,
) -> dict[str, Any]:
    if role not in {ROLE_ENUMERATOR, ROLE_IC10}:
        raise P42RuntimeError("unknown P42 signer role")
    if not all(
        (signer_id, organization_id, control_root, valid_from, valid_until)
    ):
        raise P42RuntimeError("signer enrollment fields must be non-empty")
    if not control_root.startswith("sha256:") or len(control_root) != 71:
        raise P42RuntimeError("signer enrollment requires a SHA-256 control root")
    if not valid_from.endswith("Z") or not valid_until.endswith("Z"):
        raise P42RuntimeError("signer validity bounds must be UTC timestamps")
    body = {
        "schema": "KC144.P42.SignerEnrollment.V1",
        "signer_id": signer_id,
        "organization_id": organization_id,
        "control_root": control_root,
        "role": role,
        "public_key": _b64(
            public_key.public_bytes(
                serialization.Encoding.Raw,
                serialization.PublicFormat.Raw,
            )
        ),
        "valid_from": valid_from,
        "valid_until": valid_until,
    }
    return {
        **body,
        "enrollment_digest": content_address("kc144.p42.signer-enrollment", body),
    }


def enroll_p42_signer(
    registry: Mapping[str, Any],
    enrollment: Mapping[str, Any],
    control_proof: str,
) -> dict[str, Any]:
    if registry.get("schema") != "KC144.P42.SignerRegistry.V1":
        raise P42RuntimeError("invalid signer registry")
    enrollment_body = {
        key: value
        for key, value in enrollment.items()
        if key != "enrollment_digest"
    }
    if enrollment.get("enrollment_digest") != content_address(
        "kc144.p42.signer-enrollment", enrollment_body
    ):
        raise P42RuntimeError("invalid signer enrollment digest")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            _unb64(str(enrollment["public_key"]))
        )
        public_key.verify(
            _unb64(control_proof),
            _ENROLLMENT_DOMAIN + canonical_bytes(enrollment_body),
        )
    except (InvalidSignature, ValueError, KeyError) as error:
        raise P42RuntimeError("invalid signer control proof") from error
    entries = [dict(row) for row in registry.get("entries", [])]
    if any(
        row.get("signer_id") == enrollment.get("signer_id")
        or row.get("organization_id") == enrollment.get("organization_id")
        or row.get("control_root") == enrollment.get("control_root")
        for row in entries
    ):
        raise P42RuntimeError(
            "signer, organization, and control root must be globally unique"
        )
    entries.append({**dict(enrollment), "control_proof": control_proof})
    entries.sort(key=lambda row: (str(row["role"]), str(row["signer_id"])))
    body = {
        "schema": "KC144.P42.SignerRegistry.V1",
        "entries": entries,
        "authority": "EXTERNAL_REGISTRY_BOUND",
    }
    return {
        **body,
        "registry_root": content_address("kc144.p42.signer-registry", body),
    }


def _verify_registry(registry: Mapping[str, Any]) -> bool:
    body = {key: value for key, value in registry.items() if key != "registry_root"}
    if (
        registry.get("schema") != "KC144.P42.SignerRegistry.V1"
        or registry.get("registry_root")
        != content_address("kc144.p42.signer-registry", body)
    ):
        return False
    seen_signers: set[str] = set()
    seen_orgs: set[str] = set()
    seen_controls: set[str] = set()
    for entry in registry.get("entries", []):
        signer = str(entry.get("signer_id", ""))
        organization = str(entry.get("organization_id", ""))
        control = str(entry.get("control_root", ""))
        enrollment = {
            key: value for key, value in entry.items() if key != "control_proof"
        }
        enrollment_body = {
            key: value
            for key, value in enrollment.items()
            if key != "enrollment_digest"
        }
        if (
            not signer
            or not organization
            or not control
            or signer in seen_signers
            or organization in seen_orgs
            or control in seen_controls
            or enrollment.get("role") not in {ROLE_ENUMERATOR, ROLE_IC10}
            or enrollment.get("enrollment_digest")
            != content_address("kc144.p42.signer-enrollment", enrollment_body)
        ):
            return False
        try:
            public_key = Ed25519PublicKey.from_public_bytes(
                _unb64(str(entry["public_key"]))
            )
            public_key.verify(
                _unb64(str(entry["control_proof"])),
                _ENROLLMENT_DOMAIN + canonical_bytes(enrollment_body),
            )
        except (InvalidSignature, ValueError, KeyError):
            return False
        seen_signers.add(signer)
        seen_orgs.add(organization)
        seen_controls.add(control)
    return True


def build_p42_enumeration_witness(
    *,
    signer_id: str,
    organization_id: str,
    control_root: str,
    private_key: Ed25519PrivateKey,
    issued_at: str,
    ordered_rows: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    source = p41_source_manifest()
    rows = [
        {
            "source_slot": row["source_slot"],
            "locator_commitment": row["locator_commitment"],
            "body_commitment": row["body_commitment"],
            "body_state": row["body_state"],
        }
        for row in (ordered_rows or source["rows"])
    ]
    body = {
        "schema": "KC144.P42.SourceEnumerationWitness.V1",
        "scope": "EXACT_P41_29_SLOT_ENUMERATION",
        "source_manifest_root": source["manifest_root"],
        "ordered_rows": rows,
        "enumerated_slot_count": len(rows),
        "signer_id": signer_id,
        "organization_id": organization_id,
        "control_root": control_root,
        "issued_at": issued_at,
    }
    signed = {
        **body,
        "signature": _b64(
            private_key.sign(_ENUMERATION_DOMAIN + canonical_bytes(body))
        ),
    }
    return {
        **signed,
        "witness_digest": content_address("kc144.p42.enumeration-witness", signed),
    }


def evaluate_p42_enumeration(
    registry: Mapping[str, Any],
    witness: Mapping[str, Any] | None,
) -> dict[str, Any]:
    source = p41_source_manifest()
    errors: list[str] = []
    accepted: dict[str, Any] | None = None
    registry_valid = _verify_registry(registry)
    row = dict(witness or {})
    entries = {
        str(item.get("signer_id")): item
        for item in registry.get("entries", [])
        if item.get("role") == ROLE_ENUMERATOR
    }
    signer = entries.get(str(row.get("signer_id")))
    if not row:
        errors.append("WITNESS_ABSENT")
    elif not registry_valid:
        errors.append("REGISTRY_INVALID")
    elif signer is None:
        errors.append("ENUMERATOR_NOT_ENROLLED")
    else:
        signed_body = {
            key: value
            for key, value in row.items()
            if key not in {"signature", "witness_digest"}
        }
        digest_body = {
            key: value for key, value in row.items() if key != "witness_digest"
        }
        expected_rows = [
            {
                "source_slot": item["source_slot"],
                "locator_commitment": item["locator_commitment"],
                "body_commitment": item["body_commitment"],
                "body_state": item["body_state"],
            }
            for item in source["rows"]
        ]
        if row.get("witness_digest") != content_address(
            "kc144.p42.enumeration-witness", digest_body
        ):
            errors.append("WITNESS_DIGEST_INVALID")
        if row.get("source_manifest_root") != source["manifest_root"]:
            errors.append("SOURCE_ROOT_MISMATCH")
        if row.get("scope") != "EXACT_P41_29_SLOT_ENUMERATION":
            errors.append("SCOPE_MISMATCH")
        if row.get("ordered_rows") != expected_rows or row.get(
            "enumerated_slot_count"
        ) != 29:
            errors.append("EXACT_ORDERED_ENUMERATION_MISMATCH")
        if (
            row.get("organization_id") != signer.get("organization_id")
            or row.get("control_root") != signer.get("control_root")
        ):
            errors.append("ENROLLMENT_BINDING_MISMATCH")
        if not (
            str(signer.get("valid_from"))
            <= str(row.get("issued_at"))
            < str(signer.get("valid_until"))
        ):
            errors.append("VALIDITY_WINDOW_MISMATCH")
        try:
            public_key = Ed25519PublicKey.from_public_bytes(
                _unb64(str(signer["public_key"]))
            )
            public_key.verify(
                _unb64(str(row["signature"])),
                _ENUMERATION_DOMAIN + canonical_bytes(signed_body),
            )
        except (InvalidSignature, ValueError, KeyError):
            errors.append("SIGNATURE_INVALID")
        if not errors:
            accepted = row
    body = {
        "schema": "KC144.P42.EnumerationEvaluation.V1",
        "registry_root": registry.get("registry_root"),
        "registry_valid": registry_valid,
        "source_manifest_root": source["manifest_root"],
        "accepted_witness": accepted,
        "accepted_witness_count": 1 if accepted else 0,
        "errors": sorted(set(errors)),
        "status": "EXACT_ENUMERATION_VERIFIED" if accepted else "HOLD",
        "truth_effect": "NONE",
        "authority_effect": "SOURCE_ENUMERATION_ONLY" if accepted else "NONE",
    }
    return {
        **body,
        "evaluation_digest": content_address(
            "kc144.p42.enumeration-evaluation", body
        ),
    }


def compile_p42_cohort(
    events: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    cohort = freeze_heldout_cohort(events)
    body = {
        "schema": "KC144.P42.CumulativeHeldoutCohort.V1",
        "source_schema": cohort["schema"],
        "source_cohort_root": cohort["cohort_root"],
        "freeze": P42_FREEZE,
        "events": cohort["events"],
        "event_count": cohort["event_count"],
        "required_event_count": cohort["required_event_count"],
        "event_type_count": cohort["event_type_count"],
        "source_surface_count": cohort["source_surface_count"],
        "route_count": cohort["route_count"],
        "labels_revealed": cohort["labels_revealed"],
        "continuation_events_admitted": cohort["continuation_events_admitted"],
        "errors": cohort["errors"],
        "status": cohort["status"],
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "cohort_root": content_address("kc144.p42.cumulative-cohort", body),
    }


def _edge_candidate(
    enumeration: Mapping[str, Any],
    cohort: Mapping[str, Any],
) -> dict[str, Any]:
    source = p41_source_manifest()
    forest = p41_repository_forest()
    body = {
        "schema": "KC144.P42.EdgeTransactionCandidate.V1",
        "edge": dict(THIRD_EDGE),
        "public_parent_result_id": PUBLIC_P41_RESULT_ID,
        "source_manifest_root": source["manifest_root"],
        "repository_forest_root": forest["forest_root"],
        "enumeration_evaluation_digest": enumeration["evaluation_digest"],
        "heldout_cohort_root": cohort["cohort_root"],
        "mutation_scope": "CANONICAL_PROPOSAL_EDGE_LEDGER_ONLY",
        "expected_execution_count": 1,
    }
    return {
        **body,
        "transaction_root": content_address(
            "kc144.p42.edge-transaction-candidate", body
        ),
    }


def build_p42_edge_authorization(
    *,
    transaction_root: str,
    source_manifest_root: str,
    repository_forest_root: str,
    enumeration_evaluation_digest: str,
    heldout_cohort_root: str,
    signer_id: str,
    organization_id: str,
    control_root: str,
    private_key: Ed25519PrivateKey,
    issued_at: str,
    expires_at: str,
    nonce: str,
) -> dict[str, Any]:
    body = {
        "schema": "KC144.P42.EdgeAuthorization.V1",
        "scope": "P41_EDGE_003_EXACTLY_ONCE",
        "verdict": "AUTHORIZE_EDGE",
        "transaction_root": transaction_root,
        "source_manifest_root": source_manifest_root,
        "repository_forest_root": repository_forest_root,
        "enumeration_evaluation_digest": enumeration_evaluation_digest,
        "heldout_cohort_root": heldout_cohort_root,
        "signer_id": signer_id,
        "organization_id": organization_id,
        "control_root": control_root,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
    }
    signed = {
        **body,
        "signature": _b64(
            private_key.sign(_AUTHORIZATION_DOMAIN + canonical_bytes(body))
        ),
    }
    return {
        **signed,
        "authorization_digest": content_address(
            "kc144.p42.edge-authorization", signed
        ),
    }


def evaluate_p42_authorizations(
    registry: Mapping[str, Any],
    authorizations: Sequence[Mapping[str, Any]],
    *,
    candidate: Mapping[str, Any],
    enumeration: Mapping[str, Any],
    cohort: Mapping[str, Any],
) -> dict[str, Any]:
    source = p41_source_manifest()
    forest = p41_repository_forest()
    registry_valid = _verify_registry(registry)
    entries = {
        str(item.get("signer_id")): item
        for item in registry.get("entries", [])
        if item.get("role") == ROLE_IC10
    }
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, str]] = []
    seen_nonces: set[str] = set()
    for value in authorizations:
        row = dict(value)
        signer = entries.get(str(row.get("signer_id")))
        reason = ""
        signed_body = {
            key: item
            for key, item in row.items()
            if key not in {"signature", "authorization_digest"}
        }
        digest_body = {
            key: item
            for key, item in row.items()
            if key != "authorization_digest"
        }
        if not registry_valid:
            reason = "REGISTRY_INVALID"
        elif signer is None:
            reason = "IC10_SIGNER_NOT_ENROLLED"
        elif row.get("authorization_digest") != content_address(
            "kc144.p42.edge-authorization", digest_body
        ):
            reason = "AUTHORIZATION_DIGEST_INVALID"
        elif row.get("scope") != "P41_EDGE_003_EXACTLY_ONCE":
            reason = "SCOPE_MISMATCH"
        elif row.get("verdict") != "AUTHORIZE_EDGE":
            reason = "VERDICT_MISMATCH"
        elif row.get("transaction_root") != candidate["transaction_root"]:
            reason = "TRANSACTION_ROOT_MISMATCH"
        elif row.get("source_manifest_root") != source["manifest_root"]:
            reason = "SOURCE_ROOT_MISMATCH"
        elif row.get("repository_forest_root") != forest["forest_root"]:
            reason = "REPOSITORY_ROOT_MISMATCH"
        elif row.get("enumeration_evaluation_digest") != enumeration[
            "evaluation_digest"
        ]:
            reason = "ENUMERATION_ROOT_MISMATCH"
        elif row.get("heldout_cohort_root") != cohort["cohort_root"]:
            reason = "COHORT_ROOT_MISMATCH"
        elif (
            row.get("organization_id") != signer.get("organization_id")
            or row.get("control_root") != signer.get("control_root")
        ):
            reason = "ENROLLMENT_BINDING_MISMATCH"
        elif not (
            str(signer.get("valid_from"))
            <= str(row.get("issued_at"))
            < str(row.get("expires_at"))
            <= str(signer.get("valid_until"))
        ):
            reason = "VALIDITY_WINDOW_MISMATCH"
        elif str(row.get("nonce", "")) in seen_nonces:
            reason = "NONCE_REPLAY"
        else:
            try:
                public_key = Ed25519PublicKey.from_public_bytes(
                    _unb64(str(signer["public_key"]))
                )
                public_key.verify(
                    _unb64(str(row["signature"])),
                    _AUTHORIZATION_DOMAIN + canonical_bytes(signed_body),
                )
            except (InvalidSignature, ValueError, KeyError):
                reason = "SIGNATURE_INVALID"
        if reason:
            rejected.append(
                {
                    "authorization_digest": str(
                        row.get("authorization_digest", "")
                    ),
                    "reason": reason,
                }
            )
        else:
            accepted.append(row)
            seen_nonces.add(str(row["nonce"]))
    accepted.sort(key=lambda row: str(row["authorization_digest"]))
    rejected.sort(key=lambda row: (row["reason"], row["authorization_digest"]))
    body = {
        "schema": "KC144.P42.AuthorizationEvaluation.V1",
        "registry_root": registry.get("registry_root"),
        "registry_valid": registry_valid,
        "required_independent_authorizations": 1,
        "accepted_authorizations": accepted,
        "accepted_authorization_count": len(accepted),
        "rejected_authorizations": rejected,
        "status": "IC10_AUTHORIZED" if accepted else "HOLD",
        "truth_effect": "NONE",
        "authority_effect": "EDGE_EXECUTION_ONLY" if accepted else "NONE",
    }
    return {
        **body,
        "evaluation_digest": content_address(
            "kc144.p42.authorization-evaluation", body
        ),
    }


def _compile_edge_transaction(
    *,
    candidate: Mapping[str, Any],
    enumeration: Mapping[str, Any],
    cohort: Mapping[str, Any],
    authorization: Mapping[str, Any],
    execution_ledger: Sequence[Mapping[str, Any]],
    namespace: str,
    execution_time: str,
) -> dict[str, Any]:
    ledger_before = [dict(row) for row in execution_ledger]
    matching = [
        row
        for row in ledger_before
        if row.get("edge_id") == THIRD_EDGE["edge_id"]
    ]
    ledger_valid = (
        len(matching) <= 1
        and all(row.get("schema") == "KC144.P42.EdgeExecutionRecord.V1" for row in matching)
    )
    roles_independent = False
    witness = enumeration.get("accepted_witness")
    auths = authorization.get("accepted_authorizations", [])
    if witness and auths:
        roles_independent = all(
            witness.get(field) != auths[0].get(field)
            for field in ("signer_id", "organization_id", "control_root")
        )
    eligible = (
        enumeration.get("status") == "EXACT_ENUMERATION_VERIFIED"
        and cohort.get("status") == "COHORT_READY"
        and authorization.get("status") == "IC10_AUTHORIZED"
        and roles_independent
        and ledger_valid
    )
    already_executed = len(matching) == 1
    execute_now = eligible and not already_executed
    ledger_after = list(ledger_before)
    execution_record: dict[str, Any] | None = matching[0] if matching else None
    if execute_now and namespace == "PRODUCTION":
        record_body = {
            "schema": "KC144.P42.EdgeExecutionRecord.V1",
            "edge_id": THIRD_EDGE["edge_id"],
            "transaction_root": candidate["transaction_root"],
            "authorization_digest": auths[0]["authorization_digest"],
            "executed_at": execution_time,
            "execution_ordinal": 1,
            "mutation_scope": "CANONICAL_PROPOSAL_EDGE_LEDGER_ONLY",
            "truth_effect": "NONE",
        }
        execution_record = {
            **record_body,
            "record_digest": content_address(
                "kc144.p42.edge-execution-record", record_body
            ),
        }
        ledger_after.append(execution_record)
    status = "HELD_NOT_EXECUTED"
    if already_executed and eligible:
        status = "ALREADY_EXECUTED_IDEMPOTENT"
    elif execute_now and namespace == "PRODUCTION":
        status = "EXECUTED"
    elif execute_now and namespace == "TEST":
        status = "SIMULATED_EXECUTION"
    body = {
        "schema": "KC144.P42.ExactlyOnceEdgeTransaction.V1",
        "candidate": dict(candidate),
        "enumeration_gate": enumeration.get("status"),
        "heldout_gate": cohort.get("status"),
        "ic10_gate": authorization.get("status"),
        "role_independence": roles_independent,
        "ledger_valid": ledger_valid,
        "ledger_before": ledger_before,
        "ledger_after": ledger_after,
        "execution_record": execution_record,
        "execution_status": status,
        "execution_count_before": len(matching),
        "execution_count_after": len(
            [
                row
                for row in ledger_after
                if row.get("edge_id") == THIRD_EDGE["edge_id"]
            ]
        ),
        "ledger_mutated": ledger_after != ledger_before,
        "canonical_graph_mutations": (
            1 if status == "EXECUTED" else 0
        ),
        "test_simulation": status == "SIMULATED_EXECUTION",
        "production_mutated": status == "EXECUTED",
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "EDGE_EXECUTION_ONLY" if status == "EXECUTED" else "NONE",
    }
    return {
        **body,
        "transaction_digest": content_address(
            "kc144.p42.exactly-once-transaction", body
        ),
    }


def _compile_post_edge_watch(
    transaction: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    execution_record = transaction.get("execution_record") or {}
    cutoff = execution_record.get("executed_at")
    authorization_ids = {
        str(row.get("event_id"))
        for row in transaction.get("candidate", {}).get("heldout_events", [])
    }
    accepted: list[dict[str, Any]] = []
    errors: list[str] = []
    armed = transaction.get("execution_status") in {
        "EXECUTED",
        "ALREADY_EXECUTED_IDEMPOTENT",
    }
    for value in events:
        row = dict(value)
        if not armed:
            errors.append("WATCH_NOT_ARMED")
            continue
        if row.get("event_id") in authorization_ids:
            errors.append("AUTHORIZATION_EVENT_REUSE")
        if str(row.get("observed_at", "")) <= str(cutoff):
            errors.append("RETROACTIVE_WATCH_EVENT")
        if row.get("outcome_class") not in {"TASK_OUTCOME", "EMPIRICAL_RESULT"}:
            errors.append("WATCH_EVENT_CLASS")
        if row.get("continuation_only") is not False:
            errors.append("CONTINUATION_ONLY")
        if not errors:
            accepted.append(row)
    body = {
        "schema": "KC144.P42.PostEdgeWatch.V1",
        "status": "ARMED" if armed else "HELD_NOT_ARMED",
        "cutoff": cutoff,
        "events": accepted,
        "event_count": len(accepted),
        "errors": sorted(set(errors)),
        "retroactive_events_admitted": 0,
        "authorization_events_reused": 0,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "watch_digest": content_address("kc144.p42.post-edge-watch", body),
    }


def _lane_receipt(
    index: int,
    lane: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "schema": "KC144.P42.LaneReceipt.V1",
        "lane_id": f"P42.L{index:02d}",
        "lane": lane,
        "payload_digest": content_address(
            f"kc144.p42.lane.{lane.lower()}", payload
        ),
        "return": P42_ROUTE[-1],
        "truth_effect": "NONE",
    }
    return {
        **body,
        "receipt_id": content_address("kc144.p42.lane-receipt", body),
    }


def compile_p42_cycle(
    *,
    signer_registry: Mapping[str, Any] | None = None,
    enumeration_witness: Mapping[str, Any] | None = None,
    heldout_events: Sequence[Mapping[str, Any]] = (),
    edge_authorizations: Sequence[Mapping[str, Any]] = (),
    execution_ledger: Sequence[Mapping[str, Any]] = (),
    post_edge_events: Sequence[Mapping[str, Any]] = (),
    namespace: str = "PRODUCTION",
    execution_time: str = P42_FREEZE,
) -> dict[str, Any]:
    if namespace not in {"PRODUCTION", "TEST"}:
        raise P42RuntimeError("namespace must be PRODUCTION or TEST")
    registry = dict(signer_registry or empty_p42_signer_registry())
    contract = p42_contract()
    parent = p42_public_parent()
    enumeration = evaluate_p42_enumeration(registry, enumeration_witness)
    cohort = compile_p42_cohort(heldout_events)
    candidate = _edge_candidate(enumeration, cohort)
    candidate["heldout_events"] = list(cohort["events"])
    candidate["transaction_root"] = content_address(
        "kc144.p42.edge-transaction-candidate",
        {key: value for key, value in candidate.items() if key != "transaction_root"},
    )
    authorization = evaluate_p42_authorizations(
        registry,
        edge_authorizations,
        candidate=candidate,
        enumeration=enumeration,
        cohort=cohort,
    )
    transaction = _compile_edge_transaction(
        candidate=candidate,
        enumeration=enumeration,
        cohort=cohort,
        authorization=authorization,
        execution_ledger=execution_ledger,
        namespace=namespace,
        execution_time=execution_time,
    )
    watch = _compile_post_edge_watch(transaction, post_edge_events)
    parallel = p42_parallel_lineage()
    residuals: list[str] = []
    if enumeration["status"] != "EXACT_ENUMERATION_VERIFIED":
        residuals.append("EXACT_SOURCE_ENUMERATION_WITNESS_PENDING")
    if cohort["status"] != "COHORT_READY":
        residuals.append("FIRST_FIVE_NONLEAKING_HELDOUT_OUTCOMES_PENDING")
    if authorization["status"] != "IC10_AUTHORIZED":
        residuals.append("INDEPENDENT_IC10_EDGE_AUTHORIZATION_PENDING")
    if transaction["execution_status"] == "HELD_NOT_EXECUTED":
        residuals.append("P41_EDGE_003_HELD")
    if watch["status"] != "ARMED":
        residuals.append("POST_EDGE_WATCH_NOT_ARMED")
    state = {
        "schema": "KC144.P42.StateDelta.V1",
        "public_parent_result_id": PUBLIC_P41_RESULT_ID,
        "enumeration_witnesses": enumeration["accepted_witness_count"],
        "heldout_outcomes": cohort["event_count"],
        "required_heldout_outcomes": cohort["required_event_count"],
        "independent_ic10_authorizations": authorization[
            "accepted_authorization_count"
        ],
        "third_edge": transaction["execution_status"],
        "edge_execution_count": transaction["execution_count_after"],
        "post_edge_watch": watch["status"],
        "post_edge_outcomes": watch["event_count"],
        "canonical_graph_mutations": transaction["canonical_graph_mutations"],
        "parallel_p42_merges": 0,
        "deployments": 0,
        "model_weight_mutations": 0,
        "promotions": 0,
        "production_mutated": transaction["production_mutated"],
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": transaction["authority_effect"],
        "global_release": (
            "EDGE_EXECUTED"
            if transaction["execution_status"] in {
                "EXECUTED",
                "ALREADY_EXECUTED_IDEMPOTENT",
            }
            else "HOLD"
        ),
        "residuals": sorted(residuals),
        "return": P42_ROUTE[-1],
        "next_seed": P42_NEXT_SEED,
    }
    state["delta_id"] = content_address("kc144.p42.state-delta", state)
    payloads = (
        parent,
        enumeration,
        {
            "event_count": cohort["event_count"],
            "source_cohort_root": cohort["source_cohort_root"],
        },
        cohort,
        authorization,
        candidate,
        transaction,
        watch,
        parallel,
        {
            "return": P42_ROUTE[-1],
            "next_seed": P42_NEXT_SEED,
            "state_delta": state["delta_id"],
        },
    )
    receipts = [
        _lane_receipt(index, lane, payload)
        for index, (lane, payload) in enumerate(zip(P42_LANES, payloads), 1)
    ]
    body = {
        "schema": "KC144.P42.Macrocycle.V1",
        "contract_digest": contract["contract_digest"],
        "namespace": namespace,
        "execution_time": execution_time,
        "public_parent_binding": parent,
        "signer_registry": registry,
        "enumeration_evaluation": enumeration,
        "heldout_cohort": cohort,
        "edge_candidate": candidate,
        "authorization_evaluation": authorization,
        "edge_transaction": transaction,
        "post_edge_watch": watch,
        "parallel_lineage": parallel,
        "lane_receipts": receipts,
        "state": state,
    }
    return {**body, "envelope_digest": content_address("kc144.p42.macrocycle", body)}


def verify_p42_cycle(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: item for key, item in value.items() if key != "envelope_digest"}
    if value.get("schema") != "KC144.P42.Macrocycle.V1":
        errors.append("E_SCHEMA")
    if value.get("envelope_digest") != content_address(
        "kc144.p42.macrocycle", body
    ):
        errors.append("E_ENVELOPE_DIGEST")
    if value.get("contract_digest") != p42_contract()["contract_digest"]:
        errors.append("E_CONTRACT")
    if value.get("public_parent_binding") != p42_public_parent():
        errors.append("E_PUBLIC_PARENT")
    if value.get("parallel_lineage") != p42_parallel_lineage():
        errors.append("E_PARALLEL_LINEAGE")
    transaction = value.get("edge_transaction", {})
    transaction_body = {
        key: item
        for key, item in transaction.items()
        if key != "transaction_digest"
    }
    if transaction.get("transaction_digest") != content_address(
        "kc144.p42.exactly-once-transaction", transaction_body
    ):
        errors.append("E_TRANSACTION_DIGEST")
    if transaction.get("execution_count_after", 0) > 1:
        errors.append("E_EXACTLY_ONCE")
    if value.get("namespace") == "TEST" and (
        transaction.get("ledger_mutated")
        or transaction.get("canonical_graph_mutations")
        or transaction.get("production_mutated")
    ):
        errors.append("E_TEST_PRODUCTION_MUTATION")
    if transaction.get("execution_status") == "HELD_NOT_EXECUTED" and (
        transaction.get("ledger_mutated")
        or transaction.get("canonical_graph_mutations")
        or transaction.get("production_mutated")
    ):
        errors.append("E_HELD_EDGE_MUTATION")
    watch = value.get("post_edge_watch", {})
    if watch.get("status") == "ARMED" and transaction.get(
        "execution_status"
    ) not in {"EXECUTED", "ALREADY_EXECUTED_IDEMPOTENT"}:
        errors.append("E_WATCH_ARMED_WITHOUT_EDGE")
    state = value.get("state", {})
    if (
        state.get("parallel_p42_merges") != 0
        or state.get("deployments") != 0
        or state.get("model_weight_mutations") != 0
        or state.get("promotions") != 0
        or state.get("truth_effect") != "NONE"
    ):
        errors.append("E_PROTECTED_STATE_ESCALATION")
    receipts = value.get("lane_receipts", [])
    if len(receipts) != len(P42_LANES):
        errors.append("E_LANE_CENSUS")
    else:
        for index, (lane, receipt) in enumerate(zip(P42_LANES, receipts), 1):
            receipt_body = {
                key: item
                for key, item in receipt.items()
                if key != "receipt_id"
            }
            if (
                receipt.get("lane_id") != f"P42.L{index:02d}"
                or receipt.get("lane") != lane
                or receipt.get("receipt_id")
                != content_address("kc144.p42.lane-receipt", receipt_body)
            ):
                errors.append("E_LANE_RECEIPT")
    try:
        enumeration = value.get("enumeration_evaluation", {})
        witness = enumeration.get("accepted_witness")
        authorization = value.get("authorization_evaluation", {})
        replay = compile_p42_cycle(
            signer_registry=value.get("signer_registry"),
            enumeration_witness=witness,
            heldout_events=value.get("heldout_cohort", {}).get("events", []),
            edge_authorizations=authorization.get(
                "accepted_authorizations", []
            ),
            execution_ledger=value.get("edge_transaction", {}).get(
                "ledger_before", []
            ),
            post_edge_events=value.get("post_edge_watch", {}).get("events", []),
            namespace=str(value.get("namespace", "")),
            execution_time=str(value.get("execution_time", "")),
        )
        if (
            not enumeration.get("errors")
            and not authorization.get("rejected_authorizations")
            and replay != dict(value)
        ):
            errors.append("E_COLD_REPLAY")
        if (
            enumeration.get("errors") == ["WITNESS_ABSENT"]
            and not authorization.get("rejected_authorizations")
            and replay != dict(value)
        ):
            errors.append("E_COLD_REPLAY")
    except (P42RuntimeError, TypeError, ValueError):
        errors.append("E_COLD_REPLAY")
    return {
        "schema": "KC144.P42.MacrocycleVerification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "envelope_digest": value.get("envelope_digest"),
    }


def compile_p42_release(
    output_directory: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
) -> dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(implementation_commit):
        raise P42RuntimeError("implementation_commit must be a Git SHA")
    if not GIT_SHA_RE.fullmatch(implementation_tree):
        raise P42RuntimeError("implementation_tree must be a Git tree SHA")
    contract = p42_contract()
    registry = empty_p42_signer_registry()
    cycle = compile_p42_cycle(signer_registry=registry)
    verification = verify_p42_cycle(cycle)
    enumeration = cycle["enumeration_evaluation"]
    cohort = cycle["heldout_cohort"]
    authorization = cycle["authorization_evaluation"]
    transaction = cycle["edge_transaction"]
    watch = cycle["post_edge_watch"]
    parallel = cycle["parallel_lineage"]
    release_core = {
        "schema": "KC144.P42.Release.V1",
        "release_id": "KC144_P42_EXACT_EDGE_TRANSACTION_CANDIDATE_V1",
        "status": "CANDIDATE_HOLD",
        "implementation": {
            "repository": "demeet2k/guild-hall",
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "public_parent_result_id": PUBLIC_P41_RESULT_ID,
        "public_parent_release_digest": PUBLIC_P41_RELEASE_DIGEST,
        "contract_digest": contract["contract_digest"],
        "signer_registry_root": registry["registry_root"],
        "enumeration_evaluation_digest": enumeration["evaluation_digest"],
        "heldout_cohort_root": cohort["cohort_root"],
        "authorization_evaluation_digest": authorization["evaluation_digest"],
        "edge_transaction_digest": transaction["transaction_digest"],
        "post_edge_watch_digest": watch["watch_digest"],
        "parallel_lineage_digest": parallel["lineage_digest"],
        "envelope_digest": cycle["envelope_digest"],
        "verification_verdict": verification["verdict"],
        "exact_enumeration_witnesses": enumeration["accepted_witness_count"],
        "heldout_outcomes": cohort["event_count"],
        "required_heldout_outcomes": cohort["required_event_count"],
        "independent_ic10_authorizations": authorization[
            "accepted_authorization_count"
        ],
        "third_edge": transaction["execution_status"],
        "edge_execution_count": transaction["execution_count_after"],
        "post_edge_watch": watch["status"],
        "canonical_graph_mutations": 0,
        "parallel_p42_merges": 0,
        "production_authority": "HOLD",
        "production_mutated": False,
        "truth_effect": "NONE",
        "next_seed": P42_NEXT_SEED,
    }
    release_digest = content_address("kc144.p42.release", release_core)
    release = {
        **release_core,
        "release_digest": release_digest,
        "result_id": "KC144.P42.CANDIDATE::"
        + release_digest.removeprefix("sha256:")[:24],
    }
    artifacts = {
        "p42_contract_v1.json": contract,
        "p42_signer_registry_v1.json": registry,
        "p42_enumeration_evaluation_v1.json": enumeration,
        "p42_heldout_cohort_v1.json": cohort,
        "p42_authorization_evaluation_v1.json": authorization,
        "p42_edge_transaction_v1.json": transaction,
        "p42_post_edge_watch_v1.json": watch,
        "p42_parallel_lineage_v1.json": parallel,
        "p42_macrocycle_v1.json": cycle,
        "p42_verification_v1.json": verification,
        "p42_release_v1.json": release,
    }
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    for name, artifact in artifacts.items():
        (output / name).write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )
    checksum_lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in sorted(output.glob("*.json"))
    ]
    (output / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )
    return release
