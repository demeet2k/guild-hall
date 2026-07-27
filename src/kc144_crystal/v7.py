from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .crosswalk import (
    ACTIVE_EPOCH_CENSUS,
    ACTIVE_EPOCH_ID,
    compile_coordinate_crosswalk,
    domain_binding_for_subject,
    graph_slice_registry,
)
from .evidence_v7 import (
    SignedEvidenceEnvelope,
    authority_registry_integrity,
    empty_authority_registry,
    production_evidence_contract,
    verify_signed_envelope,
)
from .population import digest
from .repair import evidence_packet_contract
from .v6 import compile_repair_framework


def compile_production_evidence_kernel(
    output_directory: str | Path,
    *,
    ledger: Mapping[str, Any] | None = None,
    authority_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    v6_release = compile_repair_framework(output, ledger=ledger)
    v6_state = json.loads(
        (output / "m12_repair_state_v6.json").read_text(encoding="utf-8")
    )
    crosswalk = compile_coordinate_crosswalk()
    graph_registry = graph_slice_registry()
    authorities = dict(authority_registry or empty_authority_registry())
    contract = production_evidence_contract()
    ledger_document = json.loads(
        (output / "m12_repair_ledger_v6.json").read_text(encoding="utf-8")
    )
    envelope_rechecks = []
    for receipt in ledger_document.get("v7_envelopes", ()):
        try:
            report = verify_signed_envelope(
                SignedEvidenceEnvelope.from_dict(receipt["envelope"]),
                authorities,
                ledger_document,
            )
        except (KeyError, TypeError, ValueError):
            report = {"verdict": "HOLD"}
        envelope_rechecks.append(report["verdict"] == "PASS")

    graph_by_id = {
        row["slice_id"]: row for row in graph_registry["slices"]
    }
    domain_subjects = evidence_packet_contract()["targets"][
        "DOMAIN_POPULATION"
    ]["subject_ids"]
    internal_checks = {
        "active_epoch_exact": (
            crosswalk["epoch_id"] == ACTIVE_EPOCH_ID
            and crosswalk["epoch_census"] == ACTIVE_EPOCH_CENSUS
        ),
        "kc15_crosswalk_bijective": crosswalk["kc15"]["bijection"],
        "kc15_difference_preserved": crosswalk["kc15"]["relocated"] == 10,
        "kc27_crosswalk_exact": crosswalk["kc27"]["exact"],
        "ssn12_role_views_preserved": (
            len(crosswalk["ssn12"]["entries"]) == 12
            and crosswalk["ssn12"]["collapse_forbidden"]
        ),
        "f37_conflicts_preserved": (
            len(crosswalk["f37_branch_ledger"]["entries"]) == 3
            and crosswalk["f37_branch_ledger"]["latest_wins_forbidden"]
        ),
        "graph_schedule_exact": (
            graph_by_id["X16_SCHEDULE"]["relation_record_count"] == 268
        ),
        "graph_algebra_exact": (
            graph_by_id["X16_ALGEBRA"]["relation_record_count"] == 276
        ),
        "graph_multiplex_exact": (
            graph_by_id["X16_MULTIPLEX"]["relation_record_count"] == 308
        ),
        "domain_population_bindings_complete": all(
            domain_binding_for_subject(subject)["canonical_gid"]
            == int(subject[3:])
            for subject in domain_subjects
        ),
        "authority_registry_integrity": authority_registry_integrity(
            authorities
        ),
        "admitted_envelopes_reverified": all(envelope_rechecks),
        "direct_unsigned_production_closed": (
            contract["direct_v6_production_admission"]
            == "FORBIDDEN_WITHOUT_V7_ENVELOPE_CONTEXT"
            and contract["direct_v5_bridge_commit"]
            == "FORBIDDEN_WITHOUT_V7_ENVELOPE_CONTEXT"
        ),
        "paired_ic10_required": "IC10_constitutional"
        in contract["ic10_law"],
        "atomic_envelope_required": (
            contract["envelope_atomicity"] == "ALL_PACKETS_OR_NONE"
        ),
    }
    internal_verdict = (
        "PASS" if all(internal_checks.values()) else "FAIL"
    )
    pinned_active_keys = [
        key
        for key in authorities.get("keys", ())
        if key.get("status") == "ACTIVE"
        and key.get("key_id") not in authorities.get("revoked_key_ids", ())
        and key.get("algorithm") == "ED25519"
        and key.get("independent") is True
        and key.get("test_only") is False
        and "PRODUCTION" in key.get("namespaces", ())
    ]
    state_body = {
        "schema": "KC144.ProductionEvidenceState.V7",
        "release": "KC144.PRODUCTION.EVIDENCE.KERNEL.V7",
        "parent_release": "KC144.M12.REPAIR.COMPILER.V6",
        "epoch_id": ACTIVE_EPOCH_ID,
        "epoch_census": ACTIVE_EPOCH_CENSUS,
        "frozen_base_state_root": v6_state["frozen_base_state_root"],
        "crosswalk_digest": crosswalk["crosswalk_digest"],
        "graph_slice_registry_digest": graph_registry["registry_digest"],
        "authority_registry_digest": authorities["registry_digest"],
        "internal_readiness": {
            "verdict": internal_verdict,
            "checks": internal_checks,
        },
        "external_readiness": {
            "pinned_active_keys": len(pinned_active_keys),
            "signed_envelopes": len(envelope_rechecks),
            "signed_envelopes_reverified": sum(envelope_rechecks),
            "status": (
                "READY"
                if pinned_active_keys
                else "READY_AWAITING_PINNED_EXTERNAL_AUTHORITY"
            ),
        },
        "m12": v6_state["ssn12"],
        "production_certificate_issued": v6_state[
            "production_certificate_issued"
        ],
        "production_truth_effect": "NONE",
        "frozen_crystal_mutated": False,
        "next_seed": (
            v6_state["next_seed"]
            if pinned_active_keys
            else "KC144.V7::PIN-EXTERNAL-AUTHORITY-AND-SIGN-PARALLEL-WAVE"
        ),
    }
    state = {**state_body, "state_digest": digest(state_body)}
    documents = {
        "active_epoch_crosswalk_v7.json": crosswalk,
        "graph_slice_registry_v7.json": graph_registry,
        "authority_registry_v7.json": authorities,
        "production_evidence_contract_v7.json": contract,
        "production_evidence_state_v7.json": state,
    }
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    release_body = {
        "schema": "KC144.ProductionEvidenceRelease.V7",
        "release": "KC144.PRODUCTION.EVIDENCE.KERNEL.V7",
        "parent_release": v6_release["release"],
        "verdict": (
            "PASS"
            if v6_release["verdict"] == "PASS"
            and internal_verdict == "PASS"
            else "FAIL"
        ),
        "operational_status": state["external_readiness"]["status"],
        "m12_status": state["m12"]["verdict"],
        "production_certificate_issued": state[
            "production_certificate_issued"
        ],
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
        "next_seed": state["next_seed"],
    }
    release = {**release_body, "release_digest": digest(release_body)}
    (output / "production_evidence_release_v7.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
