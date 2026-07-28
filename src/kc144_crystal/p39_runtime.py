from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from collections import Counter
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


P39_LOOKUP_KEY = (
    "KC144.V4.0::MATH144.P39::LIVE_OUTCOME_CORPUS_INDEPENDENT_IC10_"
    "CONVERGENCE_WEIGHT_CALIBRATION_AND_CANONICAL_SUCCESSOR_DECISION_"
    "MACROCYCLE_08"
)
P39_NEXT_SEED = (
    "KC144.V4.1::MATH144.P40::AUTHORIZED_SUCCESSOR_ACTIVATION_CANONICAL_"
    "WEIGHT_COMMIT_AND_POST_ACTIVATION_OUTCOME_WATCH_MACROCYCLE_09"
)
P39_ROUTE = (
    "KC144.V1::GID135::M03",
    "KC144.V1::GID047::F04",
    "KC144.V1::GID141::M09",
    "KC144.V1::GID003::H03",
    "KC144.V1::GID144::M12",
)
P39_LANES = (
    "LIVE_OUTCOME_INTAKE",
    "PARTITION_LEAKAGE_BARRIER",
    "DETERMINISTIC_WEIGHT_CALIBRATION",
    "FIXED_FIVE_SEAT_IC10_REGISTRY",
    "THREE_OF_FIVE_INDEPENDENT_CONVERGENCE",
    "CANONICAL_SUCCESSOR_DECISION",
    "M12_RETURN",
)
P38_RESULT_ID = "KC144.P38.CANDIDATE::903b28c3df75072423c72959"
P38_RELEASE_DIGEST = (
    "sha256:903b28c3df75072423c72959a03860ef0d636f6a189b302f4281ca36944963d8"
)
P39_CUTOFF = "2026-07-29T23:59:59.000000Z"
P39_REQUIRED_CALIBRATION = 12
P39_REQUIRED_HELD_OUT = 12
P39_REQUIRED_SURFACES = 3
P39_REQUIRED_ROUTES = 3
P39_REGISTRY_SEATS = 5
P39_THRESHOLD = 3
P39_IC10_GATES = tuple(f"I{index:02d}" for index in range(1, 11))

DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
OUTCOME_CLASSES = frozenset({"TASK_OUTCOME", "EMPIRICAL_RESULT"})
ORIGIN_CLASSES = frozenset({"PRODUCTION", "USER_OBSERVED", "CONNECTOR_OBSERVED"})
PARTITIONS = frozenset({"CALIBRATION", "HELD_OUT"})


