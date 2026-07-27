from __future__ import annotations

from collections import defaultdict
from typing import Any

from .lattice import K4, generate_edges
from .population import crystallize, digest
from .transform import br_mirror, kc27_transform

H6_QUESTIONS = (
    "Which exact seat and identity is this?",
    "Which domain body occupies which seat?",
    "Which typed routes exist, and where do they return?",
    "Which invariants, bridges, and defects hold?",
    "Which sources exist, with what evidence and version?",
    "How does a session activate, replay, and reseed?",
)

X16_QUESTIONS = {
    ("11", "SQ"): "What exactly is retained before anything acts upon it?",
    ("11", "FL"): "How is the retained object generated?",
    ("11", "CL"): "What competing candidates could the retained object be?",
    ("11", "FR"): "How does the retained object reproduce itself across depth?",
    ("10", "SQ"): "What exactly is the operator, with domain, codomain, and effects?",
    ("10", "FL"): "How is the operator executed with receipts?",
    ("10", "CL"): "What branch field does the operator produce?",
    ("10", "FR"): "How do operators compose across depth or scale?",
    ("00", "SQ"): "Which kind of zero is this, on which carrier?",
    ("00", "FL"): "How is the invariant enforced, transported, and repaired?",
    ("00", "CL"): "What defects and obstructions are present, and where?",
    ("00", "FR"): "Does invariance survive the change of scale?",
    ("01", "SQ"): "What return is owed, and of which class?",
    ("01", "FL"): "How is the return actually performed?",
    ("01", "CL"): "Which antecedents remain admissible?",
    ("01", "FR"): "What minimal seed reconstructs this region to declared fidelity?",
}

BR21_QUESTIONS = {
    ("ADMIT", "PLUS"): "What exact body is materialized from the admitted request?",
    ("ADMIT", "HINGE"): "Are request, sources, policy, and carrier jointly admissible?",
    ("ADMIT", "STAR"): "How could this admission be wrong, and what would refute it?",
    ("EXPAND", "PLUS"): "What children does the body lawfully generate?",
    ("EXPAND", "HINGE"): "Where do the children overlap, and at what typed cost?",
    ("EXPAND", "STAR"): "What did the expansion fail to cover?",
    ("NAVIGATE", "PLUS"): "What ordered, typed, witnessed path reaches the target?",
    ("NAVIGATE", "HINGE"): "Which routes remain jointly active, and do they commute?",
    ("NAVIGATE", "STAR"): "Is the traversed path auditable and reversible?",
    ("TRANSFORM", "PLUS"): "What changed, and what was preserved?",
    ("TRANSFORM", "HINGE"): "Which invariants survive transport between carriers?",
    ("TRANSFORM", "STAR"): "Of which return type is this transform capable?",
    ("TEST", "PLUS"): "Does the claim pass, inside which corridor?",
    ("TEST", "HINGE"): "Are the constructive and conjugate results compatible?",
    ("TEST", "STAR"): "Can a lawful falsification be compiled against this claim?",
    ("COMPRESS", "PLUS"): "What macrostate plus carry reconstructs the body?",
    ("COMPRESS", "HINGE"): "What is shared, and what must stay in per-branch carry?",
    ("COMPRESS", "STAR"): "What did compression lose, and is the loss certified?",
    ("RETURN", "PLUS"): "What certified successor was produced?",
    ("RETURN", "HINGE"): "Can the process be restarted, not merely remembered?",
    ("RETURN", "STAR"): "Can the circuit be reversed, compensated, or proven irreversible?",
}

IC10_QUESTIONS = (
    "Is the object exactly identified and sourced?",
    "Is its form canonical and its raw identity preserved?",
    "Is every object typed with carrier and units?",
    "Is the validity corridor declared and testable?",
    "Is each invariant preserved under a declared transport?",
    "Is the evidence class sufficient and lawful?",
    "Are all dependencies resolved and unrevoked?",
    "Are transport loss and return behaviour declared?",
    "Can an independent process reproduce the result?",
    "May this exact candidate become an authoritative successor?",
)

SSN12_QUESTIONS = (
    "What state is each node in?",
    "What state is each edge in?",
    "Which frontier activates next?",
    "What lives between two nodes?",
    "How dense is the coupling?",
    "Which nodes co-activate?",
    "Where is the commitment boundary?",
    "What was healed, and what gap remains?",
    "What exact path produced this?",
    "Which projective synapses exist?",
    "What fraction of the crystal is covered and returnable?",
    "May a solid-state certificate be issued?",
)

BAND_INVARIANTS = {
    "H6": "registry authority is not content authority",
    "X16": "pole and lens roles do not migrate; the four-pole cycle closes",
    "BR21": "PLUS, HINGE, and STAR are projections of one computation",
    "F37": "carrier legality is not transport legality; bridges require a full beta tuple",
    "IC10": "gates are conjunctive and ordered; nine gates do not authorize I10",
    "KC15": "a support mask records support, never probability or truth",
    "KC27": "topological adjacency does not imply a lawful semantic route",
    "SSN12": "telemetry measures and records; it never promotes",
}

