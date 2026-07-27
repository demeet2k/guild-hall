from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Any, Mapping, Sequence

from .ceremony_v10 import (
    CEREMONY_ID,
    ROLES,
    GovernanceChallenge,
    GovernanceEnrollmentResponse,
    assemble_pending_society,
    create_governance_challenge,
    governance_ceremony_contract,
    verify_enrollment_response,
)
from .crosswalk import ACTIVE_EPOCH_ID
from .handoff_v9 import GOVERNANCE_MEMBER_COUNT
from .population import digest


DISPATCH_ID = "KC144.GOVERNANCE.DISPATCH.V11"
BATCH_STATUS = "ISSUED_AWAITING_EXTERNAL_RESPONSES"


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def governance_dispatch_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.GovernanceDispatchContract.V11",
        "dispatch_id": DISPATCH_ID,
        "ceremony_id": CEREMONY_ID,
        "epoch_id": ACTIVE_EPOCH_ID,
        "roles": list(ROLES),
        "challenge_count": GOVERNANCE_MEMBER_COUNT,
        "issuance_law": (
            "one immutable batch contains one independently random, "
            "role-bound V10 challenge for each of the five governance roles"
        ),
        "routing_law": (
            "all supplied responses are evaluated as one parallel intake "
            "wave against the exact issued batch; collisions fail closed"
        ),
        "assembly_law": (
            "only five unique batch-matched verified responses may invoke "
            "the V10 pending-society assembler"
        ),
        "expiration_law": (
            "responses are accepted only while the batch is open; an "
            "expired batch is preserved and must be replaced, never edited"
        ),
        "activation_law": (
            "dispatch and response routing never activate governance; a "
            "complete pending society still requires V10 external "
            "ratification"
        ),
        "fixture_law": "LOCAL_OR_TEST_RESPONSES_HAVE_ZERO_PRODUCTION_EFFECT",
        "truth_effect": "NONE",
    }
    return {**body, "contract_digest": digest(body)}


def _batch_id(challenge_digests: Sequence[str]) -> str:
    seed = {
        "dispatch_id": DISPATCH_ID,
        "challenge_digests": list(challenge_digests),
    }
    return f"V11-BATCH::{digest(seed)[7:31]}"


def issue_governance_challenge_batch(
    *,
    authority_registry_digest: str,
    handoff_bundle_root: str,
    issued_at: str,
    expires_at: str,
) -> dict[str, Any]:
    challenges = [
        create_governance_challenge(
            role,
            authority_registry_digest=authority_registry_digest,
            handoff_bundle_root=handoff_bundle_root,
            issued_at=issued_at,
            expires_at=expires_at,
        ).to_dict()
        for role in ROLES
    ]
    challenge_digests = [
        challenge["challenge_digest"] for challenge in challenges
    ]
    body = {
        "schema": "KC144.GovernanceChallengeBatch.V11",
        "dispatch_id": DISPATCH_ID,
        "batch_id": _batch_id(challenge_digests),
        "ceremony_id": CEREMONY_ID,
        "epoch_id": ACTIVE_EPOCH_ID,
        "dispatch_contract_digest": governance_dispatch_contract()[
            "contract_digest"
        ],
        "ceremony_contract_digest": governance_ceremony_contract()[
            "contract_digest"
        ],
        "authority_registry_digest": authority_registry_digest,
        "handoff_bundle_root": handoff_bundle_root,
        "issued_at": issued_at,
        "expires_at": expires_at,
        "roles": list(ROLES),
        "challenges": challenges,
        "challenge_digests": challenge_digests,
        "challenge_count": len(challenges),
        "response_count": 0,
        "status": BATCH_STATUS,
        "governance_activated": False,
        "truth_effect": "NONE",
    }
    return {**body, "batch_root": digest(body)}