class P39RuntimeError(ValueError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _require_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise P39RuntimeError(f"{label} must be a lowercase SHA-256 address")
    return value


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


def _public_key_bytes(public_key: Ed25519PublicKey) -> bytes:
    return public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def _key_id(public_key: Ed25519PublicKey) -> str:
    return _sha256_bytes(_public_key_bytes(public_key))


def p39_policy() -> dict[str, Any]:
    body = {
        "schema": "KC144.P39.CalibrationPolicy.V1",
        "partition_law": {
            "calibration": "MAY_PROPOSE_WEIGHTS",
            "held_out": "MAY_EVALUATE_PROPOSAL_ONLY",
            "cross_partition_evidence_unit": "FATAL_LEAKAGE",
            "route_generated_observations": "REJECT",
        },
        "minimums": {
            "calibration_observations": P39_REQUIRED_CALIBRATION,
            "held_out_observations": P39_REQUIRED_HELD_OUT,
            "source_surfaces_per_partition": P39_REQUIRED_SURFACES,
            "routes_per_partition": P39_REQUIRED_ROUTES,
            "observations_per_route_per_partition": 3,
        },
        "estimator": {
            "metric": "success",
            "value_range": [0.0, 1.0],
            "route_probability": "LAPLACE_BERNOULLI_(SUM_PLUS_1)/(N_PLUS_2)",
            "weight_normalization": "DIVIDE_BY_SUM_ROUTE_PROBABILITIES",
            "precision_decimals": 12,
        },
        "held_out_gate": {
            "score": "BRIER_MEAN",
            "baseline_probability": 0.5,
            "law": "PROPOSED_BRIER_MUST_NOT_EXCEED_BASELINE_BRIER",
        },
        "ic10": {
            "registry_seats": P39_REGISTRY_SEATS,
            "threshold": P39_THRESHOLD,
            "distinct_signer_ids": P39_THRESHOLD,
            "distinct_organizations": P39_THRESHOLD,
            "distinct_control_roots": P39_THRESHOLD,
            "all_ten_gates": "PASS",
        },
        "ceilings": {
            "canonical_weight_mutation": False,
            "canonical_graph_mutation": False,
            "production_mutation": False,
            "truth_effect": "NONE",
            "evidence_effect": "NONE",
            "enrollment_authority": "NONE",
        },
    }
    return {**body, "policy_digest": content_address("kc144.p39.policy", body)}


def p39_contract() -> dict[str, Any]:
    policy = p39_policy()
    body = {
        "schema": "KC144.P39.Contract.V1",
        "lookup_key": P39_LOOKUP_KEY,
        "parent_result_id": P38_RESULT_ID,
        "parent_release_digest": P38_RELEASE_DIGEST,
        "route": list(P39_ROUTE),
        "lanes": [
            {
                "lane_id": f"P39.L{index:02d}",
                "lane": lane,
                "parallel_group": 1 if index <= 3 else 2 if index <= 5 else 3,
                "return": P39_ROUTE[-1],
            }
            for index, lane in enumerate(P39_LANES, 1)
        ],
        "policy_digest": policy["policy_digest"],
        "merge_law": (
            "VERIFY_ALL_SEVEN_LANES_AND_EXACT_ROOT_BINDINGS_THEN_REDUCE_"
            "IN_CANONICAL_LANE_ORDER"
        ),
        "noncollapse": [
            "CONTENT_ADDRESS_IS_NOT_EMPIRICAL_VALIDITY",
            "SIGNATURE_VALIDITY_IS_NOT_SOURCE_TRUTH",
            "CALIBRATION_DATA_IS_NOT_HELD_OUT_DATA",
            "PROPOSED_WEIGHT_IS_NOT_CANONICAL_WEIGHT",
            "SIGNER_ENROLLMENT_IS_NOT_AUTHORITY",
            "THREE_SIGNATURES_ARE_NOT_INDEPENDENT_WITHOUT_THREE_CONTROL_ROOTS",
            "IC10_CONVERGENCE_IS_NOT_PRODUCTION_MUTATION",
            "SUCCESSOR_READY_IS_NOT_SUCCESSOR_ACTIVATED",
            "PUBLICATION_IS_NOT_TRUTH_PROMOTION",
        ],
        "default_state": "HOLD_UNTIL_LIVE_OUTCOMES_AND_INDEPENDENT_RETURNS_EXIST",
        "next_seed": P39_NEXT_SEED,
    }
    return {**body, "contract_digest": content_address("kc144.p39.contract", body)}


def build_live_outcome(
    *,
    outcome_class: str,
    origin_class: str,
    observed_at: str,
    source_surface: str,
    source_commitment: str,
    evidence_unit: str,
    route_id: str,
    partition: str,
    value: float,
    observer_id: str,
    private_key: Ed25519PrivateKey,
) -> dict[str, Any]:
    if outcome_class not in OUTCOME_CLASSES:
        raise P39RuntimeError("unknown outcome class")
    if origin_class not in ORIGIN_CLASSES:
        raise P39RuntimeError("origin must be independently observable")
    if partition not in PARTITIONS:
        raise P39RuntimeError("partition must be CALIBRATION or HELD_OUT")
    if not RFC3339_RE.fullmatch(observed_at):
        raise P39RuntimeError("observed_at must be fixed-precision UTC RFC3339")
    _require_digest(source_commitment, "source commitment")
    _require_digest(evidence_unit, "evidence unit")
    if (
        not source_surface
        or not route_id
        or not observer_id
        or isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not 0.0 <= float(value) <= 1.0
    ):
        raise P39RuntimeError("live outcome identity and [0,1] value are required")
    public_key = private_key.public_key()
    body = {
        "schema": "KC144.P39.LiveOutcomeObservation.V1",
        "outcome_class": outcome_class,
        "origin_class": origin_class,
        "observed_at": observed_at,
        "source_surface": source_surface,
        "source_commitment": source_commitment,
        "evidence_unit": evidence_unit,
        "route_id": route_id,
        "partition": partition,
        "metric": "success",
        "value": float(value),
        "observer_id": observer_id,
        "observer_key_id": _key_id(public_key),
        "observer_public_key": _encode(_public_key_bytes(public_key)),
        "consent_scope": ["OUTCOME_CALIBRATION", "CURRENT_TASK_EXECUTION"],
        "source_verified": True,
        "route_generated": False,
        "test_only": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    observation_id = content_address("kc144.p39.live-outcome", body)
    signed_body = {**body, "observation_id": observation_id}
    signature = private_key.sign(
        b"KC144.P39.LIVE-OUTCOME.V1\0" + canonical_bytes(signed_body)
    )
    return {
        **signed_body,
        "signature": {
            "algorithm": "Ed25519",
            "domain": "KC144.P39.LIVE-OUTCOME.V1",
            "value": _encode(signature),
        },
    }


def _verify_observation(
    observation: Mapping[str, Any],
    *,
    cutoff: str,
) -> list[str]:
    errors: list[str] = []
    body = {
        key: item
        for key, item in observation.items()
        if key not in {"observation_id", "signature"}
    }
    if observation.get("schema") != "KC144.P39.LiveOutcomeObservation.V1":
        errors.append("E_SCHEMA")
    if observation.get("observation_id") != content_address(
        "kc144.p39.live-outcome", body
    ):
        errors.append("E_OBSERVATION_DIGEST")
    if observation.get("outcome_class") not in OUTCOME_CLASSES:
        errors.append("E_OUTCOME_CLASS")
    if observation.get("origin_class") not in ORIGIN_CLASSES:
        errors.append("E_ORIGIN")
    if observation.get("partition") not in PARTITIONS:
        errors.append("E_PARTITION")
    if observation.get("metric") != "success":
        errors.append("E_METRIC")
    value = observation.get("value")
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
        or not 0.0 <= float(value) <= 1.0
    ):
        errors.append("E_VALUE")
    for field in ("source_commitment", "evidence_unit", "observer_key_id"):
        if not DIGEST_RE.fullmatch(str(observation.get(field, ""))):
            errors.append(f"E_{field.upper()}")
    if (
        not observation.get("source_surface")
        or not observation.get("route_id")
        or not observation.get("observer_id")
    ):
        errors.append("E_IDENTITY")
    observed_at = observation.get("observed_at")
    if (
        not isinstance(observed_at, str)
        or not RFC3339_RE.fullmatch(observed_at)
        or observed_at > cutoff
    ):
        errors.append("E_TIME")
    if set(observation.get("consent_scope", [])) < {
        "OUTCOME_CALIBRATION",
        "CURRENT_TASK_EXECUTION",
    }:
        errors.append("E_CONSENT")
    if observation.get("source_verified") is not True:
        errors.append("E_SOURCE_UNVERIFIED")
    if observation.get("route_generated") is not False:
        errors.append("E_ROUTE_GENERATED")
    if observation.get("test_only") is not False:
        errors.append("E_TEST_ONLY")
    if (
        observation.get("truth_effect") != "NONE"
        or observation.get("authority_effect") != "NONE"
    ):
        errors.append("E_EFFECT_ESCALATION")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            _decode(str(observation.get("observer_public_key", "")))
        )
        if _key_id(public_key) != observation.get("observer_key_id"):
            errors.append("E_OBSERVER_KEY_ID")
        signature = observation.get("signature", {})
        if (
            not isinstance(signature, Mapping)
            or signature.get("algorithm") != "Ed25519"
            or signature.get("domain") != "KC144.P39.LIVE-OUTCOME.V1"
        ):
            raise ValueError("invalid signature envelope")
        signed_body = {**body, "observation_id": observation.get("observation_id")}
        public_key.verify(
            _decode(str(signature.get("value", ""))),
            b"KC144.P39.LIVE-OUTCOME.V1\0" + canonical_bytes(signed_body),
        )
    except (ValueError, InvalidSignature):
        errors.append("E_SIGNATURE")
    return sorted(set(errors))


