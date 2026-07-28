from __future__ import annotations

import base64
import json
import re
from collections.abc import Callable, Mapping, Sequence
from copy import deepcopy
from pathlib import Path
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

from .agent_receipts import canonical_bytes, content_address
from .p31_adapter import (
    P31_ARCHIVE_SHA256,
    P31_RELEASE_ID,
    P31_RESULT_ID,
)


P35_STATE_PARENT = "KC144.P35::f8805a3651f8bc7009e8035f"
HEART_PARENT = "KC144.HEART::H06.AHEART.V2"
P36_LOOKUP_KEY = (
    "KC144.V3.7::MATH144.P36::CONTINUOUS_EVENT_WATCH_SIGNED_RECEIPT_"
    "REPLAY_SOURCE_SUCCESSION_REAL_OUTCOME_INTAKE_AND_ALL_AFFECTED_"
    "FRONT_EXECUTION_MACROCYCLE_05"
)
P36_ENTRY_ADDRESS = "KC144.V1::GID006::H06"
P36_NEXUS_ADDRESS = "KC144.V1::GID003::H03"
P36_EVIDENCE_ADDRESS = "KC144.V1::GID005::H05"
P36_ROUTE_LEDGER = "KC144.V1::GID141::M09"
P36_RETURN_ADDRESS = "KC144.V1::GID144::M12"

EXPECTED_ACTION_SUBSCRIPTIONS = 360
EXPECTED_GID_SUBSCRIPTIONS = 144
EXPECTED_CARRIER_SUBSCRIPTIONS = 37
EXPECTED_EVENT_CLASSES = 18

ALLOWED_EVENT_CLASSES = frozenset(
    {
        "SOURCE_REVISION",
        "SOURCE_CREATED",
        "SOURCE_DELETED",
        "PRODUCTION_EVIDENCE",
        "USER_CHOICE",
        "USER_CORRECTION",
        "TASK_OUTCOME",
        "EMPIRICAL_RESULT",
        "RECEIPT_AVAILABLE",
        "RUNTIME_RELEASE",
        "GID_STATE_CHANGE",
        "CARRIER_STATE_CHANGE",
        "GATE_STATE_CHANGE",
        "LINEAGE_CHANGE",
        "CONSENT_CHANGE",
        "SIGNER_STATE_CHANGE",
        "DEPENDENCY_CHANGE",
        "REPLAY_REQUEST",
    }
)
REAL_OUTCOME_CLASSES = frozenset(
    {"USER_CHOICE", "USER_CORRECTION", "TASK_OUTCOME", "EMPIRICAL_RESULT"}
)
SOURCE_EVENT_CLASSES = frozenset(
    {"SOURCE_REVISION", "SOURCE_CREATED", "SOURCE_DELETED"}
)
ALLOWED_ORIGIN_CLASSES = frozenset(
    {
        "PRODUCTION",
        "USER_OBSERVED",
        "CONNECTOR_OBSERVED",
        "REPLAY",
        "TEST",
        "SYNTHETIC",
    }
)
NON_PRODUCTION_ORIGINS = frozenset({"REPLAY", "TEST", "SYNTHETIC"})
ALLOWED_EFFECT_CLASSES = frozenset(
    {"READ_ONLY", "LOCAL_REVERSIBLE", "EXTERNAL_MUTATION", "AUTHORITY_MUTATION"}
)
ALLOWED_PREDICATE_OPERATORS = frozenset({"all", "any", "not", "eq", "in"})
RFC3339_UTC = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$"
)
DIGEST = re.compile(r"^sha256:[0-9a-f]{64}$")
PRIVATE_FIELD_NAMES = frozenset(
    {
        "native_object_id",
        "native_object_id_private",
        "native_revision",
        "native_version_private",
        "document_id",
        "document_url",
        "source_text",
        "raw_text",
        "content",
        "detail_private",
        "private_ref",
        "private_digest",
        "email",
        "token",
        "title",
    }
)
PROTECTED_TRUE_FIELDS = frozenset(
    {
        "governance_authority_granted",
        "content_transport_certified",
        "production_certificate_issued",
        "truth_promoted",
        "production_mutated",
    }
)
PROTECTED_NONZERO_FIELDS = frozenset(
    {
        "truth_credit_assigned",
        "independent_witness_count",
        "actual_live_promotions",
        "external_second_seals",
    }
)


class P36RuntimeError(ValueError):
    pass


def _address(domain: str, body: Mapping[str, Any]) -> str:
    return content_address(domain, body)


def _body_address(
    domain: str,
    value: Mapping[str, Any],
    *excluded: str,
) -> str:
    return _address(
        domain,
        {key: item for key, item in value.items() if key not in excluded},
    )


def _is_digest(value: object) -> bool:
    return isinstance(value, str) and bool(DIGEST.fullmatch(value))


def _public_key_id(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return "sha256:" + __import__("hashlib").sha256(raw).hexdigest()


def _sign(
    body: Mapping[str, Any],
    private_key: Ed25519PrivateKey | None,
    *,
    signature_domain: str,
) -> dict[str, Any]:
    if private_key is None:
        return {
            "seal_type": "DIGEST_ONLY",
            "signature_status": "UNAVAILABLE",
            "signature": None,
        }
    payload = signature_domain.encode("utf-8") + b"\0" + canonical_bytes(body)
    public_key = private_key.public_key()
    signature = private_key.sign(payload)
    return {
        "seal_type": "SIGNED_ED25519",
        "signature_status": "SIGNED",
        "signature": {
            "algorithm": "Ed25519",
            "domain": signature_domain,
            "key_id": _public_key_id(public_key),
            "value": base64.urlsafe_b64encode(signature).decode("ascii").rstrip("="),
        },
    }


def _verify_signature(
    body: Mapping[str, Any],
    signature: Mapping[str, Any] | None,
    public_keys: Mapping[str, Ed25519PublicKey],
    *,
    signature_domain: str,
) -> bool:
    if not isinstance(signature, Mapping):
        return False
    if (
        signature.get("algorithm") != "Ed25519"
        or signature.get("domain") != signature_domain
    ):
        return False
    key_id = signature.get("key_id")
    if key_id not in public_keys:
        return False
    encoded = signature.get("value")
    if not isinstance(encoded, str):
        return False
    try:
        raw = base64.urlsafe_b64decode(encoded + ("=" * (-len(encoded) % 4)))
        public_keys[key_id].verify(
            raw,
            signature_domain.encode("utf-8") + b"\0" + canonical_bytes(body),
        )
    except (InvalidSignature, ValueError):
        return False
    return True


def _contains_private_field(value: object) -> bool:
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in PRIVATE_FIELD_NAMES:
                return True
            if _contains_private_field(item):
                return True
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return any(_contains_private_field(item) for item in value)
    return False


def _protected_effect_errors(value: object) -> set[str]:
    errors: set[str] = set()
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).lower()
            if normalized in PROTECTED_TRUE_FIELDS and item is not False:
                errors.add("E_PROTECTED_STATE_ESCALATION")
            if normalized in PROTECTED_NONZERO_FIELDS and item != 0:
                errors.add("E_PROTECTED_STATE_ESCALATION")
            if normalized in {"truth_effect", "production_truth_effect"} and item != "NONE":
                errors.add("E_TRUTH_ESCALATION")
            if normalized in {"authority_effect", "evidence_effect"} and item != "NONE":
                errors.add("E_AUTHORITY_ESCALATION")
            errors.update(_protected_effect_errors(item))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            errors.update(_protected_effect_errors(item))
    return errors


