from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .audit import audit_crystal
from .holonomy import measure_holonomy, replay_ablation
from .navigation import DECLARED_BRIDGES, bridge_registry, navigation_report
from .population import crystallize
from .station import station_population_report
from .tool_registry import mycelium_tool_registry
from .wave import WaveQuery, propagate


def frontier_ledger() -> dict[str, Any]:
    crystal = crystallize()
    residual_gids = [row["gid"] for row in crystal["residuals"]]
    return {
        "schema": "KC144.SystematicFrontier.V3",
        "status": "FRAMEWORK_COMPLETE_LIVE_OBLIGATIONS_OPEN",
        "obligations": [
            {
                "id": "FRT-I09-DOCUMENTED",
                "count": 86,
                "action": "independent replay of each source-documented station",
                "cannot_self_supply": True,
            },
            {
                "id": "FRT-I09-GENERATOR",
                "count": 1,
                "action": "independent cold replay of the complete generator",
                "cannot_self_supply": True,
            },
            {
                "id": "FRT-DOMAIN",
                "count": 58,
                "action": "bind source-domain residents without converting structure into evidence",
                "explicit_F37_residuals": residual_gids,
            },
            {
                "id": "FRT-BRIDGES",
                "count": len(DECLARED_BRIDGES),
                "action": "replace declared connectivity with beta-tuple transport witnesses",
            },
            {
                "id": "FRT-FEDERATION",
                "count": 12,
                "action": "pin live repository commits and publish prepared contracts",
            },
            {
                "id": "FRT-SOLID",
                "count": 1,
                "action": "issue M12 only after live coverage, returnability, and authority checks",
            },
        ],
        "next_seed": "KC144.V3::NAV-PASS-002::ATTRACTOR_QUERY_OVERLAY",
        "promotion_effect": "NONE",
    }


def compile_systematic_framework(output_directory: str | Path) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    artifacts = {
        "crystal.json": crystallize(),
        "crystal_audit.json": audit_crystal(),
        "station_bodies.json": station_population_report(),
        "navigation.json": navigation_report(),
        "declared_bridges.json": bridge_registry(),
        "holonomy.json": measure_holonomy(),
        "replay_ablation.json": replay_ablation(),
        "wave_h06.json": propagate(
            WaveQuery("KC144.V3.DEFAULT.H06", starts=(6,), route_budget=18)
        ),
        "tool_registry_v1.json": mycelium_tool_registry(),
        "frontier.json": frontier_ledger(),
    }
    for filename, document in artifacts.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    release = {
        "schema": "KC144.SystematicRelease.V3",
        "release": "KC144.SYSTEMATIC.FRAMEWORK.V3",
        "verdict": "PASS"
        if all(
            (
                artifacts["crystal_audit.json"]["verdict"] == "PASS",
                artifacts["navigation.json"]["components"] == 1,
                artifacts["navigation.json"]["return_arm"]["verdict"] == "PASS",
                artifacts["holonomy.json"]["all_paths_valid"],
                artifacts["holonomy.json"]["all_pairwise_holonomy_nonzero"],
                artifacts["wave_h06.json"]["reached"] == 144,
            )
        )
        else "FAIL",
        "structural_population": "144/144",
        "source_domain_population": "86/144",
        "navigation": {
            "components": artifacts["navigation.json"]["components"],
            "diameter": artifacts["navigation.json"]["diameter"],
            "radius": artifacts["navigation.json"]["radius"],
            "center": artifacts["navigation.json"]["centers"],
            "reachable_from_H06": artifacts["navigation.json"]["reachable_from_H06"],
            "max_hops_from_H06": artifacts["navigation.json"]["max_hops_from_H06"],
            "distinct_intra_adjacency_edges": artifacts["navigation.json"][
                "distinct_intra_adjacency_edges"
            ],
            "declared_bridge_records": artifacts["navigation.json"][
                "declared_bridge_records"
            ],
            "distinct_adjacency_edges": artifacts["navigation.json"][
                "distinct_adjacency_edges"
            ],
        },
        "holonomy": {
            "routes": len(artifacts["holonomy.json"]["routes"]),
            "common_carry": artifacts["holonomy.json"]["shared_carry_all_routes"],
            "all_pairwise_nonzero": artifacts["holonomy.json"][
                "all_pairwise_holonomy_nonzero"
            ],
        },
        "navigation_wave": {
            "seed": "H06",
            "coverage": artifacts["wave_h06.json"]["coverage"],
            "base_graph_mutated": artifacts["wave_h06.json"]["base_graph_mutated"],
            "truth_effect": "NONE",
        },
        "mycelium_tools": {
            "registered": len(
                artifacts["tool_registry_v1.json"]["descriptors"]
            ),
            "lookup_keys": sorted(
                artifacts["tool_registry_v1.json"]["descriptors"]
            ),
            "registry_digest": artifacts["tool_registry_v1.json"][
                "registry_digest"
            ],
            "base_graph_mutated": False,
            "truth_effect": "NONE",
        },
        "actual_live_promotions": 0,
        "solid_state": "HOLD",
        "nonclaims": [
            "declared bridge connectivity is not transport certification",
            "the replay ablation is not an independent live replay",
            "the wave overlay does not mutate evidence or truth standing",
            "no external federation was published",
            "no solid-state certificate was issued",
        ],
        "artifacts": sorted(artifacts),
    }
    (output / "systematic_release.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