def challenge_batch_integrity(batch: Mapping[str, Any]) -> bool:
    expected_keys = {
        "schema",
        "dispatch_id",
        "batch_id",
        "ceremony_id",
        "epoch_id",
        "dispatch_contract_digest",
        "ceremony_contract_digest",
        "authority_registry_digest",
        "handoff_bundle_root",
        "issued_at",
        "expires_at",
        "roles",
        "challenges",
        "challenge_digests",
        "challenge_count",
        "response_count",
        "status",
        "governance_activated",
        "truth_effect",
        "batch_root",
    }
    try:
        raw_challenges = list(batch["challenges"])
        challenges = [
            GovernanceChallenge.from_dict(value)
            for value in raw_challenges
        ]
        issued = _parse_time(str(batch["issued_at"]))
        expires = _parse_time(str(batch["expires_at"]))
        reconstructed = [
            create_governance_challenge(
                challenge.role,
                authority_registry_digest=challenge.authority_registry_digest,
                handoff_bundle_root=challenge.handoff_bundle_root,
                issued_at=challenge.issued_at,
                expires_at=challenge.expires_at,
                nonce=challenge.nonce,
            ).to_dict()
            for challenge in challenges
        ]
    except (KeyError, TypeError, ValueError):
        return False
    challenge_digests = [
        challenge["challenge_digest"] for challenge in reconstructed
    ]
    challenge_ids = [
        challenge["challenge_id"] for challenge in reconstructed
    ]
    nonces = [challenge["nonce"] for challenge in reconstructed]
    body = {key: value for key, value in batch.items() if key != "batch_root"}
    return (
        set(batch) == expected_keys
        and batch.get("schema") == "KC144.GovernanceChallengeBatch.V11"
        and batch.get("dispatch_id") == DISPATCH_ID
        and batch.get("ceremony_id") == CEREMONY_ID
        and batch.get("epoch_id") == ACTIVE_EPOCH_ID
        and batch.get("dispatch_contract_digest")
        == governance_dispatch_contract()["contract_digest"]
        and batch.get("ceremony_contract_digest")
        == governance_ceremony_contract()["contract_digest"]
        and issued < expires
        and batch.get("roles") == list(ROLES)
        and raw_challenges == reconstructed
        and [challenge.role for challenge in challenges] == list(ROLES)
        and all(
            challenge.authority_registry_digest
            == batch.get("authority_registry_digest")
            and challenge.handoff_bundle_root
            == batch.get("handoff_bundle_root")
            and challenge.issued_at == batch.get("issued_at")
            and challenge.expires_at == batch.get("expires_at")
            for challenge in challenges
        )
        and len(challenges) == GOVERNANCE_MEMBER_COUNT
        and len(challenge_ids) == len(set(challenge_ids))
        and len(nonces) == len(set(nonces))
        and batch.get("challenge_digests") == challenge_digests
        and len(challenge_digests) == len(set(challenge_digests))
        and batch.get("challenge_count") == GOVERNANCE_MEMBER_COUNT
        and batch.get("response_count") == 0
        and batch.get("status") == BATCH_STATUS
        and batch.get("governance_activated") is False
        and batch.get("truth_effect") == "NONE"
        and batch.get("batch_id") == _batch_id(challenge_digests)
        and batch.get("batch_root") == digest(body)
    )


def governance_challenge_batch_state(
    batch: Mapping[str, Any],
    *,
    checked_at: str,
) -> dict[str, Any]:
    integrity = challenge_batch_integrity(batch)
    lifecycle = "INVALID"
    accepting_responses = False
    try:
        checked = _parse_time(checked_at)
        issued = _parse_time(str(batch["issued_at"]))
        expires = _parse_time(str(batch["expires_at"]))
        if integrity and checked < issued:
            lifecycle = "NOT_YET_OPEN"
        elif integrity and checked <= expires:
            lifecycle = "OPEN"
            accepting_responses = True
        elif integrity:
            lifecycle = "EXPIRED"
    except (KeyError, TypeError, ValueError):
        integrity = False
    body = {
        "schema": "KC144.GovernanceChallengeBatchState.V11",
        "batch_id": batch.get("batch_id"),
        "batch_root": batch.get("batch_root"),
        "checked_at": checked_at,
        "integrity": "PASS" if integrity else "FAIL",
        "lifecycle": lifecycle,
        "accepting_responses": accepting_responses,
        "governance_activated": False,
        "truth_effect": "NONE",
    }
    return {**body, "state_digest": digest(body)}