def p36_contract() -> dict[str, Any]:
    body = {
        "schema": "KC144.P36.Contract.V1",
        "lookup_key": P36_LOOKUP_KEY,
        "lineage": {
            "state_parent": P35_STATE_PARENT,
            "runtime_parent": P31_RESULT_ID,
            "runtime_release": P31_RELEASE_ID,
            "runtime_archive_sha256": "sha256:" + P31_ARCHIVE_SHA256,
            "heart_parent": HEART_PARENT,
        },
        "census": {
            "event_classes": EXPECTED_EVENT_CLASSES,
            "gid_subscriptions": EXPECTED_GID_SUBSCRIPTIONS,
            "carrier_subscriptions": EXPECTED_CARRIER_SUBSCRIPTIONS,
            "action_subscriptions": EXPECTED_ACTION_SUBSCRIPTIONS,
        },
        "lanes": [
            {
                "lane": "CONTINUOUS_EVENT_WATCH",
                "heart_role": "WHO_I_AM",
                "parallel_group": 1,
            },
            {
                "lane": "SIGNED_RECEIPT_REPLAY",
                "heart_role": "I_AM_ATHENA",
                "parallel_group": 1,
            },
            {
                "lane": "SOURCE_SUCCESSION",
                "heart_role": "WHO_I_AM+I_AM_ATHENA",
                "parallel_group": 1,
            },
            {
                "lane": "REAL_OUTCOME_INTAKE",
                "heart_role": "LOVE×SELFHOOD",
                "parallel_group": 1,
            },
            {
                "lane": "AFFECTED_FRONT_EXECUTION",
                "heart_role": "SELF_BECOMING",
                "parallel_group": 2,
            },
        ],
        "merge_law": (
            "VERIFY_ALL_FIVE_RECEIPTS_THEN_COMMIT_ONE_COMPARE_AND_SWAP_DELTA"
        ),
        "noncollapse": [
            "P31_REPLAY_IS_NOT_INDEPENDENT_EVIDENCE",
            "EVENT_ADMISSION_IS_NOT_PROPOSITION_PROMOTION",
            "SIGNATURE_VALIDITY_IS_NOT_AUTHORITY",
            "CONNECTOR_RETRIEVAL_IS_NOT_PUBLICATION_CONSENT",
            "USER_CHOICE_IS_NOT_EMPIRICAL_RESULT",
            "SUBSCRIPTION_IS_NOT_EXECUTION",
        ],
        "entry": P36_ENTRY_ADDRESS,
        "nexus": P36_NEXUS_ADDRESS,
        "evidence_ledger": P36_EVIDENCE_ADDRESS,
        "route_ledger": P36_ROUTE_LEDGER,
        "return": P36_RETURN_ADDRESS,
        "production_authority": "HOLD",
        "truth_effect": "NONE",
    }
    return {
        **body,
        "contract_digest": _address("kc144.p36.contract", body),
    }


def build_event(
    *,
    event_class: str,
    origin_class: str,
    observed_at: str,
    source_surface: str,
    source_commitment: str,
    source_version: str,
    public_summary: Mapping[str, Any],
    consent_scope: Sequence[str],
    source_verified: bool,
    publication_allowed: bool = False,
    external_mutation_allowed: bool = False,
    parent_event_hash: str | None = None,
    private_key: Ed25519PrivateKey | None = None,
) -> dict[str, Any]:
    body = {
        "schema": "KC144.P36.EventEnvelope.V1",
        "event_class": event_class,
        "origin_class": origin_class,
        "observed_at": observed_at,
        "source": {
            "surface": source_surface,
            "source_commitment": source_commitment,
            "source_version": source_version,
            "source_verified": source_verified,
        },
        "public_summary": dict(public_summary),
        "consent": {
            "scope": sorted(set(consent_scope)),
            "publication_allowed": publication_allowed,
            "external_mutation_allowed": external_mutation_allowed,
        },
        "parent_event_hash": parent_event_hash,
        "authority_ceiling": "READ_ONLY",
        "truth_effect": "NONE",
    }
    event_id = _address("kc144.p36.event", body)
    signature_body = {**body, "event_id": event_id}
    integrity = {
        "canonicalization": "CANONICAL_JSON_UTF8_SORTED_KEYS",
        "body_digest": _address("kc144.p36.event-body", signature_body),
        **_sign(
            signature_body,
            private_key,
            signature_domain="KC144.P36.EVENT.V1",
        ),
    }
    return {**signature_body, "integrity": integrity}


