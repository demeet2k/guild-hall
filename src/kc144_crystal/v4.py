from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .agent_receipts import agent_run_receipt_contract
from .query import QueryBundle, compile_query, query_contract
from .systematic import compile_systematic_framework, frontier_ledger
from .tool_registry import locate_mycelium_tool
from .witness import bridge_witness_contract


def default_query_bundles() -> tuple[QueryBundle, ...]:
    return (
        QueryBundle(
            query_id="KC144.V4.EXAMPLE.RETURNABLE",
            goal="compile an activation route through return and adjudication",
            terms=("activation", "return", "adjudication"),
            operators=("RETURN",),
            invariants=("return",),
            start_coordinates=(6,),
            route_budget=18,
            return_mode="RETURN_ARM",
        ),
        QueryBundle(
            query_id="KC144.V4.EXAMPLE.SOURCE-CARRIER",
            goal="locate a source declared carrier with identity and evidence",
            terms=("carrier", "identity", "source"),
            domains=("F37",),
            evidence_floor="SOURCE_DECLARED",
            start_coordinates=(6,),
            route_budget=18,
            return_mode="TYPED_RETRACE",
        ),
        QueryBundle(
            query_id="KC144.V4.EXAMPLE.INDEPENDENT-REFUSAL",
            goal="locate independently replayed stations",
            terms=("replay",),
            evidence_floor="INDEPENDENT_REPLAY",
            start_coordinates=(6,),
            route_budget=18,
            return_mode="NONE",
        ),
    )


def compile_mycelium_framework(output_directory: str | Path) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    v3_release = compile_systematic_framework(output)
    query_reports = [compile_query(bundle) for bundle in default_query_bundles()]
    documents = {
        "query_contract.json": query_contract(),
        "compiled_queries.json": {
            "schema": "KC144.CompiledQuerySet.V4",
            "queries": query_reports,
        },
        "bridge_witness_contract.json": bridge_witness_contract(),
        "bridge_witness_ledger.json": {
            "schema": "KC144.BridgeWitnessLedger.V4",
            "production_packets": [],
            "certified_bridge_ids": [],
            "certified_transport_count": 0,
            "declared_transport_open": 28,
            "promotion_effect": "NONE",
        },
        "agent_run_receipt_contract.json": agent_run_receipt_contract(),
        "agent_run_receipt_location.json": locate_mycelium_tool(
            "KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS",
            start_coordinates=(6,),
            route_budget=18,
        ),
        "tool_dispatch_location.json": locate_mycelium_tool(
            "KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH",
            start_coordinates=(6,),
            route_budget=18,
        ),
        "p31_live_navigate_location.json": locate_mycelium_tool(
            "KC144.P31::LIVE_COGNITION_NAVIGATE",
            start_coordinates=(6,),
            route_budget=18,
        ),
        "frontier_v4.json": {
            **frontier_ledger(),
            "schema": "KC144.SystematicFrontier.V4",
            "next_seed": "KC144.V4::MYCELIUM-PASS-003::QUERY_ROUTE_RETURN_COMPILER",
            "new_runtime_capability": (
                "H06 QueryBundle -> evidence-filtered Pareto attractors -> typed route "
                "-> bridge exposure -> return plan"
            ),
        },
    }
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    release = {
        "schema": "KC144.MyceliumRelease.V4",
        "release": "KC144.MYCELIUM.FRAMEWORK.V4",
        "verdict": (
            "PASS"
            if (
                v3_release["verdict"] == "PASS"
                and query_reports[0]["status"] == "COMPILED"
                and query_reports[1]["status"] == "COMPILED"
                and query_reports[2]["status"] == "REFUSED"
                and query_reports[2]["refusal"]["code"]
                == "EVIDENCE_FLOOR_UNSATISFIED"
            )
            else "FAIL"
        ),
        "base_release": v3_release["release"],
        "query_runtime": {
            "contract": "H06_QUERY_BUNDLE",
            "ranking": "PARETO_NONSCALAR",
            "graph_mutation": False,
            "truth_effect": "NONE",
        },
        "bridge_runtime": {
            "declared": 28,
            "certified": 0,
            "admission_gate": "EXECUTABLE",
        },
        "tool_runtime": {
            "lookup_key": (
                "KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS"
            ),
            "location_status": documents[
                "agent_run_receipt_location.json"
            ]["status"],
            "coordinate_routes": len(
                documents["agent_run_receipt_location.json"][
                    "coordinate_routes"
                ]
            ),
            "base_graph_mutated": False,
            "truth_effect": "NONE",
        },
        "dispatch_runtime": {
            "lookup_key": "KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH",
            "location_status": documents["tool_dispatch_location.json"][
                "status"
            ],
            "registered_execution": "STATIC_IN_PROCESS_HANDLER_ALLOWLIST_ONLY",
            "p31_binding": "LOCATOR_ONLY_EXTERNAL_RUNTIME_REQUIRED",
            "base_graph_mutated": False,
            "truth_effect": "NONE",
        },
        "actual_live_promotions": 0,
        "solid_state": "HOLD",
        "added_artifacts": sorted(documents),
    }
    (output / "mycelium_release.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