def _duplicates(values: Sequence[str]) -> set[str]:
    return {
        value
        for value, count in Counter(values).items()
        if value and count > 1
    }


def route_governance_responses(
    batch: Mapping[str, Any],
    responses: Sequence[GovernanceEnrollmentResponse],
    *,
    verified_at: str,
) -> dict[str, Any]:
    batch_state = governance_challenge_batch_state(
        batch,
        checked_at=verified_at,
    )
    expected_by_role: dict[str, dict[str, Any]] = {}
    if batch_state["integrity"] == "PASS":
        expected_by_role = {
            value["role"]: value for value in batch["challenges"]
        }
    preliminary: list[dict[str, Any]] = []
    for response in responses:
        expected = expected_by_role.get(response.member.role)
        verification = verify_enrollment_response(
            response,
            verified_at=verified_at,
        )
        challenge_exact = (
            expected is not None
            and response.challenge.to_dict() == expected
        )
        preliminary.append(
            {
                "response": response,
                "response_id": response.response_id,
                "role": response.member.role,
                "challenge_exact": challenge_exact,
                "verification": verification,
                "preliminary_eligible": (
                    batch_state["accepting_responses"]
                    and challenge_exact
                    and verification["verdict"] == "PASS"
                ),
            }
        )
    eligible = [
        row for row in preliminary if row["preliminary_eligible"]
    ]
    collision_sets = {
        "response_id": _duplicates(
            [row["response"].response_id for row in eligible]
        ),
        "role": _duplicates(
            [row["response"].member.role for row in eligible]
        ),
        "challenge_id": _duplicates(
            [row["response"].challenge.challenge_id for row in eligible]
        ),
        "member_id": _duplicates(
            [row["response"].member.member_id for row in eligible]
        ),
        "public_key": _duplicates(
            [row["response"].member.public_key_b64 for row in eligible]
        ),
        "institution_root": _duplicates(
            [row["response"].institution_root for row in eligible]
        ),
        "lineage_root": _duplicates(
            [row["response"].lineage_root for row in eligible]
        ),
    }
    counted: list[GovernanceEnrollmentResponse] = []
    response_reports = []
    for row in preliminary:
        response = row["response"]
        collisions = sorted(
            field
            for field, values in collision_sets.items()
            if (
                (
                    response.response_id
                    if field == "response_id"
                    else response.member.role
                    if field == "role"
                    else response.challenge.challenge_id
                    if field == "challenge_id"
                    else response.member.member_id
                    if field == "member_id"
                    else response.member.public_key_b64
                    if field == "public_key"
                    else response.institution_root
                    if field == "institution_root"
                    else response.lineage_root
                )
                in values
            )
        )
        is_counted = row["preliminary_eligible"] and not collisions
        if is_counted:
            counted.append(response)
        response_reports.append(
            {
                "response_id": row["response_id"],
                "role": row["role"],
                "challenge_exact": row["challenge_exact"],
                "verification_verdict": row["verification"]["verdict"],
                "collisions": collisions,
                "counted": is_counted,
            }
        )
    counted.sort(key=lambda response: ROLES.index(response.member.role))
    counted_roles = [response.member.role for response in counted]
    remaining_roles = [role for role in ROLES if role not in counted_roles]
    pending_society = (
        assemble_pending_society(counted, verified_at=verified_at)
        if len(counted) == GOVERNANCE_MEMBER_COUNT
        else None
    )
    if batch_state["integrity"] != "PASS":
        barrier = "VALID_CHALLENGE_BATCH_REQUIRED"
        status = "INTAKE_HOLD"
    elif batch_state["lifecycle"] == "NOT_YET_OPEN":
        barrier = "CHALLENGE_BATCH_NOT_YET_OPEN"
        status = "INTAKE_HOLD"
    elif batch_state["lifecycle"] == "EXPIRED":
        barrier = "CHALLENGE_BATCH_REISSUE_REQUIRED"
        status = "INTAKE_HOLD"
    elif (
        pending_society is not None
        and pending_society["verdict"] == "PASS"
    ):
        barrier = "EXTERNAL_RATIFICATION_REQUIRED"
        status = "PENDING_SOCIETY_ASSEMBLED"
    else:
        barrier = (
            "FIVE_INDEPENDENT_PARTICIPANT_RESPONSES_REQUIRED"
            if len(counted) == 0
            else "REMAINING_EXTERNAL_PARTICIPANT_RESPONSES_REQUIRED"
        )
        status = "AWAITING_EXTERNAL_RESPONSES"
    body = {
        "schema": "KC144.GovernanceResponseRouter.V11",
        "dispatch_id": DISPATCH_ID,
        "batch_id": batch.get("batch_id"),
        "batch_root": batch.get("batch_root"),
        "verified_at": verified_at,
        "batch_state": batch_state,
        "supplied_response_count": len(responses),
        "counted_response_count": len(counted),
        "counted_roles": counted_roles,
        "remaining_roles": remaining_roles,
        "response_reports": response_reports,
        "pending_society": pending_society,
        "status": status,
        "barrier": barrier,
        "governance_activated": False,
        "production_certificate_issued": False,
        "truth_effect": "NONE",
    }
    return {**body, "router_digest": digest(body)}