def compile_live_outcome_corpus(
    observations: Sequence[Mapping[str, Any]],
    *,
    cutoff: str = P39_CUTOFF,
) -> dict[str, Any]:
    if not RFC3339_RE.fullmatch(cutoff):
        raise P39RuntimeError("cutoff must be fixed-precision UTC RFC3339")
    ordered = sorted(
        (dict(item) for item in observations),
        key=lambda row: str(row.get("observation_id", "")),
    )
    ids = Counter(str(row.get("observation_id", "")) for row in ordered)
    unit_counts = Counter(str(row.get("evidence_unit", "")) for row in ordered)
    units: dict[str, set[str]] = {}
    for row in ordered:
        units.setdefault(str(row.get("evidence_unit", "")), set()).add(
            str(row.get("partition", ""))
        )
    leaking_units = sorted(
        unit
        for unit, partitions in units.items()
        if unit and {"CALIBRATION", "HELD_OUT"} <= partitions
    )
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    for row in ordered:
        errors = _verify_observation(row, cutoff=cutoff)
        observation_id = str(row.get("observation_id", ""))
        if ids[observation_id] > 1:
            errors.append("E_DUPLICATE_OBSERVATION")
        if unit_counts[str(row.get("evidence_unit", ""))] > 1:
            errors.append("E_DUPLICATE_EVIDENCE_UNIT")
        if row.get("evidence_unit") in leaking_units:
            errors.append("E_CROSS_PARTITION_LEAKAGE")
        receipt = {
            "observation_id": observation_id,
            "partition": row.get("partition"),
            "evidence_unit": row.get("evidence_unit"),
            "status": "ADMITTED" if not errors else "REJECTED",
            "errors": sorted(set(errors)),
        }
        if errors:
            rejected.append(receipt)
        else:
            accepted.append(row)
    partition_stats: dict[str, dict[str, Any]] = {}
    for partition in ("CALIBRATION", "HELD_OUT"):
        rows = [row for row in accepted if row["partition"] == partition]
        by_route = Counter(str(row["route_id"]) for row in rows)
        partition_stats[partition.lower()] = {
            "observations": len(rows),
            "source_surfaces": len({str(row["source_surface"]) for row in rows}),
            "routes": len(by_route),
            "observations_by_route": dict(sorted(by_route.items())),
            "all_routes_have_three": bool(by_route)
            and all(count >= 3 for count in by_route.values()),
        }
    calibration = partition_stats["calibration"]
    held_out = partition_stats["held_out"]
    ready = (
        not leaking_units
        and calibration["observations"] >= P39_REQUIRED_CALIBRATION
        and held_out["observations"] >= P39_REQUIRED_HELD_OUT
        and calibration["source_surfaces"] >= P39_REQUIRED_SURFACES
        and held_out["source_surfaces"] >= P39_REQUIRED_SURFACES
        and calibration["routes"] >= P39_REQUIRED_ROUTES
        and held_out["routes"] >= P39_REQUIRED_ROUTES
        and calibration["all_routes_have_three"]
        and held_out["all_routes_have_three"]
        and set(calibration["observations_by_route"])
        == set(held_out["observations_by_route"])
    )
    accepted_projection = [
        {
            "observation_id": row["observation_id"],
            "partition": row["partition"],
            "source_surface": row["source_surface"],
            "source_commitment": row["source_commitment"],
            "evidence_unit": row["evidence_unit"],
            "route_id": row["route_id"],
            "metric": row["metric"],
            "value": row["value"],
            "observer_key_id": row["observer_key_id"],
        }
        for row in accepted
    ]
    body = {
        "schema": "KC144.P39.LiveOutcomeCorpus.V1",
        "cutoff": cutoff,
        "observations": ordered,
        "accepted": accepted_projection,
        "rejected": rejected,
        "leaking_evidence_units": leaking_units,
        "census": {
            "supplied": len(ordered),
            "accepted": len(accepted),
            "rejected": len(rejected),
            "partitions": partition_stats,
        },
        "status": "CORPUS_READY" if ready else "CORPUS_HOLD",
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "corpus_root": content_address("kc144.p39.live-outcome-corpus", body),
    }


