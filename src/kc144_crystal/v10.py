from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .ceremony_v10 import (
    CEREMONY_ID,
    ROLES,
    governance_ceremony_contract,
    governance_ceremony_plan,
    governance_ratification_contract,
)
from .evidence_v7 import empty_authority_registry
from .handoff_v9 import empty_governance_registry
from .population import digest
from .v9 import compile_external_handoff_runtime


def compile_governance_ceremony_runtime(
    output_directory: str | Path,
    *,
    ledger: Mapping[str, Any] | None = None,
    authority_registry: Mapping[str, Any] | None = None,
    governance_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    authorities = dict(authority_registry or empty_authority_registry())
    governance = dict(
        governance_registry or empty_governance_registry()
    )
    v9_release = compile_external_handoff_runtime(
        output,
        ledger=ledger,
        authority_registry=authorities,
        governance_registry=governance,
    )
    handoff = json.loads(
        (output / "external_handoff_bundle_v9.json").read_text(
            encoding="utf-8"
        )
    )
    ceremony_contract = governance_ceremony_contract()
    ratification_contract = governance_ratification_contract()
    plan = governance_ceremony_plan(
        authority_registry_digest=authorities["registry_digest"],
        handoff_bundle_root=handoff["bundle_root"],
    )
    internal_checks = {
        "v9_runtime_pass": v9_release["verdict"] == "PASS",
        "ceremony_identity_exact": plan["ceremony_id"] == CEREMONY_ID,
        "five_roles_exact": [seat["role"] for seat in plan["seats"]]
        == list(ROLES),
        "five_seats_unfilled": (
            plan["required_seats"] == 5 and plan["filled_seats"] == 0
        ),
        "random_nonce_required": ceremony_contract["challenge_nonce"]
        == "32_RANDOM_BYTES_HEX",
        "single_institution_forbidden": "institutions"
        in ceremony_contract["independence_law"],
        "external_ratification_required": "two independent signed"
        in ceremony_contract["activation_law"],
        "challenge_disposition_required": "challenge disposition"
        in ceremony_contract["activation_law"],
        "constitution_transition_required": "constitution transition"
        in ceremony_contract["activation_law"],
        "rollback_required": "rollback root"
        in ceremony_contract["activation_law"],
        "two_anchor_contract": ratification_contract[
            "minimum_external_anchors"
        ]
        == 2,
        "fixture_activation_forbidden": ceremony_contract["fixture_law"]
        == "LOCAL_OR_TEST_PROOFS_NEVER_ACTIVATE_PRODUCTION",
        "no_default_challenges_or_keys_emitted": plan["status"]
        == "AWAITING_EXTERNAL_PARTICIPANTS",
    }
    internal_verdict = (
        "PASS" if all(internal_checks.values()) else "FAIL"
    )
    runtime_body = {
        "schema": "KC144.GovernanceCeremonyRuntimeState.V10",
        "release": "KC144.GOVERNANCE.CEREMONY.RUNTIME.V10",
        "parent_release": "KC144.EXTERNAL.HANDOFF.RUNTIME.V9",
        "ceremony_id": CEREMONY_ID,
        "ceremony_contract_digest": ceremony_contract[
            "contract_digest"
        ],
        "ratification_contract_digest": ratification_contract[
            "contract_digest"
        ],
        "plan_digest": plan["plan_digest"],
        "internal_readiness": {
            "verdict": internal_verdict,
            "checks": internal_checks,
        },
        "filled_seats": plan["filled_seats"],
        "required_seats": plan["required_seats"],
        "barrier": plan["barrier"],
        "governance_activated": False,
        "production_certificate_issued": v9_release[
            "production_certificate_issued"
        ],
        "production_truth_effect": "NONE",
        "frozen_crystal_mutated": False,
        "next_seed": plan["next_seed"],
    }
    runtime = {
        **runtime_body,
        "runtime_state_digest": digest(runtime_body),
    }
    documents = {
        "governance_ceremony_contract_v10.json": ceremony_contract,
        "governance_ratification_contract_v10.json": ratification_contract,
        "governance_ceremony_plan_v10.json": plan,
        "governance_ceremony_runtime_state_v10.json": runtime,
    }
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    release_body = {
        "schema": "KC144.GovernanceCeremonyRelease.V10",
        "release": "KC144.GOVERNANCE.CEREMONY.RUNTIME.V10",
        "parent_release": v9_release["release"],
        "verdict": (
            "PASS"
            if v9_release["verdict"] == "PASS"
            and internal_verdict == "PASS"
            else "FAIL"
        ),
        "operational_status": plan["barrier"],
        "governance_roles": len(ROLES),
        "filled_seats": plan["filled_seats"],
        "required_seats": plan["required_seats"],
        "governance_activated": False,
        "production_certificate_issued": runtime[
            "production_certificate_issued"
        ],
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
        "next_seed": runtime["next_seed"],
    }
    release = {**release_body, "release_digest": digest(release_body)}
    (output / "governance_ceremony_release_v10.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
