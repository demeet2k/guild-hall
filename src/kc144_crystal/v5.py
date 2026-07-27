from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .bridge2pc import empty_production_bridge_commit_ledger
from .edge_manifest import freeze_edge_manifest
from .population import crystallize, digest
from .session import SessionSpec, cold_reconstruct, compile_session
from .v4 import compile_mycelium_framework, default_query_bundles


def default_session_spec() -> SessionSpec:
    return SessionSpec(
        session_id="KC144.V5.DEFAULT.CONSTELLATION",
        epoch="EPOCH-B/V5",
        queries=default_query_bundles(),
    )


def compile_global_state(output_directory: str | Path) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    v4_release = compile_mycelium_framework(output)
    manifest = freeze_edge_manifest()
    session = compile_session(default_session_spec())
    reconstruction = cold_reconstruct(session["reentry_seed"])
    bridge_commits = empty_production_bridge_commit_ledger()
    documents = {
        "edge_manifest_v5.json": manifest,
        "traversal_session_v5.json": session,
        "reentry_seed_v5.json": session["reentry_seed"],
        "cold_reconstruction_v5.json": reconstruction,
        "bridge_commit_ledger_v5.json": bridge_commits,
    }
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    global_body = {
        "schema": "KC144.GlobalState.V5",
        "release": "KC144.SSN12.GLOBAL_STATE.V5",
        "base_release": v4_release["release"],
        "crystal_digest": crystallize()["digest"],
        "edge_manifest_digest": manifest["manifest_digest"],
        "session_digest": session["session_digest"],
        "receipt_root": session["receipt_root"],
        "reentry_seed_digest": session["reentry_seed"]["seed_digest"],
        "cold_reconstruction": reconstruction["verdict"],
        "replay_level": reconstruction["replay_level"],
        "independent_replay": False,
        "ssn12": session["observatory"]["M12_SOLID_STATE"],
        "production_bridge_commits": bridge_commits["committed"],
        "actual_live_promotions": 0,
        "truth_effect": "NONE",
        "next_seed": (
            "KC144.V2::POPULATE_MATH144"
            if session["observatory"]["M12_SOLID_STATE"]["verdict"] == "CERTIFIED"
            else "KC144.V5::REPAIR-SEED::M12-OPEN-GATES"
        ),
    }
    global_state = {**global_body, "global_state_digest": digest(global_body)}
    (output / "global_state_v5.json").write_text(
        json.dumps(global_state, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    release = {
        "schema": "KC144.GlobalStateRelease.V5",
        "release": "KC144.SSN12.GLOBAL_STATE.V5",
        "verdict": (
            "PASS"
            if (
                v4_release["verdict"] == "PASS"
                and manifest["status"] == "FROZEN"
                and reconstruction["verdict"] == "PASS"
                and global_state["ssn12"]["verdict"] == "HOLD"
                and bridge_commits["committed"] == 0
            )
            else "FAIL"
        ),
        "edge_manifest": {
            "records": manifest["relation_record_count"],
            "distinct_adjacencies": manifest["distinct_adjacency_count"],
            "all_carry_loss_declared": (
                manifest["all_edges_declare_carry"]
                and manifest["all_edges_declare_loss"]
            ),
        },
        "session": {
            "queries": len(default_session_spec().queries),
            "receipts": len(session["receipts"]),
            "receipt_chain": "PASS",
            "projective_synapses": len(
                session["observatory"]["M10_PROJECTIVE_SYNAPSE_MAP"]
            ),
        },
        "cold_reconstruction": reconstruction["replay_level"],
        "independent_replay": False,
        "solid_state": global_state["ssn12"]["verdict"],
        "actual_live_promotions": 0,
        "added_artifacts": sorted([*documents, "global_state_v5.json"]),
    }
    (output / "global_state_release_v5.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