def calibrate_weights(corpus: Mapping[str, Any]) -> dict[str, Any]:
    policy = p39_policy()
    calibration_rows = [
        row
        for row in corpus.get("accepted", [])
        if row.get("partition") == "CALIBRATION"
    ]
    held_out_rows = [
        row for row in corpus.get("accepted", []) if row.get("partition") == "HELD_OUT"
    ]
    routes = sorted({str(row.get("route_id")) for row in calibration_rows})
    proposals: list[dict[str, Any]] = []
    probabilities: dict[str, float] = {}
    if corpus.get("status") == "CORPUS_READY":
        for route in routes:
            rows = [row for row in calibration_rows if row["route_id"] == route]
            probability = (sum(float(row["value"]) for row in rows) + 1.0) / (
                len(rows) + 2.0
            )
            probabilities[route] = probability
        denominator = sum(probabilities.values())
        for route in routes:
            proposals.append(
                {
                    "route_id": route,
                    "calibration_observations": sum(
                        row["route_id"] == route for row in calibration_rows
                    ),
                    "laplace_success_probability": round(
                        probabilities[route], 12
                    ),
                    "proposed_normalized_weight": round(
                        probabilities[route] / denominator, 12
                    ),
                }
            )
    proposed_brier = None
    baseline_brier = None
    held_out_gate = False
    if proposals and held_out_rows:
        proposed_brier = round(
            sum(
                (
                    probabilities[str(row["route_id"])]
                    - float(row["value"])
                )
                ** 2
                for row in held_out_rows
            )
            / len(held_out_rows),
            12,
        )
        baseline_brier = round(
            sum((0.5 - float(row["value"])) ** 2 for row in held_out_rows)
            / len(held_out_rows),
            12,
        )
        held_out_gate = proposed_brier <= baseline_brier
    ready = corpus.get("status") == "CORPUS_READY" and held_out_gate
    body = {
        "schema": "KC144.P39.WeightCalibration.V1",
        "corpus_root": corpus.get("corpus_root"),
        "policy_digest": policy["policy_digest"],
        "proposed_weights": proposals,
        "held_out_evaluation": {
            "observations": len(held_out_rows),
            "proposed_brier": proposed_brier,
            "baseline_brier": baseline_brier,
            "non_degradation_gate": "PASS" if held_out_gate else "HOLD",
        },
        "status": "CALIBRATION_READY" if ready else "CALIBRATION_HOLD",
        "canonical_weights_before": "UNCHANGED",
        "canonical_weight_updates_executed": 0,
        "production_mutated": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "calibration_digest": content_address("kc144.p39.weight-calibration", body),
    }


def empty_ic10_registry() -> dict[str, Any]:
    body = {
        "schema": "KC144.P39.IC10Registry.V1",
        "capacity": P39_REGISTRY_SEATS,
        "threshold": P39_THRESHOLD,
        "entries": [],
        "authority_granted_by_enrollment": False,
    }
    return {
        **body,
        "registry_digest": content_address("kc144.p39.ic10-registry", body),
    }


def build_ic10_enrollment(
    *,
    signer_id: str,
    organization_id: str,
    control_root: str,
    public_key: Ed25519PublicKey,
    valid_from: str,
    valid_until: str,
) -> dict[str, Any]:
    _require_digest(control_root, "control root")
    if (
        not signer_id
        or not organization_id
        or not RFC3339_RE.fullmatch(valid_from)
        or not RFC3339_RE.fullmatch(valid_until)
        or valid_from >= valid_until
    ):
        raise P39RuntimeError(
            "signer, organization, and validity interval are required"
        )
    body = {
        "schema": "KC144.P39.IC10Enrollment.V1",
        "signer_id": signer_id,
        "organization_id": organization_id,
        "control_root": control_root,
        "key_id": _key_id(public_key),
        "public_key": _encode(_public_key_bytes(public_key)),
        "algorithm": "Ed25519",
        "purpose": "P39_CANONICAL_SUCCESSOR_DECISION",
        "scope": [P39_LOOKUP_KEY],
        "independence_class": "EXTERNAL_INDEPENDENT",
        "valid_from": valid_from,
        "valid_until": valid_until,
        "authority_granted": False,
    }
    return {
        **body,
        "enrollment_digest": content_address("kc144.p39.ic10-enrollment", body),
    }


def enroll_ic10_signer(
    registry: Mapping[str, Any],
    enrollment: Mapping[str, Any],
    proof_of_possession: str,
) -> dict[str, Any]:
    verification = verify_ic10_registry(registry, allow_incomplete=True)
    if verification["verdict"] != "PASS":
        raise P39RuntimeError("input IC10 registry is invalid")
    entries = list(registry.get("entries", []))
    if len(entries) >= P39_REGISTRY_SEATS:
        raise P39RuntimeError("fixed five-seat IC10 registry is full")
    body = {
        key: item
        for key, item in enrollment.items()
        if key != "enrollment_digest"
    }
    errors: list[str] = []
    if enrollment.get("schema") != "KC144.P39.IC10Enrollment.V1":
        errors.append("E_SCHEMA")
    if enrollment.get("enrollment_digest") != content_address(
        "kc144.p39.ic10-enrollment", body
    ):
        errors.append("E_ENROLLMENT_DIGEST")
    if (
        enrollment.get("purpose") != "P39_CANONICAL_SUCCESSOR_DECISION"
        or enrollment.get("independence_class") != "EXTERNAL_INDEPENDENT"
        or enrollment.get("scope") != [P39_LOOKUP_KEY]
        or enrollment.get("authority_granted") is not False
    ):
        errors.append("E_SCOPE")
    try:
        public_key = Ed25519PublicKey.from_public_bytes(
            _decode(str(enrollment.get("public_key", "")))
        )
        if _key_id(public_key) != enrollment.get("key_id"):
            errors.append("E_KEY_ID")
        public_key.verify(
            _decode(proof_of_possession),
            b"KC144.P39.IC10-ENROLLMENT.V1\0" + canonical_bytes(enrollment),
        )
    except (ValueError, InvalidSignature):
        errors.append("E_PROOF_OF_POSSESSION")
    duplicate_fields = ("signer_id", "organization_id", "control_root", "key_id")
    if any(
        any(entry.get(field) == enrollment.get(field) for field in duplicate_fields)
        for entry in entries
    ):
        errors.append("E_INDEPENDENCE_COLLISION")
    if errors:
        raise P39RuntimeError("IC10 enrollment failed: " + ", ".join(sorted(errors)))
    entry_body = {
        **body,
        "enrollment_digest": enrollment["enrollment_digest"],
        "proof_of_possession": proof_of_possession,
        "revoked": False,
        "authority_granted": False,
    }
    entry = {
        **entry_body,
        "entry_digest": content_address("kc144.p39.ic10-entry", entry_body),
    }
    entries.append(entry)
    entries.sort(key=lambda row: str(row["key_id"]))
    result_body = {
        "schema": "KC144.P39.IC10Registry.V1",
        "capacity": P39_REGISTRY_SEATS,
        "threshold": P39_THRESHOLD,
        "entries": entries,
        "authority_granted_by_enrollment": False,
    }
    return {
        **result_body,
        "registry_digest": content_address("kc144.p39.ic10-registry", result_body),
    }