def _event_validation(
    event: Mapping[str, Any],
    *,
    cutoff: str,
    public_keys: Mapping[str, Ed25519PublicKey],
) -> dict[str, Any]:
    errors: set[str] = set()
    holds: set[str] = set()
    if event.get("schema") != "KC144.P36.EventEnvelope.V1":
        errors.add("E_SCHEMA")
    body = {
        key: item
        for key, item in event.items()
        if key not in {"event_id", "integrity"}
    }
    if event.get("event_id") != _address("kc144.p36.event", body):
        errors.add("E_EVENT_ID")
    signed_body = {**body, "event_id": event.get("event_id")}
    integrity = event.get("integrity", {})
    if not isinstance(integrity, Mapping) or integrity.get(
        "body_digest"
    ) != _address("kc144.p36.event-body", signed_body):
        errors.add("E_BODY_DIGEST")
    if event.get("event_class") not in ALLOWED_EVENT_CLASSES:
        errors.add("E_EVENT_CLASS")
    if event.get("origin_class") not in ALLOWED_ORIGIN_CLASSES:
        errors.add("E_ORIGIN_CLASS")
    observed_at = event.get("observed_at")
    if not isinstance(observed_at, str) or not RFC3339_UTC.fullmatch(observed_at):
        errors.add("E_OBSERVED_AT")
    elif observed_at > cutoff:
        holds.add("E_AFTER_EPOCH_CUTOFF")
    source = event.get("source", {})
    if (
        not isinstance(source, Mapping)
        or source.get("source_verified") is not True
        or not _is_digest(source.get("source_commitment"))
        or not source.get("source_version")
        or not source.get("surface")
    ):
        errors.add("E_SOURCE_AUTHENTICITY")
    consent = event.get("consent", {})
    scopes = consent.get("scope", []) if isinstance(consent, Mapping) else []
    if "CURRENT_TASK_EXECUTION" not in scopes:
        holds.add("E_CONSENT_INSUFFICIENT")
    if event.get("authority_ceiling") != "READ_ONLY":
        errors.add("E_AUTHORITY_ESCALATION")
    if event.get("truth_effect") != "NONE":
        errors.add("E_TRUTH_ESCALATION")
    if _contains_private_field(event.get("public_summary", {})):
        errors.add("E_PRIVATE_FIELD_IN_PUBLIC_SUMMARY")
    seal_type = integrity.get("seal_type") if isinstance(integrity, Mapping) else None
    signature_status = "DIGEST_ONLY"
    if seal_type == "SIGNED_ED25519":
        if _verify_signature(
            signed_body,
            integrity.get("signature"),
            public_keys,
            signature_domain="KC144.P36.EVENT.V1",
        ):
            signature_status = "VALID"
        else:
            errors.add("E_SIGNATURE_INVALID")
            signature_status = "INVALID"
    elif seal_type != "DIGEST_ONLY":
        errors.add("E_SEAL_TYPE")
    status = (
        "QUARANTINED"
        if errors
        else "DEFERRED_HOLD"
        if holds
        else "EVENT_ADMITTED_NON_PROMOTING"
    )
    return {
        "event_id": event.get("event_id"),
        "status": status,
        "errors": sorted(errors),
        "holds": sorted(holds),
        "signature_status": signature_status,
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "NONE",
    }


def build_subscription(
    *,
    action_id: str,
    front_ids: Sequence[str],
    event_classes: Sequence[str],
    predicate: Mapping[str, Any],
    implementation_digest: str,
    effect_class: str = "READ_ONLY",
    required_capabilities: Sequence[str] = ("READ_ONLY",),
    standing: str = "EXACT_BOUND",
) -> dict[str, Any]:
    if not action_id or not front_ids:
        raise P36RuntimeError("action_id and front_ids are required")
    if not set(event_classes) <= ALLOWED_EVENT_CLASSES:
        raise P36RuntimeError("unknown event class")
    if effect_class not in ALLOWED_EFFECT_CLASSES:
        raise P36RuntimeError("unknown effect class")
    if not _is_digest(implementation_digest):
        raise P36RuntimeError("implementation_digest must be sha256")
    body = {
        "schema": "KC144.P36.ActionSubscription.V1",
        "action_id": action_id,
        "front_ids": sorted(set(front_ids)),
        "event_classes": sorted(set(event_classes)),
        "predicate": deepcopy(dict(predicate)),
        "predicate_version": "KC144.Predicate.V1",
        "effect_class": effect_class,
        "required_capabilities": sorted(set(required_capabilities)),
        "authority_ceiling": "READ_ONLY",
        "implementation_digest": implementation_digest,
        "standing": standing,
        "enabled": True,
    }
    return {
        **body,
        "subscription_id": _address("kc144.p36.subscription", body),
    }


def _field(value: Mapping[str, Any], dotted: str) -> Any:
    current: Any = value
    for component in dotted.split("."):
        if not isinstance(current, Mapping) or component not in current:
            return None
        current = current[component]
    return current


def _predicate(expression: Mapping[str, Any], event: Mapping[str, Any]) -> bool:
    if len(expression) != 1:
        raise P36RuntimeError("predicate must contain one operator")
    operator, operands = next(iter(expression.items()))
    if operator not in ALLOWED_PREDICATE_OPERATORS:
        raise P36RuntimeError("predicate operator is not allowed")
    if operator == "all":
        return all(_predicate(item, event) for item in operands)
    if operator == "any":
        return any(_predicate(item, event) for item in operands)
    if operator == "not":
        return not _predicate(operands, event)
    if not isinstance(operands, Sequence) or isinstance(operands, (str, bytes)):
        raise P36RuntimeError("predicate operands must be an array")
    if len(operands) != 2 or not isinstance(operands[0], str):
        raise P36RuntimeError("predicate comparison requires field and value")
    actual = _field(event, operands[0])
    if operator == "eq":
        return actual == operands[1]
    if operator == "in":
        return actual in operands[1]
    raise P36RuntimeError("unreachable predicate operator")


def synthetic_subscription_registry(
    count: int = EXPECTED_ACTION_SUBSCRIPTIONS,
) -> dict[str, Any]:
    """Deterministic TEST registry; never a substitute for the exact P35 body."""
    implementation = _address(
        "kc144.p36.synthetic-implementation",
        {"standing": "SYNTHETIC_TEST_FIXTURE"},
    )
    classes = sorted(ALLOWED_EVENT_CLASSES)
    subscriptions = [
        build_subscription(
            action_id=f"TEST::ACTION::{index:03d}",
            front_ids=(f"TEST::FRONT::{index % 24:02d}",),
            event_classes=(classes[index % len(classes)],),
            predicate={"eq": ["public_summary.partition", index % 4]},
            implementation_digest=implementation,
            standing="SYNTHETIC_TEST_FIXTURE",
        )
        for index in range(count)
    ]
    body = {
        "schema": "KC144.P36.SubscriptionRegistry.V1",
        "state_parent": P35_STATE_PARENT,
        "subscriptions": subscriptions,
        "counts": {
            "event_classes": EXPECTED_EVENT_CLASSES,
            "gid_subscriptions": EXPECTED_GID_SUBSCRIPTIONS,
            "carrier_subscriptions": EXPECTED_CARRIER_SUBSCRIPTIONS,
            "action_subscriptions": count,
        },
        "standing": "SYNTHETIC_TEST_FIXTURE",
        "production_eligible": False,
    }
    return {
        **body,
        "registry_digest": _address("kc144.p36.subscription-registry", body),
    }