def governance_dispatch_plan(
    *,
    authority_registry_digest: str,
    handoff_bundle_root: str,
    batch: Mapping[str, Any] | None = None,
    router: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if batch is None:
        status = "READY_TO_ISSUE"
        barrier = "CHALLENGE_BATCH_ISSUANCE_REQUIRED"
        next_seed = "KC144.V11::ISSUE-IMMUTABLE-FIVE-ROLE-BATCH"
        batch_id = None
        batch_root = None
    else:
        status = (
            str(router["status"])
            if router is not None
            else BATCH_STATUS
        )
        barrier = (
            str(router["barrier"])
            if router is not None
            else "FIVE_INDEPENDENT_PARTICIPANT_RESPONSES_REQUIRED"
        )
        if barrier == "EXTERNAL_RATIFICATION_REQUIRED":
            next_seed = "KC144.V11::EXTERNAL-RATIFICATION"
        elif barrier == "CHALLENGE_BATCH_REISSUE_REQUIRED":
            next_seed = "KC144.V11::REISSUE-IMMUTABLE-FIVE-ROLE-BATCH"
        elif barrier == "CHALLENGE_BATCH_NOT_YET_OPEN":
            next_seed = "KC144.V11::WAIT-FOR-ISSUANCE-TIME"
        else:
            next_seed = (
                "KC144.V11::AWAIT-FIVE-SIGNED-ROLE-BOUND-RESPONSES"
            )
        batch_id = batch.get("batch_id")
        batch_root = batch.get("batch_root")
    body = {
        "schema": "KC144.GovernanceDispatchPlan.V11",
        "dispatch_id": DISPATCH_ID,
        "parent_ceremony_id": CEREMONY_ID,
        "dispatch_contract_digest": governance_dispatch_contract()[
            "contract_digest"
        ],
        "authority_registry_digest": authority_registry_digest,
        "handoff_bundle_root": handoff_bundle_root,
        "batch_id": batch_id,
        "batch_root": batch_root,
        "status": status,
        "barrier": barrier,
        "next_seed": next_seed,
        "parallelism": "ALL_FIVE_ROLE_RESPONSES_ROUTE_IN_ONE_WAVE",
        "governance_activated": False,
        "truth_effect": "NONE",
    }
    return {**body, "plan_digest": digest(body)}