def verify_ic10_registry(
    registry: Mapping[str, Any],
    *,
    allow_incomplete: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: item for key, item in registry.items() if key != "registry_digest"}
    if registry.get("schema") != "KC144.P39.IC10Registry.V1":
        errors.append("E_SCHEMA")
    if registry.get("registry_digest") != content_address(
        "kc144.p39.ic10-registry", body
    ):
        errors.append("E_REGISTRY_DIGEST")
    if (
        registry.get("capacity") != P39_REGISTRY_SEATS
        or registry.get("threshold") != P39_THRESHOLD
        or registry.get("authority_granted_by_enrollment") is not False
    ):
        errors.append("E_REGISTRY_POLICY")
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        entries = []
        errors.append("E_ENTRIES")
    if len(entries) > P39_REGISTRY_SEATS or (
        not allow_incomplete and len(entries) != P39_REGISTRY_SEATS
    ):
        errors.append("E_SEAT_CENSUS")
    identities: dict[str, list[str]] = {
        field: []
        for field in ("signer_id", "organization_id", "control_root", "key_id")
    }
    for entry in entries:
        if not isinstance(entry, Mapping):
            errors.append("E_ENTRY")
            continue
        entry_body = {
            key: item for key, item in entry.items() if key != "entry_digest"
        }
        if entry.get("entry_digest") != content_address(
            "kc144.p39.ic10-entry", entry_body
        ):
            errors.append("E_ENTRY_DIGEST")
        for field in identities:
            identities[field].append(str(entry.get(field, "")))
        if (
            entry.get("purpose") != "P39_CANONICAL_SUCCESSOR_DECISION"
            or entry.get("independence_class") != "EXTERNAL_INDEPENDENT"
            or entry.get("scope") != [P39_LOOKUP_KEY]
            or entry.get("authority_granted") is not False
            or entry.get("revoked") is not False
        ):
            errors.append("E_ENTRY_SCOPE")
        enrollment = {
            key: item
            for key, item in entry.items()
            if key
            not in {
                "entry_digest",
                "proof_of_possession",
                "revoked",
            }
        }
        if enrollment.get("enrollment_digest") != content_address(
            "kc144.p39.ic10-enrollment",
            {
                key: item
                for key, item in enrollment.items()
                if key != "enrollment_digest"
            },
        ):
            errors.append("E_ENROLLMENT_DIGEST")
        try:
            public_key = Ed25519PublicKey.from_public_bytes(
                _decode(str(entry.get("public_key", "")))
            )
            if _key_id(public_key) != entry.get("key_id"):
                errors.append("E_KEY_ID")
            public_key.verify(
                _decode(str(entry.get("proof_of_possession", ""))),
                b"KC144.P39.IC10-ENROLLMENT.V1\0" + canonical_bytes(enrollment),
            )
        except (ValueError, InvalidSignature):
            errors.append("E_PROOF_OF_POSSESSION")
    if any(len(values) != len(set(values)) for values in identities.values()):
        errors.append("E_INDEPENDENCE_COLLISION")
    return {
        "schema": "KC144.P39.IC10RegistryVerification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "enrolled_seats": len(entries),
        "required_seats": P39_REGISTRY_SEATS,
    }


def build_ic10_convergence_return(
    *,
    candidate_root: str,
    corpus_root: str,
    calibration_digest: str,
    policy_digest: str,
    signer_id: str,
    organization_id: str,
    control_root: str,
    private_key: Ed25519PrivateKey,
    issued_at: str,
    expires_at: str,
    nonce: str,
    decision: str = "AUTHORIZE_CANONICAL_SUCCESSOR",
) -> dict[str, Any]:
    for value, label in (
        (candidate_root, "candidate root"),
        (corpus_root, "corpus root"),
        (calibration_digest, "calibration digest"),
        (policy_digest, "policy digest"),
        (control_root, "control root"),
    ):
        _require_digest(value, label)
    if (
        not signer_id
        or not organization_id
        or not nonce
        or not RFC3339_RE.fullmatch(issued_at)
        or not RFC3339_RE.fullmatch(expires_at)
        or issued_at >= expires_at
    ):
        raise P39RuntimeError("return identity, nonce, and validity are required")
    body = {
        "schema": "KC144.P39.IC10ConvergenceReturn.V1",
        "candidate_root": candidate_root,
        "corpus_root": corpus_root,
        "calibration_digest": calibration_digest,
        "policy_digest": policy_digest,
        "signer_id": signer_id,
        "organization_id": organization_id,
        "control_root": control_root,
        "key_id": _key_id(private_key.public_key()),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
        "decision": decision,
        "gates": [{"gate": gate, "status": "PASS"} for gate in P39_IC10_GATES],
        "return_target": P39_ROUTE[-1],
    }
    return_id = content_address("kc144.p39.ic10-return", body)
    signed_body = {**body, "return_id": return_id}
    signature = private_key.sign(
        b"KC144.P39.IC10-CONVERGENCE-RETURN.V1\0"
        + canonical_bytes(signed_body)
    )
    return {
        **signed_body,
        "signature": {
            "algorithm": "Ed25519",
            "domain": "KC144.P39.IC10-CONVERGENCE-RETURN.V1",
            "value": _encode(signature),
        },
    }