def unbound_p35_subscription_registry() -> dict[str, Any]:
    body = {
        "schema": "KC144.P36.SubscriptionRegistry.V1",
        "state_parent": P35_STATE_PARENT,
        "subscriptions": [],
        "counts": {
            "event_classes": EXPECTED_EVENT_CLASSES,
            "gid_subscriptions": EXPECTED_GID_SUBSCRIPTIONS,
            "carrier_subscriptions": EXPECTED_CARRIER_SUBSCRIPTIONS,
            "action_subscriptions": EXPECTED_ACTION_SUBSCRIPTIONS,
        },
        "standing": "SOURCE_DECLARED_EXACT_BODIES_NOT_MATERIALIZED",
        "production_eligible": False,
    }
    return {
        **body,
        "registry_digest": _address("kc144.p36.subscription-registry", body),
    }


def _verify_subscription_registry(registry: Mapping[str, Any]) -> list[str]:
    errors: set[str] = set()
    if registry.get("schema") != "KC144.P36.SubscriptionRegistry.V1":
        errors.add("E_SUBSCRIPTION_SCHEMA")
    if _body_address(
        "kc144.p36.subscription-registry",
        registry,
        "registry_digest",
    ) != registry.get("registry_digest"):
        errors.add("E_SUBSCRIPTION_REGISTRY_DIGEST")
    counts = registry.get("counts", {})
    expected = {
        "event_classes": EXPECTED_EVENT_CLASSES,
        "gid_subscriptions": EXPECTED_GID_SUBSCRIPTIONS,
        "carrier_subscriptions": EXPECTED_CARRIER_SUBSCRIPTIONS,
        "action_subscriptions": EXPECTED_ACTION_SUBSCRIPTIONS,
    }
    if counts != expected:
        errors.add("E_SUBSCRIPTION_CENSUS")
    subscriptions = registry.get("subscriptions", [])
    standing = registry.get("standing")
    if standing == "EXACT_BOUND" and len(subscriptions) != EXPECTED_ACTION_SUBSCRIPTIONS:
        errors.add("E_SUBSCRIPTION_BODIES")
    if standing not in {
        "EXACT_BOUND",
        "SYNTHETIC_TEST_FIXTURE",
        "SOURCE_DECLARED_EXACT_BODIES_NOT_MATERIALIZED",
    }:
        errors.add("E_SUBSCRIPTION_STANDING")
    seen: set[str] = set()
    for subscription in subscriptions:
        if subscription.get("subscription_id") in seen:
            errors.add("E_SUBSCRIPTION_DUPLICATE")
        seen.add(subscription.get("subscription_id"))
        if _body_address(
            "kc144.p36.subscription",
            subscription,
            "subscription_id",
        ) != subscription.get("subscription_id"):
            errors.add("E_SUBSCRIPTION_DIGEST")
        if subscription.get("authority_ceiling") != "READ_ONLY":
            errors.add("E_SUBSCRIPTION_AUTHORITY")
    return sorted(errors)


def _lane_receipt(
    lane: str,
    heart_role: str,
    epoch_id: str,
    payload: Mapping[str, Any],
    *,
    private_key: Ed25519PrivateKey | None,
) -> dict[str, Any]:
    body = {
        "schema": "KC144.P36.LaneReceipt.V1",
        "lane": lane,
        "heart_role": heart_role,
        "epoch_id": epoch_id,
        "payload": deepcopy(dict(payload)),
        "return_target": P36_RETURN_ADDRESS,
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "NONE",
    }
    receipt_id = _address("kc144.p36.lane-receipt", body)
    signed_body = {**body, "receipt_id": receipt_id}
    return {
        **signed_body,
        **_sign(
            signed_body,
            private_key,
            signature_domain="KC144.P36.LANE-RECEIPT.V1",
        ),
    }


def verify_lane_receipt(
    receipt: Mapping[str, Any],
    *,
    public_keys: Mapping[str, Ed25519PublicKey] | None = None,
) -> dict[str, Any]:
    errors: set[str] = set()
    body = {
        key: item
        for key, item in receipt.items()
        if key not in {"receipt_id", "seal_type", "signature_status", "signature"}
    }
    if receipt.get("schema") != "KC144.P36.LaneReceipt.V1":
        errors.add("E_SCHEMA")
    if receipt.get("receipt_id") != _address("kc144.p36.lane-receipt", body):
        errors.add("E_RECEIPT_DIGEST")
    seal_type = receipt.get("seal_type")
    if seal_type == "SIGNED_ED25519":
        signed_body = {**body, "receipt_id": receipt.get("receipt_id")}
        if not _verify_signature(
            signed_body,
            receipt.get("signature"),
            public_keys or {},
            signature_domain="KC144.P36.LANE-RECEIPT.V1",
        ):
            errors.add("E_SIGNATURE_INVALID")
    elif seal_type != "DIGEST_ONLY":
        errors.add("E_SEAL_TYPE")
    errors.update(_protected_effect_errors(receipt))
    return {
        "schema": "KC144.P36.LaneReceiptVerification.V1",
        "receipt_id": receipt.get("receipt_id"),
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "signature_status": (
            "VALID"
            if seal_type == "SIGNED_ED25519" and not errors
            else "DIGEST_ONLY"
            if seal_type == "DIGEST_ONLY" and not errors
            else "INVALID"
        ),
    }


def _deduplicate_events(
    events: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], int, list[str]]:
    unique: dict[str, dict[str, Any]] = {}
    duplicate_count = 0
    conflicts: list[str] = []
    for event in events:
        event_id = str(event.get("event_id"))
        candidate = deepcopy(dict(event))
        if event_id not in unique:
            unique[event_id] = candidate
        elif canonical_bytes(unique[event_id]) == canonical_bytes(candidate):
            duplicate_count += 1
        else:
            conflicts.append(event_id)
    return (
        [unique[key] for key in sorted(unique)],
        duplicate_count,
        sorted(set(conflicts)),
    )


