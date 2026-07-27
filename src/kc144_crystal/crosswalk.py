from __future__ import annotations

from collections import Counter
from typing import Any

from .lattice import K4, generate_seats
from .navigation import navigation_relations
from .population import crystallize, digest


ACTIVE_EPOCH_ID = "EPOCH-B-EIGHT-BLOCK"
ACTIVE_EPOCH_CENSUS = "6+16+21+37+10+15+27+12"
GRAPH_SLICE_MODES = {
    "X16_SCHEDULE": "schedule",
    "X16_ALGEBRA": "algebra",
    "X16_MULTIPLEX": "both",
}


def _support_from_mask(mask: str) -> tuple[str, ...]:
    if len(mask) != len(K4) or set(mask) - {"0", "1"}:
        raise ValueError(f"invalid KC15 support mask: {mask}")
    return tuple(pole for pole, bit in zip(K4, mask) if bit == "1")


def _graph_slice(slice_id: str, mode: str) -> dict[str, Any]:
    relations = navigation_relations(mode)
    distinct_pairs = {
        tuple(sorted((row["source"], row["target"]))) for row in relations
    }
    structural = sum(row["standing"] == "STRUCTURAL" for row in relations)
    declared = sum(row["standing"] == "DECLARED_UNCERTIFIED" for row in relations)
    body = {
        "slice_id": slice_id,
        "x16_reading": mode,
        "relation_record_count": len(relations),
        "structural_relation_records": structural,
        "declared_bridge_records": declared,
        "distinct_adjacency_count": len(distinct_pairs),
        "relation_census": dict(Counter(row["relation"] for row in relations)),
        "records_digest": digest(list(relations)),
        "truth_effect": "NONE",
    }
    return {**body, "slice_digest": digest(body)}


def graph_slice_registry() -> dict[str, Any]:
    slices = [
        _graph_slice(slice_id, mode)
        for slice_id, mode in GRAPH_SLICE_MODES.items()
    ]
    body = {
        "schema": "KC144.GraphSliceRegistry.V7",
        "active_frozen_slice": "X16_ALGEBRA",
        "maximum_union_slice": "X16_MULTIPLEX",
        "slices": slices,
        "laws": [
            "schedule and algebra relations are typed and never silently merged",
            "an evidence envelope binds exactly one named graph slice",
            "multiplex coverage is an overlay until a successor migration promotes it",
        ],
    }
    return {**body, "registry_digest": digest(body)}