def evaluate_ic10_convergence(
    returns: Sequence[Mapping[str, Any]],
    *,
    registry: Mapping[str, Any],
    candidate_root: str,
    corpus_root: str,
    calibration_digest: str,
    policy_digest: str,
    checked_at: str,
) -> dict[str, Any]:
    registry_verification = verify_ic10_registry(registry)
    entries = {
        str(entry.get("key_id")): entry
        for entry in registry.get("entries", [])
        if isinstance(entry, Mapping)
    }
    ordered = sorted(returns, key=lambda row: str(row.get("return_id", "")))
    id_counts = Counter(str(row.get("return_id", "")) for row in ordered)
    nonces: set[tuple[str, str]] = set()
    receipts: list[dict[str, Any]] = []
    for packet in ordered:
        errors: list[str] = []
        body = {
            key: item
            for key, item in packet.items()
            if key not in {"return_id", "signature"}
        }
        if registry_verification["verdict"] != "PASS":
            errors.append("E_REGISTRY")
        if packet.get("schema") != "KC144.P39.IC10ConvergenceReturn.V1":
            errors.append("E_SCHEMA")
        if packet.get("return_id") != content_address(
            "kc144.p39.ic10-return", body
        ):
            errors.append("E_RETURN_DIGEST")
        if id_counts[str(packet.get("return_id", ""))] > 1:
            errors.append("E_DUPLICATE_RETURN")
        bindings = (
            ("candidate_root", candidate_root),
            ("corpus_root", corpus_root),
            ("calibration_digest", calibration_digest),
            ("policy_digest", policy_digest),
        )
        for field, expected in bindings:
            if packet.get(field) != expected:
                errors.append(f"E_{field.upper()}_BINDING")
        if packet.get("decision") != "AUTHORIZE_CANONICAL_SUCCESSOR":
            errors.append("E_DECISION")
        gates = packet.get("gates", [])
        if [row.get("gate") for row in gates] != list(P39_IC10_GATES) or any(
            row.get("status") != "PASS" for row in gates
        ):
            errors.append("E_IC10_GATES")
        key_id = str(packet.get("key_id", ""))
        entry = entries.get(key_id)
        if entry is None:
            errors.append("E_SIGNER_UNENROLLED")
        else:
            for field in ("signer_id", "organization_id", "control_root"):
                if packet.get(field) != entry.get(field):
                    errors.append(f"E_{field.upper()}_BINDING")
            if not (
                str(entry.get("valid_from", "")) <= checked_at
                <= str(entry.get("valid_until", ""))
            ):
                errors.append("E_SIGNER_TIME")
            try:
                public_key = Ed25519PublicKey.from_public_bytes(
                    _decode(str(entry.get("public_key", "")))
                )
                signature = packet.get("signature", {})
                if (
                    not isinstance(signature, Mapping)
                    or signature.get("algorithm") != "Ed25519"
                    or signature.get("domain")
                    != "KC144.P39.IC10-CONVERGENCE-RETURN.V1"
                ):
                    raise ValueError("invalid signature envelope")
                signed_body = {**body, "return_id": packet.get("return_id")}
                public_key.verify(
                    _decode(str(signature.get("value", ""))),
                    b"KC144.P39.IC10-CONVERGENCE-RETURN.V1\0"
                    + canonical_bytes(signed_body),
                )
            except (ValueError, InvalidSignature):
                errors.append("E_SIGNATURE")
        if not (
            str(packet.get("issued_at", "")) <= checked_at
            <= str(packet.get("expires_at", ""))
        ):
            errors.append("E_RETURN_TIME")
        nonce_key = (key_id, str(packet.get("nonce", "")))
        if nonce_key in nonces:
            errors.append("E_NONCE_REPLAY")
        nonces.add(nonce_key)
        receipts.append(
            {
                "return_id": packet.get("return_id"),
                "key_id": key_id,
                "signer_id": packet.get("signer_id"),
                "organization_id": packet.get("organization_id"),
                "control_root": packet.get("control_root"),
                "verdict": "PASS" if not errors else "FAIL",
                "errors": sorted(set(errors)),
            }
        )
    valid = [receipt for receipt in receipts if receipt["verdict"] == "PASS"]
    independence = {
        "signers": len({row["signer_id"] for row in valid}),
        "organizations": len({row["organization_id"] for row in valid}),
        "control_roots": len({row["control_root"] for row in valid}),
        "keys": len({row["key_id"] for row in valid}),
    }
    converged = (
        registry_verification["verdict"] == "PASS"
        and len(valid) >= P39_THRESHOLD
        and all(value >= P39_THRESHOLD for value in independence.values())
    )
    body = {
        "schema": "KC144.P39.IC10ConvergenceEvaluation.V1",
        "registry_digest": registry.get("registry_digest"),
        "registry_verification": registry_verification,
        "receipts": receipts,
        "valid_returns": len(valid),
        "required_returns": P39_THRESHOLD,
        "independence_census": independence,
        "status": "CONVERGED" if converged else "HOLD",
        "authority_effect": "SUCCESSOR_AUTHORIZATION" if converged else "NONE",
    }
    return {
        **body,
        "evaluation_digest": content_address("kc144.p39.ic10-convergence", body),
    }


def _candidate_root(corpus: Mapping[str, Any], calibration: Mapping[str, Any]) -> str:
    body = {
        "parent_result_id": P38_RESULT_ID,
        "parent_release_digest": P38_RELEASE_DIGEST,
        "contract_digest": p39_contract()["contract_digest"],
        "policy_digest": p39_policy()["policy_digest"],
        "corpus_root": corpus.get("corpus_root"),
        "calibration_digest": calibration.get("calibration_digest"),
    }
    return content_address("kc144.p39.candidate-root", body)


def canonical_successor_decision(
    *,
    corpus: Mapping[str, Any],
    calibration: Mapping[str, Any],
    convergence: Mapping[str, Any],
) -> dict[str, Any]:
    candidate_root = _candidate_root(corpus, calibration)
    ready = (
        corpus.get("status") == "CORPUS_READY"
        and calibration.get("status") == "CALIBRATION_READY"
        and convergence.get("status") == "CONVERGED"
    )
    body = {
        "schema": "KC144.P39.CanonicalSuccessorDecision.V1",
        "candidate_root": candidate_root,
        "corpus_root": corpus.get("corpus_root"),
        "calibration_digest": calibration.get("calibration_digest"),
        "convergence_evaluation_digest": convergence.get("evaluation_digest"),
        "decision": "SUCCESSOR_READY" if ready else "HOLD",
        "reason": (
            "ALL_P39_GATES_CONVERGED"
            if ready
            else "LIVE_OUTCOME_OR_INDEPENDENT_IC10_GATES_OPEN"
        ),
        "proposed_weights": (
            calibration.get("proposed_weights", []) if ready else []
        ),
        "canonical_weight_updates_executed": 0,
        "successor_activated": False,
        "production_mutated": False,
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "SUCCESSOR_AUTHORIZATION" if ready else "NONE",
        "return": P39_ROUTE[-1],
        "next_seed": P39_NEXT_SEED,
    }
    return {
        **body,
        "decision_digest": content_address("kc144.p39.successor-decision", body),
    }


