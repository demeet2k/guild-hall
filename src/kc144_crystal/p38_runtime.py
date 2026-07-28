from __future__ import annotations

import base64
import hashlib
import itertools
import json
import re
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
from .navigation import adjacency, navigation_relations, shortest_path
from .p37_reconciliation import (
    META_ATLAS_V10_SHA256,
    PUBLIC_P36_RESULT_ID,
    SOURCE_P37_RESULT_ID,
    bind_exact_p35_registry,
    expected_p35_registry_binding,
    p37_public_reconciliation,
    source_p37_capsule,
    verify_p35_registry_binding,
    verify_reconciliation,
)
from .station import build_station_bodies
from .transform import (
    br_mirror,
    br_rotate,
    f37_reflect,
    grid_d4_view,
    kc15_permute,
    kc27_transform,
    x16_algebra_translate,
    x16_schedule_rotate,
)


P38_LOOKUP_KEY = (
    "KC144.V3.9::MATH144.P38::META_NAVIGATOR_V2_DYNAMIC_MULTI_CRYSTAL_"
    "QUERY_COMPILER_LIVE_SOURCE_ROUTING_SECOND_ONE_EDGE_OUTCOME_CORPUS_"
    "AND_INDEPENDENT_IC10_MACROCYCLE_07"
)
P38_NEXT_SEED = (
    "KC144.V4.0::MATH144.P39::LIVE_OUTCOME_CORPUS_INDEPENDENT_IC10_"
    "CONVERGENCE_WEIGHT_CALIBRATION_AND_CANONICAL_SUCCESSOR_DECISION_"
    "MACROCYCLE_08"
)
P38_ROUTE = (
    "KC144.V1::GID135::M03",
    "KC144.V1::GID047::F04",
    "KC144.V1::GID141::M09",
    "KC144.V1::GID003::H03",
    "KC144.V1::GID144::M12",
)
P38_CRYSTALS = ("KC144", "BR21", "KC27", "KC54", "MATH144", "P31", "HEART")
P38_LANES = (
    "LINEAGE_RECONCILIATION",
    "EXACT_REGISTRY_BINDING",
    "DYNAMIC_MULTI_CRYSTAL_QUERY",
    "LIVE_SOURCE_ROUTING",
    "SECOND_ONE_EDGE_EXPERIMENT",
    "HELD_OUT_OUTCOME_CALIBRATION",
    "INDEPENDENT_IC10_RETURN",
)
P38_CUTOFF = "2026-07-28T23:59:59.000000Z"
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
GIT_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
RFC3339_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")
TOKEN_RE = re.compile(r"[a-z0-9]+")

SOURCE_CLASSES = frozenset(
    {"GOOGLE_DOC_REVISION", "REPOSITORY_BYTES", "LOCAL_ARTIFACT_BYTES"}
)
OUTCOME_CLASSES = frozenset({"TASK_OUTCOME", "EMPIRICAL_RESULT"})
OUTCOME_ORIGINS = frozenset({"PRODUCTION", "USER_OBSERVED", "CONNECTOR_OBSERVED"})
IC10_GATE_IDS = tuple(f"I{index:02d}" for index in range(1, 11))


class P38RuntimeError(ValueError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def _body_address(
    domain: str,
    value: Mapping[str, Any],
    *excluded: str,
) -> str:
    return content_address(
        domain,
        {key: item for key, item in value.items() if key not in excluded},
    )


def _require_digest(value: object, label: str) -> str:
    if not isinstance(value, str) or not DIGEST_RE.fullmatch(value):
        raise P38RuntimeError(f"{label} must be a lowercase SHA-256 address")
    return value


def _public_key_id(public_key: Ed25519PublicKey) -> str:
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return _sha256_bytes(raw)


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + ("=" * (-len(value) % 4)))


def p38_contract() -> dict[str, Any]:
    reconciliation = p37_public_reconciliation()
    body = {
        "schema": "KC144.P38.Contract.V1",
        "lookup_key": P38_LOOKUP_KEY,
        "public_parent": PUBLIC_P36_RESULT_ID,
        "source_sibling": SOURCE_P37_RESULT_ID,
        "reconciliation_digest": reconciliation["reconciliation_digest"],
        "route": list(P38_ROUTE),
        "crystals": list(P38_CRYSTALS),
        "lanes": [
            {
                "lane_id": f"P38.L{index:02d}",
                "lane": lane,
                "parallel_group": 1 if index <= 4 else 2 if index <= 6 else 3,
                "return": P38_ROUTE[-1],
            }
            for index, lane in enumerate(P38_LANES, 1)
        ],
        "merge_law": (
            "VERIFY_ALL_SEVEN_LANE_RECEIPTS_THEN_REDUCE_BY_CANONICAL_LANE_ORDER"
        ),
        "noncollapse": [
            "DISTINCT_P36_PARENTS_ARE_NOT_EQUAL",
            "SOURCE_P37_IMPORT_IS_NOT_REPARENTING",
            "DOC_REVISION_IS_NOT_REPOSITORY_BYTES",
            "REPOSITORY_BYTES_ARE_NOT_A_REAL_OUTCOME",
            "STRUCTURAL_EDGE_GAIN_IS_NOT_EMPIRICAL_SUCCESS",
            "PROPOSAL_GRAPH_IS_NOT_CANONICAL_GRAPH",
            "SIGNER_ENROLLMENT_IS_NOT_AUTHORITY",
            "SIGNATURE_VALIDITY_IS_NOT_INDEPENDENCE",
            "TRAINING_OUTCOME_IS_NOT_HELD_OUT_OUTCOME",
            "ROUTE_GENERATED_DATA_IS_NOT_EXTERNAL_EVIDENCE",
            "IC10_I01_TO_I09_IS_NOT_I10_AUTHORIZATION",
            "PUBLICATION_IS_NOT_TRUTH_PROMOTION",
        ],
        "ceilings": {
            "truth_effect": "NONE",
            "evidence_effect": "NONE",
            "authority_effect_without_independent_ic10": "NONE",
            "canonical_graph_mutation": False,
        },
    }
    return {**body, "contract_digest": content_address("kc144.p38.contract", body)}