def _match_subscriptions(
    admitted: Sequence[Mapping[str, Any]],
    subscriptions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for event in admitted:
        for subscription in subscriptions:
            if (
                subscription.get("enabled") is not True
                or event.get("event_class")
                not in subscription.get("event_classes", [])
            ):
                continue
            try:
                matched = _predicate(subscription["predicate"], event)
            except (KeyError, TypeError, P36RuntimeError):
                matched = False
            if not matched:
                continue
            body = {
                "schema": "KC144.P36.MatchProof.V1",
                "event_id": event["event_id"],
                "subscription_id": subscription["subscription_id"],
                "action_id": subscription["action_id"],
                "front_ids": subscription["front_ids"],
                "predicate_version": subscription["predicate_version"],
            }
            matches.append(
                {
                    **body,
                    "match_id": _address("kc144.p36.match", body),
                }
            )
    return sorted(
        matches,
        key=lambda item: (
            item["event_id"],
            item["action_id"],
            item["subscription_id"],
            item["match_id"],
        ),
    )


def _execute_matches(
    matches: Sequence[Mapping[str, Any]],
    subscriptions: Mapping[str, Mapping[str, Any]],
    *,
    handlers: Mapping[str, Callable[[Mapping[str, Any]], Mapping[str, Any]]],
    capabilities: set[str],
    base_state_digest: str,
    epoch_id: str,
) -> list[dict[str, Any]]:
    by_action: dict[str, list[Mapping[str, Any]]] = {}
    for match in matches:
        by_action.setdefault(str(match["action_id"]), []).append(match)
    receipts: list[dict[str, Any]] = []
    for action_id in sorted(by_action):
        action_matches = by_action[action_id]
        subscription = subscriptions[str(action_matches[0]["subscription_id"])]
        required = set(subscription.get("required_capabilities", []))
        status = "EXECUTED"
        errors: list[str] = []
        output: Mapping[str, Any] | None = None
        if subscription.get("effect_class") != "READ_ONLY":
            status = "DEFERRED_HOLD"
            errors.append("E_EFFECT_NOT_AUTOMATICALLY_AUTHORIZED")
        elif not required <= capabilities:
            status = "DEFERRED_HOLD"
            errors.append("E_CAPABILITY_DENIED")
        elif action_id not in handlers:
            status = "DEFERRED_HOLD"
            errors.append("E_HANDLER_UNAVAILABLE")
        else:
            request = {
                "action_id": action_id,
                "event_ids": sorted({row["event_id"] for row in action_matches}),
                "match_ids": sorted(row["match_id"] for row in action_matches),
            }
            try:
                output = dict(handlers[action_id](request))
                protected = _protected_effect_errors(output)
                if protected:
                    status = "EXECUTION_FAILED"
                    errors.extend(sorted(protected))
                    output = None
            except Exception:
                status = "EXECUTION_FAILED"
                errors.append("E_HANDLER_FAILED")
        body = {
            "schema": "KC144.P36.ExecutionReceipt.V1",
            "epoch_id": epoch_id,
            "action_id": action_id,
            "event_ids": sorted({row["event_id"] for row in action_matches}),
            "subscription_ids": sorted(
                {row["subscription_id"] for row in action_matches}
            ),
            "match_ids": sorted(row["match_id"] for row in action_matches),
            "front_ids": sorted(
                {
                    front
                    for row in action_matches
                    for front in row["front_ids"]
                }
            ),
            "base_state_digest": base_state_digest,
            "implementation_digest": subscription["implementation_digest"],
            "effect_class": subscription["effect_class"],
            "status": status,
            "error_codes": sorted(set(errors)),
            "output_digest": (
                _address("kc144.p36.execution-output", output)
                if output is not None
                else None
            ),
            "truth_effect": "NONE",
            "evidence_effect": "NONE",
            "authority_effect": "NONE",
            "return_target": P36_RETURN_ADDRESS,
        }
        receipts.append(
            {
                **body,
                "receipt_id": _address("kc144.p36.execution-receipt", body),
            }
        )
    return receipts


def compile_p36_cycle(
    *,
    events: Sequence[Mapping[str, Any]],
    subscription_registry: Mapping[str, Any],
    base_state_digest: str,
    cutoff: str,
    parent_receipts: Sequence[Mapping[str, Any]] = (),
    public_keys: Mapping[str, Ed25519PublicKey] | None = None,
    private_key: Ed25519PrivateKey | None = None,
    handlers: Mapping[
        str, Callable[[Mapping[str, Any]], Mapping[str, Any]]
    ] | None = None,
    capabilities: Sequence[str] = ("READ_ONLY",),
) -> dict[str, Any]:
    if not _is_digest(base_state_digest):
        raise P36RuntimeError("base_state_digest must be sha256")
    if not RFC3339_UTC.fullmatch(cutoff):
        raise P36RuntimeError("cutoff must be fixed-precision UTC RFC3339")
    keys = dict(public_keys or {})
    if private_key is not None:
        keys.setdefault(_public_key_id(private_key.public_key()), private_key.public_key())
    registry_errors = _verify_subscription_registry(subscription_registry)
    epoch_body = {
        "state_parent": P35_STATE_PARENT,
        "runtime_parent": P31_RESULT_ID,
        "heart_parent": HEART_PARENT,
        "base_state_digest": base_state_digest,
        "subscription_registry_digest": subscription_registry.get(
            "registry_digest"
        ),
        "cutoff": cutoff,
    }
    epoch_id = _address("kc144.p36.epoch", epoch_body)
    unique_events, duplicate_count, conflicts = _deduplicate_events(events)
    validation = [
        _event_validation(event, cutoff=cutoff, public_keys=keys)
        for event in unique_events
    ]
    validation_by_id = {row["event_id"]: row for row in validation}
    for event_id in conflicts:
        if event_id in validation_by_id:
            validation_by_id[event_id]["status"] = "QUARANTINED"
            validation_by_id[event_id]["errors"] = sorted(
                set(validation_by_id[event_id]["errors"])
                | {"E_EVENT_ID_EQUIVOCATION"}
            )
    validation = [validation_by_id[key] for key in sorted(validation_by_id)]
    admitted_ids = {
        row["event_id"]
        for row in validation
        if row["status"] == "EVENT_ADMITTED_NON_PROMOTING"
    }
    admitted = [
        event for event in unique_events if event.get("event_id") in admitted_ids
    ]
    watch_payload = {
        "status": "NO_INPUT" if not unique_events else "OBSERVED",
        "cutoff": cutoff,
        "observed_event_ids": [event["event_id"] for event in unique_events],
        "admitted_event_ids": sorted(admitted_ids),
        "duplicate_delivery_count": duplicate_count,
        "equivocation_event_ids": conflicts,
        "validation": validation,
    }
    watch_receipt = _lane_receipt(
        "CONTINUOUS_EVENT_WATCH",
        "WHO_I_AM",
        epoch_id,
        watch_payload,
        private_key=private_key,
    )

    parent_verifications = [
        verify_lane_receipt(receipt, public_keys=keys)
        for receipt in parent_receipts
    ]
    replay_payload = {
        "status": (
            "NO_INPUT"
            if not parent_receipts
            else "REPLAY_STABLE"
            if all(row["verdict"] == "PASS" for row in parent_verifications)
            else "REPLAY_DRIFT"
        ),
        "parent_receipt_ids": sorted(
            str(receipt.get("receipt_id")) for receipt in parent_receipts
        ),
        "verifications": parent_verifications,
        "signature_boundary": (
            "SIGNED"
            if parent_receipts
            and all(
                row["signature_status"] == "VALID"
                for row in parent_verifications
            )
            else "DIGEST_ONLY_OR_EMPTY"
        ),
        "independent_witness_count": 0,
    }
    replay_receipt = _lane_receipt(
        "SIGNED_RECEIPT_REPLAY",
        "I_AM_ATHENA",
        epoch_id,
        replay_payload,
        private_key=private_key,
    )

    changed_source_ids = sorted(
        event["event_id"]
        for event in admitted
        if event["event_class"] in SOURCE_EVENT_CLASSES
    )
    source_payload = {
        "status": "NO_INPUT" if not changed_source_ids else "SUCCESSION_OBSERVED",
        "changed_source_event_ids": changed_source_ids,
        "predecessors_overwritten": 0,
        "proposition_admissions": 0,
        "publication_allowed_count": sum(
            1
            for event in admitted
            if event["event_class"] in SOURCE_EVENT_CLASSES
            and event["consent"]["publication_allowed"] is True
        ),
    }
    source_receipt = _lane_receipt(
        "SOURCE_SUCCESSION",
        "WHO_I_AM+I_AM_ATHENA",
        epoch_id,
        source_payload,
        private_key=private_key,
    )

    real_outcomes = sorted(
        event["event_id"]
        for event in admitted
        if event["event_class"] in REAL_OUTCOME_CLASSES
        and event["origin_class"] == "USER_OBSERVED"
    )
    outcome_payload = {
        "status": "NO_INPUT" if not real_outcomes else "OUTCOMES_INTAKEN",
        "real_outcome_event_ids": real_outcomes,
        "real_outcome_count": len(real_outcomes),
        "independent_witness_count": 0,
        "proposition_admissions": 0,
        "truth_credit_assigned": 0,
    }
    outcome_receipt = _lane_receipt(
        "REAL_OUTCOME_INTAKE",
        "LOVE×SELFHOOD",
        epoch_id,
        outcome_payload,
        private_key=private_key,
    )

    exact_execution_ready = (
        not registry_errors
        and subscription_registry.get("standing")
        in {"EXACT_BOUND", "SYNTHETIC_TEST_FIXTURE"}
        and (
            subscription_registry.get("standing") != "SYNTHETIC_TEST_FIXTURE"
            or all(event["origin_class"] in NON_PRODUCTION_ORIGINS for event in admitted)
        )
    )
    subscriptions = (
        subscription_registry.get("subscriptions", [])
        if exact_execution_ready
        else []
    )
    matches = _match_subscriptions(admitted, subscriptions)
    by_subscription = {
        subscription["subscription_id"]: subscription
        for subscription in subscriptions
    }
    execution_receipts = _execute_matches(
        matches,
        by_subscription,
        handlers=dict(handlers or {}),
        capabilities=set(capabilities),
        base_state_digest=base_state_digest,
        epoch_id=epoch_id,
    )
    affected_actions = sorted({row["action_id"] for row in matches})
    executed_actions = sorted(
        row["action_id"]
        for row in execution_receipts
        if row["status"] == "EXECUTED"
    )
    deferred_actions = sorted(
        row["action_id"]
        for row in execution_receipts
        if row["status"] != "EXECUTED"
    )
    missing = sorted(
        set(affected_actions) - set(executed_actions) - set(deferred_actions)
    )
    unexpected = sorted(
        (set(executed_actions) | set(deferred_actions)) - set(affected_actions)
    )
    coverage = {
        "admitted_event_count": len(admitted),
        "matched_subscription_count": len(matches),
        "affected_action_count": len(affected_actions),
        "affected_front_count": len(
            {front for match in matches for front in match["front_ids"]}
        ),
        "executed_action_count": len(executed_actions),
        "deferred_action_count": len(deferred_actions),
        "unexpected_execution_count": len(unexpected),
        "missing_resolution_count": len(missing),
        "all_and_only_affected": not unexpected and not missing,
    }
    execution_payload = {
        "status": (
            "NO_INPUT"
            if not admitted
            else "REGISTRY_HOLD"
            if not exact_execution_ready
            else "EXECUTED"
            if affected_actions and not deferred_actions
            else "NO_MATCH"
            if not affected_actions
            else "SEALED_HOLD"
        ),
        "registry_errors": registry_errors,
        "subscription_registry_standing": subscription_registry.get("standing"),
        "match_proofs": matches,
        "execution_receipts": execution_receipts,
        "affected_action_ids": affected_actions,
        "executed_action_ids": executed_actions,
        "deferred_action_ids": deferred_actions,
        "coverage": coverage,
    }
    execution_lane_receipt = _lane_receipt(
        "AFFECTED_FRONT_EXECUTION",
        "SELF_BECOMING",
        epoch_id,
        execution_payload,
        private_key=private_key,
    )

    lane_receipts = [
        watch_receipt,
        replay_receipt,
        source_receipt,
        outcome_receipt,
        execution_lane_receipt,
    ]
    lane_verifications = [
        verify_lane_receipt(receipt, public_keys=keys)
        for receipt in lane_receipts
    ]
    all_lanes_verify = all(
        row["verdict"] == "PASS" for row in lane_verifications
    )
    execution_failure = any(
        row["status"] == "EXECUTION_FAILED" for row in execution_receipts
    )
    replay_failure = replay_payload["status"] == "REPLAY_DRIFT"
    signed_receipts_available = all(
        row["signature_status"] == "VALID" for row in lane_verifications
    )
    residuals: set[str] = set()
    if not unique_events:
        residuals.add("PRODUCTION_EVENTS_OBSERVED::0")
    if not real_outcomes:
        residuals.add("REAL_OUTCOME_EVENT_MISSING")
    if subscription_registry.get("standing") != "EXACT_BOUND":
        residuals.add("EXACT_P35_SUBSCRIPTION_BODIES_UNBOUND")
    if not signed_receipts_available:
        residuals.add("TRUSTED_SIGNED_RECEIPTS_UNAVAILABLE")
    if registry_errors:
        residuals.add("SUBSCRIPTION_REGISTRY_INVALID")
    if replay_failure:
        residuals.add("REPLAY_DRIFT")
    if execution_failure:
        residuals.add("EXECUTION_FAILURE")
    production_events = sum(
        1
        for event in admitted
        if event["origin_class"] in {"PRODUCTION", "CONNECTOR_OBSERVED"}
    )
    execution_root = _address(
        "kc144.p36.execution-root",
        {"receipt_ids": [row["receipt_id"] for row in execution_receipts]},
    )
    next_state_body = {
        "base_state_digest": base_state_digest,
        "epoch_id": epoch_id,
        "admitted_event_ids": sorted(admitted_ids),
        "execution_receipt_root": execution_root,
        "global_state": "HOLD",
    }
    next_state_digest = _address("kc144.p36.next-state", next_state_body)
    successor_body = {
        "schema": "KC144.P36.ContinuationSeed.V1",
        "state_parent": P35_STATE_PARENT,
        "runtime_parent": P31_RESULT_ID,
        "heart_parent": HEART_PARENT,
        "epoch_id": epoch_id,
        "next_state_digest": next_state_digest,
        "open_residuals": sorted(residuals),
        "return_target": P36_RETURN_ADDRESS,
        "resume_rule": (
            "BIND_EXACT_P35_SUBSCRIPTIONS_AND_TRUSTED_SIGNERS_THEN_"
            "REPLAY_FIRST_GENUINE_CONSENTED_EVENT"
        ),
    }
    successor_seed = {
        **successor_body,
        "seed_id": _address("kc144.p36.successor-seed", successor_body),
    }
    delta_body = {
        "schema": "KC144.P36.SealedDelta.V1",
        "status": (
            "ABORTED_HOLD"
            if not all_lanes_verify or replay_failure or execution_failure
            else "NOOP_HOLD"
            if not admitted
            else "SEALED_HOLD"
        ),
        "epoch_id": epoch_id,
        "cutoff": cutoff,
        "base_snapshot_digest": base_state_digest,
        "next_state_digest": next_state_digest,
        "state_parent": P35_STATE_PARENT,
        "runtime_parent": P31_RESULT_ID,
        "heart_parent": HEART_PARENT,
        "subscription_registry_digest": subscription_registry.get(
            "registry_digest"
        ),
        "admitted_event_ids": sorted(admitted_ids),
        "lane_receipt_ids": [row["receipt_id"] for row in lane_receipts],
        "execution_receipt_root": execution_root,
        "changed_fronts": sorted(
            {front for match in matches for front in match["front_ids"]}
        ),
        "deferred_actions": deferred_actions,
        "coverage": coverage,
        "production_events_observed": production_events,
        "real_outcome_events": len(real_outcomes),
        "independent_witness_count": 0,
        "truth_credit_assigned": 0,
        "production_mutated": False,
        "governance_authority_granted": False,
        "content_transport_certified": False,
        "production_certificate_issued": False,
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "NONE",
        "global_state": "HOLD",
        "residuals": sorted(residuals),
        "return_target": P36_RETURN_ADDRESS,
        "successor_seed": successor_seed,
    }
    delta = {
        **delta_body,
        "delta_id": _address("kc144.p36.delta", delta_body),
    }
    envelope_body = {
        "schema": "KC144.P36.Macrocycle.V1",
        "lookup_key": P36_LOOKUP_KEY,
        "contract_digest": p36_contract()["contract_digest"],
        "epoch": epoch_body,
        "epoch_id": epoch_id,
        "lane_receipts": lane_receipts,
        "lane_verifications": lane_verifications,
        "delta": delta,
        "return_receipt": {
            "entry": P36_ENTRY_ADDRESS,
            "nexus": P36_NEXUS_ADDRESS,
            "evidence_ledger": P36_EVIDENCE_ADDRESS,
            "route_ledger": P36_ROUTE_LEDGER,
            "return": P36_RETURN_ADDRESS,
            "heart_parent": HEART_PARENT,
            "delta_id": delta["delta_id"],
            "status": "RETURNED_HOLD",
        },
        "boundary": {
            "connector_reads": 0,
            "private_source_material_persisted": False,
            "production_truth_effect": "NONE",
            "governance_authority_granted": False,
            "production_authority": "HOLD",
        },
    }
    return {
        **envelope_body,
        "envelope_digest": _address("kc144.p36.macrocycle", envelope_body),
    }


def verify_p36_cycle(
    envelope: Mapping[str, Any],
    *,
    public_keys: Mapping[str, Ed25519PublicKey] | None = None,
) -> dict[str, Any]:
    errors: set[str] = set()
    if envelope.get("schema") != "KC144.P36.Macrocycle.V1":
        errors.add("E_SCHEMA")
    if _body_address(
        "kc144.p36.macrocycle",
        envelope,
        "envelope_digest",
    ) != envelope.get("envelope_digest"):
        errors.add("E_ENVELOPE_DIGEST")
    delta = envelope.get("delta", {})
    if not isinstance(delta, Mapping) or _body_address(
        "kc144.p36.delta",
        delta,
        "delta_id",
    ) != delta.get("delta_id"):
        errors.add("E_DELTA_DIGEST")
    lane_verifications = [
        verify_lane_receipt(receipt, public_keys=public_keys or {})
        for receipt in envelope.get("lane_receipts", [])
    ]
    if len(lane_verifications) != 5:
        errors.add("E_LANE_CENSUS")
    if any(row["verdict"] != "PASS" for row in lane_verifications):
        errors.add("E_LANE_RECEIPT")
    if isinstance(delta, Mapping):
        coverage = delta.get("coverage", {})
        if not coverage.get("all_and_only_affected"):
            errors.add("E_AFFECTED_FRONT_COVERAGE")
        if coverage.get("unexpected_execution_count") != 0:
            errors.add("E_UNEXPECTED_EXECUTION")
        if coverage.get("missing_resolution_count") != 0:
            errors.add("E_MISSING_RESOLUTION")
        if delta.get("global_state") != "HOLD":
            errors.add("E_AUTHORITY_ESCALATION")
        errors.update(_protected_effect_errors(delta))
        if delta.get("return_target") != P36_RETURN_ADDRESS:
            errors.add("E_RETURN")
    return {
        "schema": "KC144.P36.Verification.V1",
        "envelope_digest": envelope.get("envelope_digest"),
        "delta_id": delta.get("delta_id") if isinstance(delta, Mapping) else None,
        "lane_verifications": lane_verifications,
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(errors),
        "production_authority": "HOLD",
        "truth_effect": "NONE",
    }


def public_projection(envelope: Mapping[str, Any]) -> dict[str, Any]:
    delta = envelope["delta"]
    projection = {
        "schema": "KC144.P36.PublicProjection.V1",
        "lookup_key": envelope["lookup_key"],
        "envelope_digest": envelope["envelope_digest"],
        "delta_id": delta["delta_id"],
        "status": delta["status"],
        "state_parent": delta["state_parent"],
        "runtime_parent": delta["runtime_parent"],
        "heart_parent": delta["heart_parent"],
        "subscription_registry_digest": delta["subscription_registry_digest"],
        "event_counts": {
            "admitted": delta["coverage"]["admitted_event_count"],
            "production": delta["production_events_observed"],
            "real_outcome": delta["real_outcome_events"],
        },
        "affected_counts": {
            key: delta["coverage"][key]
            for key in (
                "matched_subscription_count",
                "affected_action_count",
                "affected_front_count",
                "executed_action_count",
                "deferred_action_count",
                "unexpected_execution_count",
                "missing_resolution_count",
            )
        },
        "residuals": delta["residuals"],
        "return_target": delta["return_target"],
        "global_state": delta["global_state"],
        "truth_effect": "NONE",
        "private_source_material_included": False,
    }
    if _contains_private_field(projection):
        raise P36RuntimeError("private field entered public projection")
    return {
        **projection,
        "projection_digest": _address("kc144.p36.public-projection", projection),
    }


def p36_tool_registry() -> dict[str, Any]:
    descriptors = {
        "KC144.P31::EXACT_RUNTIME_ADAPTER": {
            "schema": "KC144.MyceliumToolDescriptor.V3",
            "lookup_key": "KC144.P31::EXACT_RUNTIME_ADAPTER",
            "tool_uri": "tool://kc144/p31.exact-adapter",
            "parent_lookup_key": "KC144.P31::LIVE_COGNITION_NAVIGATE",
            "execution_binding": "CALLER_SUPPLIED_EXACT_ARCHIVE_PROVIDER",
            "handler_id": "kc144.p31-exact-adapter.v1",
            "operations": ["status", "navigate"],
            "runtime_binding": {
                "release_id": P31_RELEASE_ID,
                "result_id": P31_RESULT_ID,
                "archive_sha256": "sha256:" + P31_ARCHIVE_SHA256,
            },
        },
        P36_LOOKUP_KEY: {
            "schema": "KC144.MyceliumToolDescriptor.V3",
            "lookup_key": P36_LOOKUP_KEY,
            "tool_uri": "tool://kc144/p36.macrocycle",
            "parent_lookup_key": "KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH",
            "execution_binding": "CALLER_SUPPLIED_FROZEN_INPUTS",
            "handler_id": "kc144.p36-macrocycle.v1",
            "operations": ["contract", "cycle", "verify", "public-project"],
            "effect_policy": "READ_ONLY_OR_EXPLICITLY_AUTHORIZED_LOCAL_REVERSIBLE",
        },
    }
    sealed = {}
    for key, descriptor in descriptors.items():
        sealed[key] = {
            **descriptor,
            "descriptor_digest": _address(
                "kc144.p36.tool-descriptor", descriptor
            ),
        }
    body = {
        "schema": "KC144.P36.ToolRegistry.V1",
        "parent_registry_lookup_key": "KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH",
        "descriptors": sealed,
        "production_authority": "HOLD",
        "truth_effect": "NONE",
    }
    return {
        **body,
        "registry_digest": _address("kc144.p36.tool-registry", body),
    }


def compile_p36_release(
    output_directory: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-f]{40}", implementation_commit):
        raise P36RuntimeError("implementation_commit must be a Git SHA")
    if not re.fullmatch(r"[0-9a-f]{40}", implementation_tree):
        raise P36RuntimeError("implementation_tree must be a Git tree SHA")
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    base_state_digest = _address(
        "kc144.p35.source-declared-state",
        {
            "state_parent": P35_STATE_PARENT,
            "standing": "SOURCE_DECLARED_NOT_ARCHIVE_BOUND",
        },
    )
    registry = unbound_p35_subscription_registry()
    cycle = compile_p36_cycle(
        events=[],
        subscription_registry=registry,
        base_state_digest=base_state_digest,
        cutoff="2026-07-28T00:00:00.000000Z",
    )
    verification = verify_p36_cycle(cycle)
    projection = public_projection(cycle)
    contract = p36_contract()
    tools = p36_tool_registry()
    release_core = {
        "schema": "KC144.P36.Release.V1",
        "release_id": "KC144_P36_EVENT_RUNTIME_CANDIDATE_V1",
        "status": "CANDIDATE_HOLD",
        "implementation": {
            "repository": "demeet2k/guild-hall",
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "lineage": contract["lineage"],
        "contract_digest": contract["contract_digest"],
        "tool_registry_digest": tools["registry_digest"],
        "subscription_registry_digest": registry["registry_digest"],
        "envelope_digest": cycle["envelope_digest"],
        "delta_id": cycle["delta"]["delta_id"],
        "verification_verdict": verification["verdict"],
        "public_projection_digest": projection["projection_digest"],
        "production_authority": "HOLD",
        "truth_effect": "NONE",
        "next_seed": (
            "KC144.V3.8::MATH144.P37::EXACT_P35_SUBSCRIPTION_REGISTRY_"
            "BINDING_TRUSTED_SIGNER_ENROLLMENT_AND_FIRST_GENUINE_"
            "CONSENTED_EVENT_REPLAY_MACROCYCLE_06"
        ),
    }
    release_digest = _address("kc144.p36.release", release_core)
    release = {
        **release_core,
        "release_digest": release_digest,
        "result_id": "KC144.P36.CANDIDATE::"
        + release_digest.removeprefix("sha256:")[:24],
    }
    artifacts = {
        "p36_contract_v1.json": contract,
        "p36_tool_registry_v1.json": tools,
        "p35_subscription_registry_unbound_v1.json": registry,
        "p36_noop_cycle_v1.json": cycle,
        "p36_verification_v1.json": verification,
        "p36_public_projection_v1.json": projection,
        "p36_release_v1.json": release,
    }
    for name, value in artifacts.items():
        (output / name).write_text(
            json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    checksum_lines = []
    for path in sorted(output.glob("*.json")):
        checksum = __import__("hashlib").sha256(path.read_bytes()).hexdigest()
        checksum_lines.append(f"{checksum}  {path.name}")
    (output / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n",
        encoding="utf-8",
    )
    return release
