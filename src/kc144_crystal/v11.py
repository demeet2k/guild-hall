from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ceremony_v10 import GovernanceEnrollmentResponse
from .dispatch_v11 import (
    DISPATCH_ID,
    challenge_batch_integrity,
    governance_dispatch_contract,
    governance_dispatch_plan,
    route_governance_responses,
)
from .evidence_v7 import empty_authority_registry
from .handoff_v9 import empty_governance_registry
from .population import digest
from .v10 import compile_governance_ceremony_runtime


def compile_governance_dispatch_runtime(
    output_directory: str | Path,
    *,
    ledger: Mapping[str, Any] | None = None,
    authority_registry: Mapping[str, Any] | None = None,
    governance_registry: Mapping[str, Any] | None = None,
    challenge_batch: Mapping[str, Any] | None = None,
    responses: Sequence[GovernanceEnrollmentResponse] = (),
    verified_at: str | None = None,
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    authorities = dict(authority_registry or empty_authority_registry())
    governance = dict(
        governance_registry or empty_governance_registry()
    )
    v10_release = compile_governance_ceremony_runtime(
        output,
        ledger=ledger,
        authority_registry=authorities,
        governance_registry=governance,
    )
    v10_plan = json.loads(
        (output / "governance_ceremony_plan_v10.json").read_text(
            encoding="utf-8"
        )
    )
    contract = governance_dispatch_contract()
    batch = dict(challenge_batch) if challenge_batch is not None else None
    router = None
    if batch is not None:
        effective_time = verified_at or str(batch["issued_at"])
        router = route_governance_responses(
            batch,
            responses,
            verified_at=effective_time,
        )
    plan = governance_dispatch_plan(
        authority_registry_digest=authorities["registry_digest"],
        handoff_bundle_root=v10_plan["handoff_bundle_root"],
        batch=batch,
        router=router,
    )
    batch_matches_active_roots = (
        batch is None
        or (
            batch.get("authority_registry_digest")
            == authorities["registry_digest"]
            and batch.get("handoff_bundle_root")
            == v10_plan["handoff_bundle_root"]
        )
    )
    batch_integrity = (
        batch is None or challenge_batch_integrity(batch)
    )
    internal_checks = {
        "v10_runtime_pass": v10_release["verdict"] == "PASS",
        "dispatch_identity_exact": contract["dispatch_id"]
        == DISPATCH_ID,
        "five_role_parallelism_exact": plan["parallelism"]
        == "ALL_FIVE_ROLE_RESPONSES_ROUTE_IN_ONE_WAVE",
        "batch_integrity_or_not_yet_issued": batch_integrity,
        "batch_matches_active_v10_roots": batch_matches_active_roots,
        "no_synthetic_responses": len(responses) == 0
        or batch is not None,
        "no_automatic_activation": plan["governance_activated"] is False,
        "truth_effect_none": plan["truth_effect"] == "NONE",
    }
    internal_verdict = (
        "PASS" if all(internal_checks.values()) else "FAIL"
    )
    runtime_body = {
        "schema": "KC144.GovernanceDispatchRuntimeState.V11",
        "release": "KC144.GOVERNANCE.DISPATCH.RUNTIME.V11",
        "parent_release": v10_release["release"],
        "dispatch_id": DISPATCH_ID,
        "dispatch_contract_digest": contract["contract_digest"],
        "plan_digest": plan["plan_digest"],
        "batch_id": batch.get("batch_id") if batch else None,
        "batch_root": batch.get("batch_root") if batch else None,
        "batch_issued": batch is not None and batch_integrity,
        "counted_responses": (
            router["counted_response_count"] if router else 0
        ),
        "required_responses": 5,
        "internal_readiness": {
            "verdict": internal_verdict,
            "checks": internal_checks,
        },
        "barrier": plan["barrier"],
        "governance_activated": False,
        "production_certificate_issued": False,
        "production_truth_effect": "NONE",
        "frozen_crystal_mutated": False,
        "next_seed": plan["next_seed"],
    }
    runtime = {
        **runtime_body,
        "runtime_state_digest": digest(runtime_body),
    }
    documents: dict[str, Mapping[str, Any]] = {
        "governance_dispatch_contract_v11.json": contract,
        "governance_dispatch_plan_v11.json": plan,
        "governance_dispatch_runtime_state_v11.json": runtime,
    }
    if batch is not None:
        documents["governance_challenge_batch_v11.json"] = batch
    if router is not None:
        documents["governance_response_router_v11.json"] = router
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    release_body = {
        "schema": "KC144.GovernanceDispatchRelease.V11",
        "release": "KC144.GOVERNANCE.DISPATCH.RUNTIME.V11",
        "parent_release": v10_release["release"],
        "verdict": (
            "PASS"
            if v10_release["verdict"] == "PASS"
            and internal_verdict == "PASS"
            else "FAIL"
        ),
        "operational_status": plan["barrier"],
        "batch_issued": runtime["batch_issued"],
        "counted_responses": runtime["counted_responses"],
        "required_responses": runtime["required_responses"],
        "governance_activated": False,
        "production_certificate_issued": False,
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
        "next_seed": runtime["next_seed"],
    }
    release = {**release_body, "release_digest": digest(release_body)}
    (output / "governance_dispatch_release_v11.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
