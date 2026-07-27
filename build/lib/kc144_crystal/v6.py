from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .population import digest
from .repair import (
    empty_repair_ledger,
    evidence_packet_contract,
    evidence_summary,
    repair_plan,
    verify_repair_ledger,
)
from .session import compile_session
from .v5 import compile_global_state, default_session_spec


def compile_repair_state(
    ledger: Mapping[str, Any],
    *,
    base_global_state: Mapping[str, Any],
) -> dict[str, Any]:
    summary = evidence_summary(ledger)
    effective = summary["production_effective_state"]
    session = compile_session(
        default_session_spec(),
        certified_bridges=effective["certified_bridges"],
        independent_replays=effective["independent_replays"],
        domain_population=effective["domain_population"],
        blocking_defects=effective["blocking_defects"],
        ic10_promoted=effective["ic10_promoted"],
    )
    solid = session["observatory"]["M12_SOLID_STATE"]
    production_certified = (
        ledger["namespace"] == "PRODUCTION" and solid["verdict"] == "CERTIFIED"
    )
    body = {
        "schema": "KC144.M12RepairState.V6",
        "release": "KC144.M12.REPAIR.COMPILER.V6",
        "parent_release": "KC144.SSN12.GLOBAL_STATE.V5",
        "frozen_base_state_root": ledger["frozen_base"]["state_root"],
        "base_global_state_digest": base_global_state["global_state_digest"],
        "ledger_digest": ledger["ledger_digest"],
        "ledger_integrity": verify_repair_ledger(ledger),
        "evidence": summary,
        "repair_plan": repair_plan(ledger),
        "ssn12": solid,
        "production_certificate_issued": production_certified,
        "truth_effect": (
            "AUTHORIZED_SUCCESSOR_ONLY"
            if production_certified
            else "NONE"
        ),
        "next_seed": (
            "KC144.V2::POPULATE_MATH144"
            if production_certified
            else "KC144.V6::EVIDENCE-INTAKE::PARALLEL-WAVE-01"
        ),
        "successor_law": (
            "KC144.V2::POPULATE_MATH144 is emitted only from a PRODUCTION ledger "
            "whose 28 bridge, 144 domain, 144 independent replay, zero-defect, "
            "and sole-authority IC10 gates all pass"
        ),
    }
    return {**body, "repair_state_digest": digest(body)}


def compile_repair_framework(
    output_directory: str | Path,
    *,
    ledger: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    v5_release = compile_global_state(output)
    base_global_state = json.loads(
        (output / "global_state_v5.json").read_text(encoding="utf-8")
    )
    repair_ledger = (
        dict(ledger)
        if ledger is not None
        else empty_repair_ledger(
            namespace="PRODUCTION",
            base_state_root=base_global_state["global_state_digest"],
        )
    )
    documents = {
        "m12_evidence_contract_v6.json": evidence_packet_contract(),
        "m12_repair_ledger_v6.json": repair_ledger,
        "m12_repair_plan_v6.json": repair_plan(repair_ledger),
        "m12_repair_state_v6.json": compile_repair_state(
            repair_ledger,
            base_global_state=base_global_state,
        ),
    }
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    state = documents["m12_repair_state_v6.json"]
    release_body = {
        "schema": "KC144.M12RepairRelease.V6",
        "release": "KC144.M12.REPAIR.COMPILER.V6",
        "parent_release": v5_release["release"],
        "verdict": (
            "PASS"
            if (
                v5_release["verdict"] == "PASS"
                and state["ledger_integrity"]["verdict"] == "PASS"
                and state["ssn12"]["verdict"] in {"HOLD", "CERTIFIED"}
                and not state["repair_plan"]["frozen_crystal_mutated"]
            )
            else "FAIL"
        ),
        "operational_status": state["ssn12"]["verdict"],
        "production_packets_admitted": len(repair_ledger["records"]),
        "production_certificate_issued": state["production_certificate_issued"],
        "open_gates": [
            gate
            for gate, verdict in state["ssn12"]["gates"].items()
            if verdict != "PASS"
        ],
        "next_frontier": state["repair_plan"]["next_frontier"],
        "next_seed": state["next_seed"],
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
    }
    release = {
        **release_body,
        "release_digest": digest(release_body),
    }
    (output / "m12_repair_release_v6.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