def compile_coordinate_crosswalk() -> dict[str, Any]:
    runtime = {seat.gid: seat for seat in generate_seats()}
    atlas = {row["gid"]: row for row in crystallize()["seats"]}

    canonical_by_support: dict[tuple[str, ...], int] = {}
    for gid in range(91, 106):
        label = atlas[gid]["architectural_label"]
        mask = label.rsplit(" ", 1)[-1]
        canonical_by_support[_support_from_mask(mask)] = gid

    kc15 = []
    for runtime_gid in range(91, 106):
        support = tuple(runtime[runtime_gid].coordinates["support"])
        canonical_gid = canonical_by_support[support]
        kc15.append(
            {
                "runtime_gid": runtime_gid,
                "canonical_gid": canonical_gid,
                "support": list(support),
                "runtime_station": runtime[runtime_gid].station,
                "canonical_label": atlas[canonical_gid]["architectural_label"],
                "relation": (
                    "IDENTITY"
                    if runtime_gid == canonical_gid
                    else "TYPED_PERMUTATION"
                ),
            }
        )

    kc27 = []
    for gid in range(106, 133):
        x, y, z = runtime[gid].coordinates["coord"]
        p = gid - 106
        canonical = [p // 9, (p % 9) // 3, p % 3]
        transformed = [z + 1, y + 1, x + 1]
        kc27.append(
            {
                "gid": gid,
                "station": runtime[gid].station,
                "runtime_xyz": [x, y, z],
                "canonical_abc": canonical,
                "transform": "(a,b,c)=(z+1,y+1,x+1)",
                "exact": transformed == canonical,
                "canonical_label": atlas[gid]["architectural_label"],
            }
        )

    ssn12 = [
        {
            "gid": gid,
            "station": runtime[gid].station,
            "runtime_instrument_role": runtime[gid].structural_role,
            "canonical_registry_role": atlas[gid]["architectural_label"],
            "relation": "RUNTIME_INSTRUMENT_PROJECTS_TO_CANONICAL_REGISTRY",
            "overwrite_allowed": False,
        }
        for gid in range(133, 145)
    ]

    f37_branches = [
        {
            "gid": 63,
            "station": "F20",
            "canonical_label": atlas[63]["architectural_label"],
            "preserved_branches": [
                "Berger holonomy / G2 reduced transport",
                "Fisher Information",
            ],
            "status": "CONTESTED",
        },
        {
            "gid": 70,
            "station": "F27",
            "canonical_label": atlas[70]["architectural_label"],
            "preserved_branches": [
                "Dijkgraaf-Witten finite gauge envelope",
                "Meta-Liminal Tower",
            ],
            "status": "CONTESTED_COMPOSITE",
        },
        {
            "gid": 73,
            "station": "F30",
            "canonical_label": atlas[73]["architectural_label"],
            "preserved_branches": [
                "moonshine as carrier identity",
                "moonshine as supported property",
            ],
            "status": "UNRESOLVED_SOURCE_ROLE",
        },
    ]

    body = {
        "schema": "KC144.ActiveEpochCrosswalk.V7",
        "epoch_id": ACTIVE_EPOCH_ID,
        "epoch_census": ACTIVE_EPOCH_CENSUS,
        "kc15": {
            "runtime_view": "CARDINALITY_GRADED",
            "canonical_view": "BINARY_LSB_FIRST",
            "entries": kc15,
            "bijection": (
                len({row["runtime_gid"] for row in kc15}) == 15
                and len({row["canonical_gid"] for row in kc15}) == 15
            ),
            "relocated": sum(
                row["runtime_gid"] != row["canonical_gid"] for row in kc15
            ),
        },
        "kc27": {
            "runtime_view": "SIGNED_XYZ",
            "canonical_view": "TERNARY_ABC",
            "entries": kc27,
            "exact": all(row["exact"] for row in kc27),
        },
        "ssn12": {
            "relation": "PAIRED_ROLE_VIEWS",
            "entries": ssn12,
            "collapse_forbidden": True,
        },
        "f37_branch_ledger": {
            "entries": f37_branches,
            "latest_wins_forbidden": True,
        },
        "laws": [
            "a crosswalk transports identity but does not promote content",
            "runtime and canonical views remain addressable after translation",
            "conflicted carrier branches survive until a signed adjudication",
            "the frozen V6 crystal is not mutated",
        ],
    }
    return {**body, "crosswalk_digest": digest(body)}


def domain_binding_for_subject(subject_id: str) -> dict[str, Any]:
    if not subject_id.startswith("GID") or not subject_id[3:].isdigit():
        raise ValueError(f"invalid domain subject: {subject_id}")
    gid = int(subject_id[3:])
    crosswalk = compile_coordinate_crosswalk()

    if 55 <= gid <= 79:
        branch_by_gid = {
            row["gid"]: row
            for row in crosswalk["f37_branch_ledger"]["entries"]
        }
        atlas = {row["gid"]: row for row in crystallize()["seats"]}
        branch = branch_by_gid.get(gid)
        return {
            "view": "F37_CANONICAL",
            "canonical_gid": gid,
            "canonical_label": atlas[gid]["architectural_label"],
            "adjudication_required": branch is not None,
            "preserved_status": (
                branch["status"] if branch is not None else "UNCONTESTED"
            ),
        }

    if 91 <= gid <= 105:
        row = next(
            entry
            for entry in crosswalk["kc15"]["entries"]
            if entry["canonical_gid"] == gid
        )
        return {
            "view": "KC15_CANONICAL_BINARY",
            "canonical_gid": gid,
            "runtime_gid": row["runtime_gid"],
            "support": row["support"],
        }

    if 106 <= gid <= 132:
        row = next(
            entry
            for entry in crosswalk["kc27"]["entries"]
            if entry["gid"] == gid
        )
        return {
            "view": "KC27_CANONICAL_ABC",
            "canonical_gid": gid,
            "canonical_abc": row["canonical_abc"],
            "runtime_xyz": row["runtime_xyz"],
        }

    if 133 <= gid <= 144:
        row = next(
            entry
            for entry in crosswalk["ssn12"]["entries"]
            if entry["gid"] == gid
        )
        return {
            "view": "SSN_PAIRED_ROLE_VIEW",
            "canonical_gid": gid,
            "canonical_registry_role": row["canonical_registry_role"],
            "runtime_instrument_role": row["runtime_instrument_role"],
        }

    raise ValueError(f"no V7 domain coordinate binding for {subject_id}")