RETURN_BY_POLE = {
    "11": "BRANCH_PRESERVING_ANTECEDENT_SET",
    "10": "PARTIAL_INVERSE",
    "00": "COMPENSATING_RETURN",
    "01": "EXACT_INVERSE",
}


def _question(row: dict[str, Any]) -> str:
    band = row["band"]
    coord = row["coordinates"]
    if band == "H6":
        return H6_QUESTIONS[coord["index"] - 1]
    if band == "X16":
        return X16_QUESTIONS[(coord["pole"], coord["lens"])]
    if band == "BR21":
        return BR21_QUESTIONS[(coord["family"], coord["lens"])]
    if band == "F37":
        if row["evidence_status"] == "DOCUMENTED":
            return f"What are (P, iota, Lambda, boundary, N) for carrier {row['station']}?"
        return f"What source-bound domain object, if any, lawfully occupies {row['station']}?"
    if band == "IC10":
        return IC10_QUESTIONS[coord["index"] - 1]
    if band == "KC15":
        support = coord["support"]
        absent = [pole for pole in K4 if pole not in support]
        return (
            f"What is expressible with support {{{','.join(support)}}}, and what remains "
            f"inexpressible without {{{','.join(absent)}}}?"
        )
    if band == "KC27":
        x, y, z = coord["coord"]
        if (x, y, z) == (0, 0, 0):
            return "Which admissible branch becomes the compressed successor?"
        return f"What does simultaneous displacement at ({x},{y},{z}) produce and preserve?"
    return SSN12_QUESTIONS[coord["index"] - 1]


def _four_pole(row: dict[str, Any]) -> dict[str, str]:
    return {
        "11": f"body admitted at {row['station']}",
        "10": f"operation performed or exposed by {row['station']}",
        "00": f"invariant and defect boundary of {row['station']}",
        "01": f"typed return and successor obligation of {row['station']}",
    }


def _route_index() -> dict[int, list[dict[str, Any]]]:
    routes: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for edge in generate_edges("both"):
        for source, target in ((edge.source, edge.target), (edge.target, edge.source)):
            routes[source].append(
                {
                    "to_gid": target,
                    "relation": edge.edge_class,
                    "semantics": edge.semantics,
                    "standing": "STRUCTURAL",
                }
            )
    for gid in range(23, 44):
        target = br_mirror(gid).target_gid
        if target != gid:
            routes[gid].append(
                {
                    "to_gid": target,
                    "relation": "BR21_MIRROR",
                    "semantics": "conjugate operator view",
                    "standing": "STRUCTURAL",
                }
            )
    for gid in range(106, 133):
        target = kc27_transform(gid, signs=(-1, -1, -1)).target_gid
        if target != gid:
            routes[gid].append(
                {
                    "to_gid": target,
                    "relation": "KC27_J",
                    "semantics": "signed-inversion mirror",
                    "standing": "STRUCTURAL",
                }
            )
    for route_list in routes.values():
        route_list.sort(key=lambda route: (route["to_gid"], route["relation"]))
    return routes


def build_station_bodies() -> tuple[dict[str, Any], ...]:
    crystal = crystallize()
    routes = _route_index()
    bodies: list[dict[str, Any]] = []
    for row in crystal["seats"]:
        domain_state = {
            "DOCUMENTED": "SOURCE_DECLARED",
            "DERIVED": "GENERATOR_ONLY",
            "ROUTED_ONLY": "ROUTE_ONLY",
            "UNMAPPED": "UNMAPPED",
        }[row["evidence_status"]]
        body: dict[str, Any] = {
            "gid": row["gid"],
            "grid": row["grid"],
            "band": row["band"],
            "station": row["station"],
            "architectural_label": row["architectural_label"],
            "structural_role": row["structural_role"],
            "evidence_status": row["evidence_status"],
            "domain_state": domain_state,
            "governing_question": _question(row),
            "four_pole": _four_pole(row),
            "native_routes": routes[row["gid"]],
            "band_invariant": BAND_INVARIANTS[row["band"]],
            "return_obligation": RETURN_BY_POLE.get(
                row["coordinates"].get("pole"), "TYPED_RETURN_REQUIRED"
            ),
            "promotion_effect": "NONE",
        }
        body["raw_cid"] = digest(body)
        bodies.append(body)
    return tuple(bodies)


def station_population_report() -> dict[str, Any]:
    bodies = build_station_bodies()
    source_declared = sum(body["domain_state"] == "SOURCE_DECLARED" for body in bodies)
    return {
        "schema": "KC144.StationPopulation.V3",
        "structural_population": f"{len(bodies)}/144",
        "source_domain_population": f"{source_declared}/144",
        "domain_open": 144 - source_declared,
        "all_cids_present": all(body["raw_cid"] for body in bodies),
        "all_questions_present": all(body["governing_question"] for body in bodies),
        "all_four_poles_present": all(set(body["four_pole"]) == set(K4) for body in bodies),
        "bodies": list(bodies),
    }