def _lane_receipt(index: int, lane: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    body = {
        "schema": "KC144.P39.LaneReceipt.V1",
        "lane_id": f"P39.L{index:02d}",
        "lane": lane,
        "payload_digest": content_address(
            f"kc144.p39.lane.{lane.lower()}", payload
        ),
        "return": P39_ROUTE[-1],
        "truth_effect": "NONE",
    }
    return {
        **body,
        "receipt_id": content_address("kc144.p39.lane-receipt", body),
    }


def compile_p39_cycle(
    *,
    observations: Sequence[Mapping[str, Any]] = (),
    signer_registry: Mapping[str, Any] | None = None,
    ic10_returns: Sequence[Mapping[str, Any]] = (),
    cutoff: str = P39_CUTOFF,
) -> dict[str, Any]:
    contract = p39_contract()
    policy = p39_policy()
    corpus = compile_live_outcome_corpus(observations, cutoff=cutoff)
    calibration = calibrate_weights(corpus)
    registry = dict(signer_registry or empty_ic10_registry())
    candidate_root = _candidate_root(corpus, calibration)
    convergence = evaluate_ic10_convergence(
        ic10_returns,
        registry=registry,
        candidate_root=candidate_root,
        corpus_root=str(corpus["corpus_root"]),
        calibration_digest=str(calibration["calibration_digest"]),
        policy_digest=str(policy["policy_digest"]),
        checked_at=cutoff,
    )
    decision = canonical_successor_decision(
        corpus=corpus,
        calibration=calibration,
        convergence=convergence,
    )
    leakage_payload = {
        "leaking_evidence_units": corpus["leaking_evidence_units"],
        "status": (
            "PASS" if not corpus["leaking_evidence_units"] else "FATAL_HOLD"
        ),
    }
    registry_payload = {
        "registry": registry,
        "verification": verify_ic10_registry(registry),
    }
    return_payload = {
        "return": P39_ROUTE[-1],
        "next_seed": P39_NEXT_SEED,
        "decision_digest": decision["decision_digest"],
    }
    payloads = (
        corpus,
        leakage_payload,
        calibration,
        registry_payload,
        convergence,
        decision,
        return_payload,
    )
    receipts = [
        _lane_receipt(index, lane, payload)
        for index, (lane, payload) in enumerate(zip(P39_LANES, payloads), 1)
    ]
    residuals: list[str] = []
    if corpus["status"] != "CORPUS_READY":
        residuals.append("LIVE_OUTCOME_CORPUS_INSUFFICIENT")
    if corpus["leaking_evidence_units"]:
        residuals.append("CROSS_PARTITION_LEAKAGE")
    if calibration["status"] != "CALIBRATION_READY":
        residuals.append("HELD_OUT_NON_DEGRADATION_NOT_ESTABLISHED")
    if registry_payload["verification"]["verdict"] != "PASS":
        residuals.append("FIXED_FIVE_SEAT_IC10_REGISTRY_INCOMPLETE")
    if convergence["status"] != "CONVERGED":
        residuals.append("THREE_OF_FIVE_INDEPENDENT_IC10_NOT_CONVERGED")
    state = {
        "schema": "KC144.P39.StateDelta.V1",
        "parent_result_id": P38_RESULT_ID,
        "candidate_root": candidate_root,
        "live_outcomes_admitted": corpus["census"]["accepted"],
        "calibration_observations": corpus["census"]["partitions"]["calibration"][
            "observations"
        ],
        "held_out_observations": corpus["census"]["partitions"]["held_out"][
            "observations"
        ],
        "independent_ic10_returns": convergence["valid_returns"],
        "canonical_successor_decision": decision["decision"],
        "canonical_weight_updates_executed": 0,
        "canonical_graph_mutations": 0,
        "successor_activated": False,
        "production_mutated": False,
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": decision["authority_effect"],
        "global_release": (
            "READY_FOR_P40_ACTIVATION"
            if decision["decision"] == "SUCCESSOR_READY"
            else "HOLD"
        ),
        "residuals": sorted(residuals),
        "return": P39_ROUTE[-1],
        "next_seed": P39_NEXT_SEED,
    }
    state["delta_id"] = content_address("kc144.p39.state-delta", state)
    body = {
        "schema": "KC144.P39.Macrocycle.V1",
        "contract_digest": contract["contract_digest"],
        "policy": policy,
        "corpus": corpus,
        "calibration": calibration,
        "signer_registry": registry,
        "ic10_returns": sorted(
            (dict(packet) for packet in ic10_returns),
            key=lambda row: str(row.get("return_id", "")),
        ),
        "ic10_convergence": convergence,
        "successor_decision": decision,
        "lane_receipts": receipts,
        "state": state,
    }
    return {**body, "envelope_digest": content_address("kc144.p39.macrocycle", body)}


def verify_p39_cycle(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: item for key, item in value.items() if key != "envelope_digest"}
    if value.get("schema") != "KC144.P39.Macrocycle.V1":
        errors.append("E_SCHEMA")
    if value.get("envelope_digest") != content_address("kc144.p39.macrocycle", body):
        errors.append("E_ENVELOPE_DIGEST")
    if value.get("contract_digest") != p39_contract()["contract_digest"]:
        errors.append("E_CONTRACT")
    policy = value.get("policy", {})
    if policy != p39_policy():
        errors.append("E_POLICY")
    corpus = value.get("corpus", {})
    corpus_body = {
        key: item for key, item in corpus.items() if key != "corpus_root"
    }
    if corpus.get("corpus_root") != content_address(
        "kc144.p39.live-outcome-corpus", corpus_body
    ):
        errors.append("E_CORPUS_ROOT")
    calibration = value.get("calibration", {})
    calibration_body = {
        key: item
        for key, item in calibration.items()
        if key != "calibration_digest"
    }
    if calibration.get("calibration_digest") != content_address(
        "kc144.p39.weight-calibration", calibration_body
    ):
        errors.append("E_CALIBRATION_DIGEST")
    convergence = value.get("ic10_convergence", {})
    convergence_body = {
        key: item
        for key, item in convergence.items()
        if key != "evaluation_digest"
    }
    if convergence.get("evaluation_digest") != content_address(
        "kc144.p39.ic10-convergence", convergence_body
    ):
        errors.append("E_CONVERGENCE_DIGEST")
    decision = value.get("successor_decision", {})
    decision_body = {
        key: item for key, item in decision.items() if key != "decision_digest"
    }
    if decision.get("decision_digest") != content_address(
        "kc144.p39.successor-decision", decision_body
    ):
        errors.append("E_DECISION_DIGEST")
    expected_candidate = _candidate_root(corpus, calibration)
    if (
        decision.get("candidate_root") != expected_candidate
        or value.get("state", {}).get("candidate_root") != expected_candidate
    ):
        errors.append("E_CANDIDATE_BINDING")
    receipts = value.get("lane_receipts", [])
    if len(receipts) != len(P39_LANES):
        errors.append("E_LANE_CENSUS")
    else:
        for index, (lane, receipt) in enumerate(zip(P39_LANES, receipts), 1):
            receipt_body = {
                key: item for key, item in receipt.items() if key != "receipt_id"
            }
            if (
                receipt.get("lane_id") != f"P39.L{index:02d}"
                or receipt.get("lane") != lane
                or receipt.get("receipt_id")
                != content_address("kc144.p39.lane-receipt", receipt_body)
            ):
                errors.append("E_LANE_RECEIPT")
    state = value.get("state", {})
    if (
        state.get("canonical_weight_updates_executed") != 0
        or state.get("canonical_graph_mutations") != 0
        or state.get("successor_activated") is not False
        or state.get("production_mutated") is not False
        or state.get("truth_effect") != "NONE"
        or state.get("evidence_effect") != "NONE"
    ):
        errors.append("E_PROTECTED_STATE_ESCALATION")
    ready = (
        corpus.get("status") == "CORPUS_READY"
        and calibration.get("status") == "CALIBRATION_READY"
        and convergence.get("status") == "CONVERGED"
    )
    if (decision.get("decision") == "SUCCESSOR_READY") != ready:
        errors.append("E_DECISION_WITHOUT_CONVERGENCE")
    if (
        state.get("global_release") == "READY_FOR_P40_ACTIVATION"
    ) != ready:
        errors.append("E_RELEASE_STATE")
    try:
        replay = compile_p39_cycle(
            observations=value.get("corpus", {}).get("observations", []),
            signer_registry=value.get("signer_registry"),
            ic10_returns=value.get("ic10_returns", []),
            cutoff=str(value.get("corpus", {}).get("cutoff", "")),
        )
        if replay != dict(value):
            errors.append("E_COLD_REPLAY")
    except (P39RuntimeError, TypeError, ValueError):
        errors.append("E_COLD_REPLAY")
    return {
        "schema": "KC144.P39.MacrocycleVerification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "envelope_digest": value.get("envelope_digest"),
    }


def compile_p39_release(
    output_directory: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
) -> dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(implementation_commit):
        raise P39RuntimeError("implementation_commit must be a Git SHA")
    if not GIT_SHA_RE.fullmatch(implementation_tree):
        raise P39RuntimeError("implementation_tree must be a Git tree SHA")
    contract = p39_contract()
    policy = p39_policy()
    cycle = compile_p39_cycle()
    verification = verify_p39_cycle(cycle)
    release_core = {
        "schema": "KC144.P39.Release.V1",
        "release_id": "KC144_P39_LIVE_OUTCOME_IC10_CANDIDATE_V1",
        "status": "CANDIDATE_HOLD",
        "implementation": {
            "repository": "demeet2k/guild-hall",
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "parent_result_id": P38_RESULT_ID,
        "parent_release_digest": P38_RELEASE_DIGEST,
        "contract_digest": contract["contract_digest"],
        "policy_digest": policy["policy_digest"],
        "corpus_root": cycle["corpus"]["corpus_root"],
        "calibration_digest": cycle["calibration"]["calibration_digest"],
        "convergence_evaluation_digest": cycle["ic10_convergence"][
            "evaluation_digest"
        ],
        "decision_digest": cycle["successor_decision"]["decision_digest"],
        "envelope_digest": cycle["envelope_digest"],
        "verification_verdict": verification["verdict"],
        "live_outcomes": 0,
        "independent_ic10_returns": 0,
        "canonical_weight_updates_executed": 0,
        "successor_activated": False,
        "production_authority": "HOLD",
        "truth_effect": "NONE",
        "next_seed": P39_NEXT_SEED,
    }
    release_digest = content_address("kc144.p39.release", release_core)
    release = {
        **release_core,
        "release_digest": release_digest,
        "result_id": "KC144.P39.CANDIDATE::"
        + release_digest.removeprefix("sha256:")[:24],
    }
    artifacts = {
        "p39_contract_v1.json": contract,
        "p39_calibration_policy_v1.json": policy,
        "p39_macrocycle_v1.json": cycle,
        "p39_verification_v1.json": verification,
        "p39_release_v1.json": release,
    }
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    for name, artifact in artifacts.items():
        (output / name).write_text(
            json.dumps(artifact, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    checksum_lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}"
        for path in sorted(output.glob("*.json"))
    ]
    (output / "SHA256SUMS").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )
    return release