def _transform_orbit(gid: int, band: str) -> dict[str, Any]:
    d4 = sorted(
        {
            grid_d4_view(gid, operation).target_gid
            for operation in (
                "identity",
                "r90",
                "r180",
                "r270",
                "reflect_vertical",
                "reflect_horizontal",
                "reflect_diagonal",
                "reflect_antidiagonal",
            )
        }
    )
    local: set[int] = {gid}
    law = "IDENTITY_ONLY"
    if band == "X16":
        local.update(
            x16_schedule_rotate(gid, pole_turn, lens_turn).target_gid
            for pole_turn in range(4)
            for lens_turn in range(4)
        )
        local.update(
            x16_algebra_translate(gid, pole, lens_turn).target_gid
            for pole in ("11", "10", "00", "01")
            for lens_turn in range(4)
        )
        law = "C4xC4_AND_V4xC4"
    elif band == "BR21":
        local.update(
            br_rotate(gid, operator_turn, lens_turn).target_gid
            for operator_turn in range(7)
            for lens_turn in range(3)
        )
        local.add(br_mirror(gid).target_gid)
        law = "C7xC3_PLUS_C2"
    elif band == "F37":
        local.add(f37_reflect(gid).target_gid)
        law = "P37_REFLECTION"
    elif band == "KC15":
        local.update(
            kc15_permute(gid, permutation).target_gid
            for permutation in itertools.permutations(range(4))
        )
        law = "S4_SUPPORT_ACTION"
    elif band == "KC27":
        local.update(
            kc27_transform(gid, permutation, signs).target_gid
            for permutation in itertools.permutations(range(3))
            for signs in itertools.product((-1, 1), repeat=3)
        )
        law = "B3_SIGNED_PERMUTATION"
    elif band == "H6":
        law = "CONSTITUTIONAL_INDEX"
    elif band == "IC10":
        law = "ORDERED_CONJUNCTIVE_GATE"
    elif band == "SSN12":
        law = "SOLID_STATE_INDEX"
    return {
        "d4_address_orbit": d4,
        "d4_orbit_size": len(d4),
        "local_law": law,
        "local_orbit": sorted(local),
        "local_orbit_size": len(local),
        "identity_preserved": True,
        "truth_effect": "NONE",
    }


def coordinate_tensor_144() -> dict[str, Any]:
    coordinates: list[dict[str, Any]] = []
    for body in build_station_bodies():
        coordinates.append(
            {
                "gid": body["gid"],
                "grid": body["grid"],
                "band": body["band"],
                "station": body["station"],
                "question": body["governing_question"],
                "band_invariant": body["band_invariant"],
                "return_obligation": body["return_obligation"],
                "transform": _transform_orbit(body["gid"], body["band"]),
                "kc54_duplex": (
                    {
                        "plus": f"KC54+::{body['station']}",
                        "conjugate": f"KC54*::{body['station']}",
                        "relation": "TYPED_SHADOW_NOT_IDENTITY",
                    }
                    if body["band"] == "KC27"
                    else None
                ),
            }
        )
    body = {
        "schema": "KC144.P38.CoordinateTensor144.V1",
        "coordinates": coordinates,
        "census": {
            "stations": len(coordinates),
            "d4_views": sum(
                row["transform"]["d4_orbit_size"] for row in coordinates
            ),
            "local_orbit_memberships": sum(
                row["transform"]["local_orbit_size"] for row in coordinates
            ),
            "kc54_duplex_nodes": sum(row["kc54_duplex"] is not None for row in coordinates),
        },
        "law": (
            "ALL_TRANSFORMS_ARE_SIMULTANEOUS_TYPED_VIEWS; NONE CHANGES SOURCE "
            "IDENTITY, TRUTH, EVIDENCE, OR AUTHORITY"
        ),
    }
    return {
        **body,
        "tensor_digest": content_address("kc144.p38.coordinate-tensor", body),
    }


def _tokens(value: object) -> set[str]:
    return set(TOKEN_RE.findall(str(value).lower()))


def _lens_gids(lens: str, bodies: Sequence[Mapping[str, Any]]) -> list[int]:
    if lens == "BR21":
        return [int(body["gid"]) for body in bodies if body["band"] == "BR21"]
    if lens in {"KC27", "KC54"}:
        return [int(body["gid"]) for body in bodies if body["band"] == "KC27"]
    if lens == "P31":
        return [135, 47, 141, 3, 144]
    if lens == "HEART":
        return [6, 47, 141, 3, 144]
    return [int(body["gid"]) for body in bodies]


def compile_multi_crystal_query(query: Mapping[str, Any]) -> dict[str, Any]:
    if query.get("schema") != "KC144.P38.Query.V1":
        raise P38RuntimeError("query schema must be KC144.P38.Query.V1")
    goal = query.get("goal")
    if not isinstance(goal, str) or not goal.strip():
        raise P38RuntimeError("query goal is required")
    requested = query.get("crystals", list(P38_CRYSTALS))
    if (
        not isinstance(requested, Sequence)
        or isinstance(requested, (str, bytes))
        or not requested
    ):
        raise P38RuntimeError("query crystals must be a non-empty array")
    requested_set = set(str(item) for item in requested)
    if not requested_set <= set(P38_CRYSTALS):
        raise P38RuntimeError("query contains an unknown crystal")
    crystals = sorted(requested_set, key=P38_CRYSTALS.index)
    terms = sorted(
        _tokens(goal)
        | {
            token
            for term in query.get("terms", [])
            for token in _tokens(term)
        }
    )
    bodies = list(build_station_bodies())
    by_gid = {int(body["gid"]): body for body in bodies}
    graph = adjacency(navigation_relations())
    lanes: list[dict[str, Any]] = []
    for lens in crystals:
        candidates = _lens_gids(lens, bodies)
        scored: list[tuple[int, int]] = []
        for gid in candidates:
            body = by_gid[gid]
            searchable = _tokens(
                " ".join(
                    [
                        str(body["station"]),
                        str(body["architectural_label"]),
                        str(body["structural_role"]),
                        str(body["governing_question"]),
                        str(body["band_invariant"]),
                    ]
                )
            )
            scored.append((len(set(terms) & searchable), gid))
        selected = [
            gid
            for _, gid in sorted(scored, key=lambda row: (-row[0], row[1]))[:3]
        ]
        entry = 6 if lens == "HEART" else 135 if lens == "P31" else selected[0]
        path = shortest_path(entry, selected[0], graph)
        lane_body = {
            "crystal": lens,
            "entry_gid": entry,
            "selected_gids": selected,
            "selected_stations": [by_gid[gid]["station"] for gid in selected],
            "route": path,
            "transform_views": [
                _transform_orbit(gid, str(by_gid[gid]["band"])) for gid in selected
            ],
            "selection_law": "TOKEN_OVERLAP_DESCENDING_THEN_GID_ASCENDING",
            "truth_effect": "NONE",
        }
        lanes.append(
            {
                **lane_body,
                "lane_digest": content_address(
                    "kc144.p38.multi-crystal-query-lane", lane_body
                ),
            }
        )
    body = {
        "schema": "KC144.P38.CompiledQuery.V1",
        "query": {
            "goal": goal.strip(),
            "terms": terms,
            "crystals": crystals,
            "source_surfaces": sorted(
                set(str(item) for item in query.get("source_surfaces", []))
            ),
        },
        "lanes": lanes,
        "parallel_width": len(lanes),
        "reducer": "CANONICAL_CRYSTAL_ORDER_THEN_LANE_DIGEST",
        "coordinate_tensor_digest": coordinate_tensor_144()["tensor_digest"],
        "route": list(P38_ROUTE),
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "query_digest": content_address("kc144.p38.compiled-query", body),
    }


def build_repository_byte_event(
    *,
    repository: str,
    branch: str,
    commit: str,
    tree: str,
    observed_at: str,
    files: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise P38RuntimeError("repository must be owner/name")
    if not GIT_SHA_RE.fullmatch(commit) or not GIT_SHA_RE.fullmatch(tree):
        raise P38RuntimeError("commit and tree must be exact Git SHA-1 identities")
    if not RFC3339_RE.fullmatch(observed_at):
        raise P38RuntimeError("observed_at must be fixed-precision UTC RFC3339")
    normalized_files: list[dict[str, Any]] = []
    for file in files:
        path = str(file.get("path", ""))
        blob = str(file.get("blob", ""))
        digest = str(file.get("sha256", ""))
        size = file.get("size")
        if (
            not path
            or path.startswith("/")
            or ".." in Path(path).parts
            or not GIT_SHA_RE.fullmatch(blob)
            or not DIGEST_RE.fullmatch(digest)
            or not isinstance(size, int)
            or size < 0
        ):
            raise P38RuntimeError("repository file binding is malformed")
        normalized_files.append(
            {"path": path, "blob": blob, "sha256": digest, "size": size}
        )
    normalized_files.sort(key=lambda row: row["path"])
    if len({row["path"] for row in normalized_files}) != len(normalized_files):
        raise P38RuntimeError("repository file paths must be unique")
    body = {
        "schema": "KC144.P38.SourceEvent.V1",
        "source_class": "REPOSITORY_BYTES",
        "observed_at": observed_at,
        "source": {
            "surface": "GITHUB",
            "repository": repository,
            "branch": branch,
            "commit": commit,
            "tree": tree,
            "version_type": "GIT_COMMIT_TREE_AND_BLOB",
        },
        "files": normalized_files,
        "consent": {
            "scope": ["CURRENT_TASK_EXECUTION", "PUBLICATION"],
            "publication_allowed": True,
        },
        "source_verified": True,
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {**body, "event_id": content_address("kc144.p38.source-event", body)}


def build_doc_revision_event(
    *,
    body_sha256: str,
    revision_commitment: str,
    observed_at: str,
    issuer_commitment: str,
) -> dict[str, Any]:
    _require_digest(body_sha256, "body sha256")
    _require_digest(revision_commitment, "revision commitment")
    _require_digest(issuer_commitment, "issuer commitment")
    if not RFC3339_RE.fullmatch(observed_at):
        raise P38RuntimeError("observed_at must be fixed-precision UTC RFC3339")
    body = {
        "schema": "KC144.P38.SourceEvent.V1",
        "source_class": "GOOGLE_DOC_REVISION",
        "observed_at": observed_at,
        "source": {
            "surface": "GOOGLE_DRIVE",
            "version_type": "GOOGLE_DRIVE_REVISION",
            "body_sha256": body_sha256,
            "revision_commitment": revision_commitment,
            "issuer_commitment": issuer_commitment,
        },
        "consent": {
            "scope": ["CURRENT_TASK_EXECUTION"],
            "publication_allowed": False,
        },
        "source_verified": True,
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {**body, "event_id": content_address("kc144.p38.source-event", body)}


def build_local_artifact_event(
    *,
    name: str,
    digest: str,
    observed_at: str,
    public_summary: Mapping[str, Any],
) -> dict[str, Any]:
    _require_digest(digest, "artifact digest")
    if not RFC3339_RE.fullmatch(observed_at):
        raise P38RuntimeError("observed_at must be fixed-precision UTC RFC3339")
    body = {
        "schema": "KC144.P38.SourceEvent.V1",
        "source_class": "LOCAL_ARTIFACT_BYTES",
        "observed_at": observed_at,
        "source": {
            "surface": "LOCAL_VERIFIED_ARTIFACT",
            "name": name,
            "version_type": "SHA256_BYTES",
            "digest": digest,
        },
        "public_summary": dict(public_summary),
        "consent": {
            "scope": ["CURRENT_TASK_EXECUTION"],
            "publication_allowed": False,
        },
        "source_verified": True,
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {**body, "event_id": content_address("kc144.p38.source-event", body)}


def route_source_events(
    events: Sequence[Mapping[str, Any]], *, cutoff: str
) -> dict[str, Any]:
    if not RFC3339_RE.fullmatch(cutoff):
        raise P38RuntimeError("cutoff must be fixed-precision UTC RFC3339")
    receipts: list[dict[str, Any]] = []
    seen: set[str] = set()
    for event in sorted(events, key=lambda row: str(row.get("event_id", ""))):
        errors: list[str] = []
        holds: list[str] = []
        event_id = str(event.get("event_id", ""))
        source_class = event.get("source_class")
        if event.get("schema") != "KC144.P38.SourceEvent.V1":
            errors.append("E_SCHEMA")
        if source_class not in SOURCE_CLASSES:
            errors.append("E_SOURCE_CLASS")
        if event_id in seen:
            errors.append("E_DUPLICATE_EVENT")
        seen.add(event_id)
        observed_at = event.get("observed_at")
        if not isinstance(observed_at, str) or not RFC3339_RE.fullmatch(observed_at):
            errors.append("E_OBSERVED_AT")
        elif observed_at > cutoff:
            holds.append("E_AFTER_CUTOFF")
        if event.get("source_verified") is not True:
            errors.append("E_SOURCE_UNVERIFIED")
        consent = event.get("consent", {})
        if (
            not isinstance(consent, Mapping)
            or "CURRENT_TASK_EXECUTION" not in consent.get("scope", [])
        ):
            errors.append("E_CONSENT")
        if any(event.get(field) != "NONE" for field in (
            "truth_effect",
            "evidence_effect",
            "authority_effect",
        )):
            errors.append("E_EFFECT_ESCALATION")
        body = {key: item for key, item in event.items() if key != "event_id"}
        if event_id != content_address("kc144.p38.source-event", body):
            errors.append("E_EVENT_DIGEST")
        if source_class == "REPOSITORY_BYTES":
            source = event.get("source", {})
            if (
                not isinstance(source, Mapping)
                or source.get("version_type") != "GIT_COMMIT_TREE_AND_BLOB"
                or not GIT_SHA_RE.fullmatch(str(source.get("commit", "")))
                or not GIT_SHA_RE.fullmatch(str(source.get("tree", "")))
            ):
                errors.append("E_REPOSITORY_IDENTITY")
        elif source_class == "GOOGLE_DOC_REVISION":
            source = event.get("source", {})
            if (
                not isinstance(source, Mapping)
                or source.get("version_type") != "GOOGLE_DRIVE_REVISION"
            ):
                errors.append("E_DOC_REVISION_IDENTITY")
            if "files" in event:
                errors.append("E_DOC_REPOSITORY_CONFLATION")
        status = "REJECTED" if errors else "HELD" if holds else "ADMITTED_NON_PROMOTING"
        receipt_body = {
            "event_id": event_id,
            "source_class": source_class,
            "status": status,
            "errors": sorted(errors),
            "holds": sorted(holds),
            "truth_effect": "NONE",
            "authority_effect": "NONE",
        }
        receipts.append(
            {
                **receipt_body,
                "receipt_id": content_address(
                    "kc144.p38.source-route-receipt", receipt_body
                ),
            }
        )
    admitted = [row for row in receipts if row["status"] == "ADMITTED_NON_PROMOTING"]
    body = {
        "schema": "KC144.P38.SourceRouting.V1",
        "cutoff": cutoff,
        "receipts": receipts,
        "counts": {
            "observed": len(receipts),
            "admitted": len(admitted),
            "repository_byte_events": sum(
                row["source_class"] == "REPOSITORY_BYTES" for row in admitted
            ),
            "doc_revision_events": sum(
                row["source_class"] == "GOOGLE_DOC_REVISION" for row in admitted
            ),
        },
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "routing_digest": content_address("kc144.p38.source-routing", body),
    }


def second_edge_experiment(*, prerequisites_pass: bool) -> dict[str, Any]:
    body = {
        "schema": "KC144.P38.SecondOneEdgeExperiment.V1",
        "proposal_parent": {
            "source_result_id": SOURCE_P37_RESULT_ID,
            "meta_atlas_sha256": META_ATLAS_V10_SHA256,
            "first_edge": ["GID047/F04", "GID064/F21"],
            "proposal_edges": 311,
            "candidate_router_distance_sum": 70,
            "global_distance_sum": 50376,
            "global_diameter": 11,
        },
        "second_edge": {
            "source": "GID135/M03",
            "target": "GID047/F04",
            "source_candidate_digest": (
                "sha256:aa461e4f9fa93b7881568309794b85698ac9f74a178c30fff4078878e62e5356"
            ),
            "selection": "P37_REDIFFERENTIATED_RANK_1",
        },
        "measurement": {
            "candidate_distance_before": 6,
            "candidate_distance_after": 1,
            "candidate_router_distance_sum_before": 70,
            "candidate_router_distance_sum_after": 55,
            "candidate_router_distance_reduction": 15,
            "global_distance_sum_before": 50376,
            "global_distance_sum_after": 49326,
            "global_distance_reduction": 1050,
            "global_diameter_before": 11,
            "global_diameter_after": 10,
        },
        "executed_in_proposal_graph": prerequisites_pass,
        "executed_in_canonical_graph": False,
        "proposal_edges_after": 312 if prerequisites_pass else 311,
        "canonical_edges_after": 310,
        "state": (
            "SECOND_EDGE_APPLIED_TO_COPIED_PROPOSAL_GRAPH"
            if prerequisites_pass
            else "HELD_PREREQUISITES"
        ),
        "structural_outcome": (
            "MEASURED_DISTANCE_REDUCTION" if prerequisites_pass else "NOT_EXECUTED"
        ),
        "real_world_outcome": "UNMEASURED",
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "experiment_digest": content_address(
            "kc144.p38.second-one-edge-experiment", body
        ),
    }


def build_outcome(
    *,
    outcome_class: str,
    origin_class: str,
    observed_at: str,
    source_surface: str,
    source_commitment: str,
    route_id: str,
    metric: str,
    value: float,
    private_key: Ed25519PrivateKey | None = None,
) -> dict[str, Any]:
    if outcome_class not in OUTCOME_CLASSES:
        raise P38RuntimeError("unknown outcome class")
    _require_digest(source_commitment, "source commitment")
    if not RFC3339_RE.fullmatch(observed_at):
        raise P38RuntimeError("observed_at must be fixed-precision UTC RFC3339")
    body = {
        "schema": "KC144.P38.HeldOutOutcome.V1",
        "outcome_class": outcome_class,
        "origin_class": origin_class,
        "observed_at": observed_at,
        "source_surface": source_surface,
        "source_commitment": source_commitment,
        "route_id": route_id,
        "partition": "HELD_OUT",
        "metric": metric,
        "value": value,
        "consent_scope": ["CALIBRATION", "CURRENT_TASK_EXECUTION"],
        "source_verified": True,
        "route_generated": False,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    outcome_id = content_address("kc144.p38.held-out-outcome", body)
    signed_body = {**body, "outcome_id": outcome_id}
    signature = None
    if private_key is not None:
        payload = b"KC144.P38.OUTCOME.V1\0" + canonical_bytes(signed_body)
        signature = {
            "algorithm": "Ed25519",
            "domain": "KC144.P38.OUTCOME.V1",
            "key_id": _public_key_id(private_key.public_key()),
            "value": _encode(private_key.sign(payload)),
        }
    return {**signed_body, "signature": signature}


def compile_outcome_calibration(
    outcomes: Sequence[Mapping[str, Any]], *, cutoff: str
) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for outcome in sorted(outcomes, key=lambda row: str(row.get("outcome_id", ""))):
        errors: list[str] = []
        body = {
            key: item
            for key, item in outcome.items()
            if key not in {"outcome_id", "signature"}
        }
        outcome_id = str(outcome.get("outcome_id", ""))
        if outcome.get("schema") != "KC144.P38.HeldOutOutcome.V1":
            errors.append("E_SCHEMA")
        if outcome_id != content_address("kc144.p38.held-out-outcome", body):
            errors.append("E_OUTCOME_DIGEST")
        if outcome_id in seen:
            errors.append("E_DUPLICATE_OUTCOME")
        seen.add(outcome_id)
        if outcome.get("outcome_class") not in OUTCOME_CLASSES:
            errors.append("E_OUTCOME_CLASS")
        if outcome.get("origin_class") not in OUTCOME_ORIGINS:
            errors.append("E_NONPRODUCTION_ORIGIN")
        if outcome.get("partition") != "HELD_OUT":
            errors.append("E_NOT_HELD_OUT")
        if outcome.get("route_generated") is not False:
            errors.append("E_ROUTE_GENERATED")
        if outcome.get("source_verified") is not True:
            errors.append("E_SOURCE_UNVERIFIED")
        if not DIGEST_RE.fullmatch(str(outcome.get("source_commitment", ""))):
            errors.append("E_SOURCE_COMMITMENT")
        if set(outcome.get("consent_scope", [])) < {
            "CALIBRATION",
            "CURRENT_TASK_EXECUTION",
        }:
            errors.append("E_CONSENT")
        observed_at = outcome.get("observed_at")
        if (
            not isinstance(observed_at, str)
            or not RFC3339_RE.fullmatch(observed_at)
            or observed_at > cutoff
        ):
            errors.append("E_TIME")
        if errors:
            rejected.append({"outcome_id": outcome_id, "errors": sorted(errors)})
        else:
            accepted.append(
                {
                    "outcome_id": outcome_id,
                    "outcome_class": outcome["outcome_class"],
                    "source_surface": outcome["source_surface"],
                    "route_id": outcome["route_id"],
                    "metric": outcome["metric"],
                    "value": outcome["value"],
                }
            )
    source_surfaces = sorted({row["source_surface"] for row in accepted})
    routes = sorted({row["route_id"] for row in accepted})
    ready = len(accepted) >= 12 and len(source_surfaces) >= 3 and len(routes) >= 3
    proposed_weight_updates = (
        [
            {
                "route_id": route,
                "observations": sum(row["route_id"] == route for row in accepted),
                "mean": (
                    sum(
                        float(row["value"])
                        for row in accepted
                        if row["route_id"] == route
                    )
                    / sum(row["route_id"] == route for row in accepted)
                ),
            }
            for route in routes
        ]
        if ready
        else []
    )
    body = {
        "schema": "KC144.P38.OutcomeCalibration.V1",
        "accepted": accepted,
        "rejected": rejected,
        "census": {
            "accepted": len(accepted),
            "rejected": len(rejected),
            "source_surfaces": len(source_surfaces),
            "routes": len(routes),
            "minimum_outcomes": 12,
            "minimum_source_surfaces": 3,
            "minimum_routes": 3,
        },
        "status": "CALIBRATION_READY" if ready else "CORPUS_HOLD",
        "proposed_weight_updates": proposed_weight_updates,
        "canonical_weight_updates_executed": 0,
        "truth_effect": "NONE",
        "authority_effect": "NONE",
    }
    return {
        **body,
        "calibration_digest": content_address(
            "kc144.p38.outcome-calibration", body
        ),
    }


def empty_signer_registry() -> dict[str, Any]:
    body = {
        "schema": "KC144.P38.TrustedSignerRegistry.V1",
        "entries": [],
        "authority_granted_by_enrollment": False,
    }
    return {
        **body,
        "registry_digest": content_address("kc144.p38.signer-registry", body),
    }


def signer_enrollment_challenge(
    *,
    signer_id: str,
    public_key: Ed25519PublicKey,
    valid_from: str,
    valid_until: str,
) -> dict[str, Any]:
    if (
        not signer_id
        or not RFC3339_RE.fullmatch(valid_from)
        or not RFC3339_RE.fullmatch(valid_until)
        or valid_from >= valid_until
    ):
        raise P38RuntimeError("signer identity and validity interval are required")
    raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    body = {
        "schema": "KC144.P38.SignerEnrollmentChallenge.V1",
        "signer_id": signer_id,
        "key_id": _public_key_id(public_key),
        "public_key": _encode(raw),
        "algorithm": "Ed25519",
        "purpose": "INDEPENDENT_IC10",
        "scope": [P38_LOOKUP_KEY],
        "independence_class": "EXTERNAL_INDEPENDENT",
        "valid_from": valid_from,
        "valid_until": valid_until,
        "authority_granted": False,
    }
    return {
        **body,
        "challenge_digest": content_address(
            "kc144.p38.signer-enrollment-challenge", body
        ),
    }


def enroll_trusted_signer(
    registry: Mapping[str, Any],
    challenge: Mapping[str, Any],
    proof_of_possession: str,
) -> dict[str, Any]:
    errors: list[str] = []
    if registry.get("schema") != "KC144.P38.TrustedSignerRegistry.V1":
        errors.append("E_REGISTRY_SCHEMA")
    registry_body = {
        key: item for key, item in registry.items() if key != "registry_digest"
    }
    if registry.get("registry_digest") != content_address(
        "kc144.p38.signer-registry", registry_body
    ):
        errors.append("E_REGISTRY_DIGEST")
    challenge_body = {
        key: item for key, item in challenge.items() if key != "challenge_digest"
    }
    if challenge.get("challenge_digest") != content_address(
        "kc144.p38.signer-enrollment-challenge", challenge_body
    ):
        errors.append("E_CHALLENGE_DIGEST")
    try:
        key = Ed25519PublicKey.from_public_bytes(
            _decode(str(challenge.get("public_key", "")))
        )
        if _public_key_id(key) != challenge.get("key_id"):
            errors.append("E_KEY_ID")
        key.verify(
            _decode(proof_of_possession),
            b"KC144.P38.SIGNER-ENROLLMENT.V1\0" + canonical_bytes(challenge),
        )
    except (ValueError, InvalidSignature):
        errors.append("E_PROOF_OF_POSSESSION")
    if challenge.get("purpose") != "INDEPENDENT_IC10":
        errors.append("E_PURPOSE")
    if challenge.get("independence_class") != "EXTERNAL_INDEPENDENT":
        errors.append("E_INDEPENDENCE")
    if challenge.get("authority_granted") is not False:
        errors.append("E_AUTHORITY_ESCALATION")
    if errors:
        raise P38RuntimeError("signer enrollment failed: " + ", ".join(errors))
    entries = list(registry.get("entries", []))
    if any(entry.get("key_id") == challenge.get("key_id") for entry in entries):
        raise P38RuntimeError("signer key is already enrolled")
    entry_body = {
        "signer_id": challenge["signer_id"],
        "key_id": challenge["key_id"],
        "public_key": challenge["public_key"],
        "algorithm": "Ed25519",
        "purpose": challenge["purpose"],
        "scope": challenge["scope"],
        "independence_class": challenge["independence_class"],
        "valid_from": challenge["valid_from"],
        "valid_until": challenge["valid_until"],
        "revoked": False,
        "proof_of_possession": proof_of_possession,
        "challenge_digest": challenge["challenge_digest"],
        "authority_granted": False,
    }
    entry = {
        **entry_body,
        "entry_digest": content_address("kc144.p38.signer-entry", entry_body),
    }
    entries.append(entry)
    entries.sort(key=lambda row: row["key_id"])
    result_body = {
        "schema": "KC144.P38.TrustedSignerRegistry.V1",
        "entries": entries,
        "authority_granted_by_enrollment": False,
    }
    return {
        **result_body,
        "registry_digest": content_address(
            "kc144.p38.signer-registry", result_body
        ),
    }


def verify_signer_registry(registry: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if registry.get("schema") != "KC144.P38.TrustedSignerRegistry.V1":
        errors.append("E_SCHEMA")
    registry_body = {
        key: item for key, item in registry.items() if key != "registry_digest"
    }
    if registry.get("registry_digest") != content_address(
        "kc144.p38.signer-registry", registry_body
    ):
        errors.append("E_REGISTRY_DIGEST")
    entries = registry.get("entries", [])
    if not isinstance(entries, list):
        entries = []
        errors.append("E_ENTRIES")
    key_ids: list[str] = []
    for entry in entries:
        if not isinstance(entry, Mapping):
            errors.append("E_ENTRY")
            continue
        entry_body = {
            key: item for key, item in entry.items() if key != "entry_digest"
        }
        if entry.get("entry_digest") != content_address(
            "kc144.p38.signer-entry", entry_body
        ):
            errors.append("E_ENTRY_DIGEST")
        key_ids.append(str(entry.get("key_id", "")))
        if (
            entry.get("purpose") != "INDEPENDENT_IC10"
            or entry.get("independence_class") != "EXTERNAL_INDEPENDENT"
            or P38_LOOKUP_KEY not in entry.get("scope", [])
            or entry.get("authority_granted") is not False
        ):
            errors.append("E_ENTRY_SCOPE")
        try:
            key = Ed25519PublicKey.from_public_bytes(
                _decode(str(entry.get("public_key", "")))
            )
            if _public_key_id(key) != entry.get("key_id"):
                errors.append("E_KEY_ID")
            challenge = {
                "schema": "KC144.P38.SignerEnrollmentChallenge.V1",
                "signer_id": entry.get("signer_id"),
                "key_id": entry.get("key_id"),
                "public_key": entry.get("public_key"),
                "algorithm": "Ed25519",
                "purpose": entry.get("purpose"),
                "scope": entry.get("scope"),
                "independence_class": entry.get("independence_class"),
                "valid_from": entry.get("valid_from"),
                "valid_until": entry.get("valid_until"),
                "authority_granted": False,
                "challenge_digest": entry.get("challenge_digest"),
            }
            challenge_body = {
                key_: item
                for key_, item in challenge.items()
                if key_ != "challenge_digest"
            }
            if challenge.get("challenge_digest") != content_address(
                "kc144.p38.signer-enrollment-challenge", challenge_body
            ):
                errors.append("E_CHALLENGE_DIGEST")
            key.verify(
                _decode(str(entry.get("proof_of_possession", ""))),
                b"KC144.P38.SIGNER-ENROLLMENT.V1\0"
                + canonical_bytes(challenge),
            )
        except (ValueError, InvalidSignature):
            errors.append("E_PROOF_OF_POSSESSION")
    if len(key_ids) != len(set(key_ids)):
        errors.append("E_DUPLICATE_KEY")
    if registry.get("authority_granted_by_enrollment") is not False:
        errors.append("E_AUTHORITY_ESCALATION")
    return {
        "schema": "KC144.P38.TrustedSignerRegistryVerification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
    }


def build_ic10_return(
    *,
    candidate_root: str,
    calibration_digest: str,
    source_routing_digest: str,
    signer_id: str,
    private_key: Ed25519PrivateKey,
    issued_at: str,
    expires_at: str,
    nonce: str,
    decision: str = "AUTHORIZE_SUCCESSOR",
) -> dict[str, Any]:
    _require_digest(candidate_root, "candidate root")
    _require_digest(calibration_digest, "calibration digest")
    _require_digest(source_routing_digest, "source routing digest")
    if (
        not RFC3339_RE.fullmatch(issued_at)
        or not RFC3339_RE.fullmatch(expires_at)
        or issued_at >= expires_at
        or not nonce
    ):
        raise P38RuntimeError("IC10 validity interval and nonce are required")
    body = {
        "schema": "KC144.P38.IndependentIC10Return.V1",
        "candidate_root": candidate_root,
        "calibration_digest": calibration_digest,
        "source_routing_digest": source_routing_digest,
        "signer_id": signer_id,
        "key_id": _public_key_id(private_key.public_key()),
        "issued_at": issued_at,
        "expires_at": expires_at,
        "nonce": nonce,
        "decision": decision,
        "gates": [{"gate": gate, "status": "PASS"} for gate in IC10_GATE_IDS],
        "return_target": P38_ROUTE[-1],
    }
    return_id = content_address("kc144.p38.ic10-return", body)
    signed_body = {**body, "return_id": return_id}
    signature = private_key.sign(
        b"KC144.P38.INDEPENDENT-IC10-RETURN.V1\0" + canonical_bytes(signed_body)
    )
    return {
        **signed_body,
        "signature": {
            "algorithm": "Ed25519",
            "domain": "KC144.P38.INDEPENDENT-IC10-RETURN.V1",
            "value": _encode(signature),
        },
    }


def verify_ic10_returns(
    returns: Sequence[Mapping[str, Any]],
    *,
    signer_registry: Mapping[str, Any],
    candidate_root: str,
    calibration: Mapping[str, Any],
    source_routing: Mapping[str, Any],
    checked_at: str,
) -> dict[str, Any]:
    registry_verification = verify_signer_registry(signer_registry)
    entries = {
        str(entry.get("key_id")): entry
        for entry in signer_registry.get("entries", [])
        if isinstance(entry, Mapping)
    }
    receipts: list[dict[str, Any]] = []
    seen_nonce: set[tuple[str, str]] = set()
    for packet in sorted(returns, key=lambda row: str(row.get("return_id", ""))):
        errors: list[str] = []
        if registry_verification["verdict"] != "PASS":
            errors.append("E_SIGNER_REGISTRY")
        body = {
            key: item for key, item in packet.items() if key not in {"return_id", "signature"}
        }
        if packet.get("return_id") != content_address("kc144.p38.ic10-return", body):
            errors.append("E_RETURN_DIGEST")
        if packet.get("candidate_root") != candidate_root:
            errors.append("E_CANDIDATE_ROOT")
        if packet.get("calibration_digest") != calibration.get("calibration_digest"):
            errors.append("E_CALIBRATION_BINDING")
        if packet.get("source_routing_digest") != source_routing.get("routing_digest"):
            errors.append("E_SOURCE_BINDING")
        if calibration.get("status") != "CALIBRATION_READY":
            errors.append("E_OUTCOME_CORPUS_HOLD")
        if source_routing.get("counts", {}).get("repository_byte_events", 0) < 1:
            errors.append("E_REPOSITORY_EVENT")
        if packet.get("decision") != "AUTHORIZE_SUCCESSOR":
            errors.append("E_DECISION")
        gates = packet.get("gates", [])
        if [row.get("gate") for row in gates] != list(IC10_GATE_IDS) or any(
            row.get("status") != "PASS" for row in gates
        ):
            errors.append("E_IC10_GATES")
        key_id = str(packet.get("key_id", ""))
        entry = entries.get(key_id)
        if not entry:
            errors.append("E_SIGNER_UNENROLLED")
        else:
            if (
                entry.get("purpose") != "INDEPENDENT_IC10"
                or entry.get("independence_class") != "EXTERNAL_INDEPENDENT"
                or P38_LOOKUP_KEY not in entry.get("scope", [])
                or entry.get("revoked") is not False
            ):
                errors.append("E_SIGNER_SCOPE")
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
                    != "KC144.P38.INDEPENDENT-IC10-RETURN.V1"
                ):
                    raise ValueError("invalid signature envelope")
                signed_body = {**body, "return_id": packet.get("return_id")}
                public_key.verify(
                    _decode(str(signature.get("value", ""))),
                    b"KC144.P38.INDEPENDENT-IC10-RETURN.V1\0"
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
        if nonce_key in seen_nonce:
            errors.append("E_NONCE_REPLAY")
        seen_nonce.add(nonce_key)
        receipts.append(
            {
                "return_id": packet.get("return_id"),
                "key_id": key_id,
                "verdict": "PASS" if not errors else "FAIL",
                "errors": sorted(errors),
            }
        )
    valid = [row for row in receipts if row["verdict"] == "PASS"]
    body = {
        "schema": "KC144.P38.IndependentIC10Evaluation.V1",
        "receipts": receipts,
        "valid_independent_returns": len(valid),
        "required_independent_returns": 1,
        "status": "AUTHORIZED" if valid else "HOLD",
        "authority_effect": "SUCCESSOR_AUTHORIZATION" if valid else "NONE",
    }
    return {
        **body,
        "evaluation_digest": content_address("kc144.p38.ic10-evaluation", body),
    }


def _lane_receipt(
    lane: str,
    index: int,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    body = {
        "schema": "KC144.P38.LaneReceipt.V1",
        "lane_id": f"P38.L{index:02d}",
        "lane": lane,
        "payload_digest": content_address(
            f"kc144.p38.lane.{lane.lower()}", payload
        ),
        "return": P38_ROUTE[-1],
        "truth_effect": "NONE",
    }
    return {
        **body,
        "receipt_id": content_address("kc144.p38.lane-receipt", body),
    }


def compile_p38_cycle(
    *,
    query: Mapping[str, Any],
    registry_binding: Mapping[str, Any],
    source_events: Sequence[Mapping[str, Any]] = (),
    outcomes: Sequence[Mapping[str, Any]] = (),
    signer_registry: Mapping[str, Any] | None = None,
    ic10_returns: Sequence[Mapping[str, Any]] = (),
    cutoff: str = P38_CUTOFF,
) -> dict[str, Any]:
    reconciliation = p37_public_reconciliation()
    reconciliation_verification = verify_reconciliation(reconciliation)
    registry_verification = verify_p35_registry_binding(registry_binding)
    registry_exact = (
        registry_verification["verdict"] == "PASS"
        and registry_binding.get("state") == "EXACT_BYTES_VERIFIED"
    )
    compiled_query = compile_multi_crystal_query(query)
    source_routing = route_source_events(source_events, cutoff=cutoff)
    repository_event_present = (
        source_routing["counts"]["repository_byte_events"] >= 1
    )
    edge = second_edge_experiment(
        prerequisites_pass=(
            reconciliation_verification["verdict"] == "PASS"
            and registry_exact
            and repository_event_present
        )
    )
    calibration = compile_outcome_calibration(outcomes, cutoff=cutoff)
    candidate_body = {
        "contract_digest": p38_contract()["contract_digest"],
        "reconciliation_digest": reconciliation["reconciliation_digest"],
        "registry_binding_digest": registry_binding.get("binding_digest"),
        "query_digest": compiled_query["query_digest"],
        "source_routing_digest": source_routing["routing_digest"],
        "edge_experiment_digest": edge["experiment_digest"],
        "calibration_digest": calibration["calibration_digest"],
    }
    candidate_root = content_address("kc144.p38.candidate-root", candidate_body)
    signers = dict(signer_registry or empty_signer_registry())
    ic10 = verify_ic10_returns(
        ic10_returns,
        signer_registry=signers,
        candidate_root=candidate_root,
        calibration=calibration,
        source_routing=source_routing,
        checked_at=cutoff,
    )
    payloads = (
        reconciliation,
        {
            "binding": registry_binding,
            "verification": registry_verification,
        },
        compiled_query,
        source_routing,
        edge,
        calibration,
        ic10,
    )
    lane_receipts = [
        _lane_receipt(lane, index, payload)
        for index, (lane, payload) in enumerate(zip(P38_LANES, payloads), 1)
    ]
    authorized = ic10["status"] == "AUTHORIZED"
    residuals: list[str] = []
    if not registry_exact:
        residuals.append("EXACT_P35_REGISTRY_NOT_LOCALLY_VERIFIED")
    if not repository_event_present:
        residuals.append("EXACT_REPOSITORY_BYTE_EVENT_MISSING")
    if calibration["status"] != "CALIBRATION_READY":
        residuals.append("HELD_OUT_OUTCOME_CORPUS_INSUFFICIENT")
    if not authorized:
        residuals.append("INDEPENDENT_IC10_RETURN_MISSING")
    if not edge["executed_in_proposal_graph"]:
        residuals.append("SECOND_PROPOSAL_EDGE_HELD")
    state = {
        "schema": "KC144.P38.StateDelta.V1",
        "candidate_root": candidate_root,
        "public_parent": PUBLIC_P36_RESULT_ID,
        "source_sibling": SOURCE_P37_RESULT_ID,
        "registry_exact": registry_exact,
        "registry_verification": registry_verification["verdict"],
        "query_crystals_routed": len(compiled_query["lanes"]),
        "repository_byte_events_admitted": source_routing["counts"][
            "repository_byte_events"
        ],
        "proposal_edges_executed_this_cycle": (
            1 if edge["executed_in_proposal_graph"] else 0
        ),
        "canonical_edges_executed_this_cycle": 0,
        "held_out_outcomes_admitted": calibration["census"]["accepted"],
        "weight_updates_executed": 0,
        "independent_ic10_returns": ic10["valid_independent_returns"],
        "production_mutated": False,
        "truth_effect": "NONE",
        "evidence_effect": "NONE",
        "authority_effect": (
            "SUCCESSOR_AUTHORIZATION" if authorized else "NONE"
        ),
        "global_release": "READY" if authorized else "HOLD",
        "residuals": sorted(residuals),
        "return": P38_ROUTE[-1],
        "next_seed": P38_NEXT_SEED,
    }
    state["delta_id"] = content_address("kc144.p38.state-delta", state)
    envelope_body = {
        "schema": "KC144.P38.Macrocycle.V1",
        "contract_digest": p38_contract()["contract_digest"],
        "reconciliation": reconciliation,
        "registry_binding": registry_binding,
        "compiled_query": compiled_query,
        "source_routing": source_routing,
        "second_edge": edge,
        "calibration": calibration,
        "signer_registry_digest": signers.get("registry_digest"),
        "ic10_evaluation": ic10,
        "lane_receipts": lane_receipts,
        "state": state,
    }
    return {
        **envelope_body,
        "envelope_digest": content_address("kc144.p38.macrocycle", envelope_body),
    }


def verify_p38_cycle(value: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    body = {key: item for key, item in value.items() if key != "envelope_digest"}
    if value.get("schema") != "KC144.P38.Macrocycle.V1":
        errors.append("E_SCHEMA")
    if value.get("envelope_digest") != content_address(
        "kc144.p38.macrocycle", body
    ):
        errors.append("E_ENVELOPE_DIGEST")
    receipts = value.get("lane_receipts", [])
    if len(receipts) != 7:
        errors.append("E_LANE_CENSUS")
    else:
        for index, (lane, receipt) in enumerate(zip(P38_LANES, receipts), 1):
            receipt_body = {
                key: item for key, item in receipt.items() if key != "receipt_id"
            }
            if (
                receipt.get("lane_id") != f"P38.L{index:02d}"
                or receipt.get("lane") != lane
                or receipt.get("receipt_id")
                != content_address("kc144.p38.lane-receipt", receipt_body)
            ):
                errors.append("E_LANE_RECEIPT")
    state = value.get("state", {})
    if (
        state.get("truth_effect") != "NONE"
        or state.get("production_mutated") is not False
        or state.get("canonical_edges_executed_this_cycle") != 0
        or state.get("weight_updates_executed") != 0
    ):
        errors.append("E_PROTECTED_STATE_ESCALATION")
    if state.get("global_release") == "READY" and (
        value.get("ic10_evaluation", {}).get("status") != "AUTHORIZED"
        or value.get("calibration", {}).get("status") != "CALIBRATION_READY"
    ):
        errors.append("E_RELEASE_WITHOUT_AUTHORITY")
    return {
        "schema": "KC144.P38.MacrocycleVerification.V1",
        "verdict": "PASS" if not errors else "FAIL",
        "errors": sorted(set(errors)),
        "envelope_digest": value.get("envelope_digest"),
    }


def compile_p38_release(
    output_directory: str | Path,
    *,
    implementation_commit: str,
    implementation_tree: str,
    registry_directory: str | Path | None = None,
    source_events: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    if not GIT_SHA_RE.fullmatch(implementation_commit):
        raise P38RuntimeError("implementation_commit must be a Git SHA")
    if not GIT_SHA_RE.fullmatch(implementation_tree):
        raise P38RuntimeError("implementation_tree must be a Git tree SHA")
    binding = (
        bind_exact_p35_registry(registry_directory)
        if registry_directory is not None
        else expected_p35_registry_binding()
    )
    public_source_events = [dict(event) for event in source_events]
    if any(
        event.get("source_class") != "REPOSITORY_BYTES"
        or event.get("consent", {}).get("publication_allowed") is not True
        for event in public_source_events
    ):
        raise P38RuntimeError(
            "release artifacts may persist only publication-consented "
            "repository-byte events"
        )
    query = {
        "schema": "KC144.P38.Query.V1",
        "goal": (
            "Observe the entire KC144 crystal simultaneously and maximize "
            "efficient expansion, compression, integration, navigation, "
            "source routing, mathematical transformation, and lawful return."
        ),
        "terms": [
            "parallel",
            "rotation",
            "transformation",
            "source",
            "outcome",
            "return",
        ],
        "crystals": list(P38_CRYSTALS),
        "source_surfaces": ["GOOGLE_DRIVE", "GITHUB", "LOCAL_ARTIFACT"],
    }
    cycle = compile_p38_cycle(
        query=query,
        registry_binding=binding,
        source_events=source_events,
        outcomes=[],
        signer_registry=empty_signer_registry(),
        ic10_returns=[],
    )
    verification = verify_p38_cycle(cycle)
    tensor = coordinate_tensor_144()
    contract = p38_contract()
    reconciliation = p37_public_reconciliation()
    source_capsule = source_p37_capsule()
    release_core = {
        "schema": "KC144.P38.Release.V1",
        "release_id": "KC144_P38_META_NAVIGATOR_V2_CANDIDATE_V1",
        "status": "CANDIDATE_HOLD",
        "implementation": {
            "repository": "demeet2k/guild-hall",
            "commit": implementation_commit,
            "tree": implementation_tree,
        },
        "public_parent": PUBLIC_P36_RESULT_ID,
        "source_sibling": SOURCE_P37_RESULT_ID,
        "reconciliation_digest": reconciliation["reconciliation_digest"],
        "source_capsule_digest": source_capsule["capsule_digest"],
        "contract_digest": contract["contract_digest"],
        "registry_binding_digest": binding["binding_digest"],
        "registry_binding_state": binding["state"],
        "coordinate_tensor_digest": tensor["tensor_digest"],
        "query_digest": cycle["compiled_query"]["query_digest"],
        "source_routing_digest": cycle["source_routing"]["routing_digest"],
        "second_edge_digest": cycle["second_edge"]["experiment_digest"],
        "calibration_digest": cycle["calibration"]["calibration_digest"],
        "envelope_digest": cycle["envelope_digest"],
        "verification_verdict": verification["verdict"],
        "proposal_edges_executed": cycle["state"][
            "proposal_edges_executed_this_cycle"
        ],
        "canonical_edges_executed": 0,
        "held_out_outcomes": 0,
        "independent_ic10_returns": 0,
        "production_authority": "HOLD",
        "truth_effect": "NONE",
        "next_seed": P38_NEXT_SEED,
    }
    release_digest = content_address("kc144.p38.release", release_core)
    release = {
        **release_core,
        "release_digest": release_digest,
        "result_id": "KC144.P38.CANDIDATE::"
        + release_digest.removeprefix("sha256:")[:24],
    }
    artifacts = {
        "p37_public_reconciliation_v1.json": reconciliation,
        "p37_source_sibling_capsule_v1.json": source_capsule,
        "p38_contract_v1.json": contract,
        "p35_exact_registry_binding_v1.json": binding,
        "p38_coordinate_tensor_144_v1.json": tensor,
        "p38_public_source_events_v1.json": public_source_events,
        "p38_macrocycle_v1.json": cycle,
        "p38_verification_v1.json": verification,
        "p38_release_v1.json": release,
    }
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in artifacts.items():
        (output / name).write_text(
            json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
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
