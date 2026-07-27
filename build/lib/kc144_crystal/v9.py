from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .campaign_v8 import campaign_manifest
from .evidence_v7 import empty_authority_registry
from .handoff_v9 import (
    GOVERNANCE_MEMBER_COUNT,
    GOVERNANCE_THRESHOLD,
    HANDOFF_ID,
    empty_governance_registry,
    governance_registry_integrity,
    handoff_bundle,
    handoff_state,
    run_handoff_to_barrier,
    source_harvest_contract,
    threshold_governance_contract,
)
from .population import digest
from .v8 import compile_parallel_campaign_runtime


def compile_external_handoff_runtime(
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
    v8_release = compile_parallel_campaign_runtime(
        output,
        ledger=ledger,
        authority_registry=authorities,
    )
    repair_ledger = (
        dict(ledger)
        if ledger is not None
        else json.loads(
            (output / "m12_repair_ledger_v6.json").read_text(
                encoding="utf-8"
            )
        )
    )
    governance_contract = threshold_governance_contract()
    harvest_contract = source_harvest_contract()
    bundle = handoff_bundle(repair_ledger)
    state = handoff_state(
        repair_ledger,
        authorities,
        governance,
    )
    empty_run = run_handoff_to_barrier(
        repair_ledger,
        authorities,
        {},
    )
    run_report = {
        key: value
        for key, value in empty_run.items()
        if key not in {"ledger", "campaign_report"}
    }
    campaign = campaign_manifest()
    request_subjects = [
        (request["evidence_kind"], subject)
        for request in bundle["requests"]
        for subject in request["subject_ids"]
    ]
    campaign_subjects = [
        (shard["evidence_kind"], subject)
        for shard in campaign["shards"]
        for subject in shard["subject_ids"]
    ]
    request_digests = [
        request["request_digest"] for request in bundle["requests"]
    ]
    internal_checks = {
        "v8_runtime_pass": v8_release["verdict"] == "PASS",
        "handoff_identity_exact": bundle["handoff_id"] == HANDOFF_ID,
        "sixteen_requests_exact": bundle["request_count"] == 16,
        "two_hundred_thirty_two_packets_exact": (
            bundle["packet_count"] == 232
        ),
        "campaign_partition_exact": request_subjects
        == campaign_subjects,
        "request_digests_unique": len(request_digests)
        == len(set(request_digests)),
        "bundle_root_bound": bool(bundle["bundle_root"]),
        "source_once_fanout_law": "hashed once"
        in harvest_contract["harvest_law"],
        "threshold_three_of_five": (
            governance_contract["member_count"]
            == GOVERNANCE_MEMBER_COUNT
            and governance_contract["threshold"]
            == GOVERNANCE_THRESHOLD
        ),
        "single_key_governance_forbidden": "no single key"
        in governance["law"],
        "governance_registry_integrity": governance_registry_integrity(
            governance
        ),
        "empty_run_has_no_truth_effect": (
            empty_run["production_truth_effect"] == "NONE"
            and not empty_run["frozen_crystal_mutated"]
        ),
        "external_barrier_explicit": state["barrier"]
        in {
            "THRESHOLD_GOVERNANCE_MEMBERS_REQUIRED",
            "THRESHOLD_AUTHORITY_PIN_REQUIRED",
            "EXTERNAL_AUTHORITY_PIN_REQUIRED",
            "SIGNED_EVIDENCE_REQUIRED",
            "PRODUCTION_CAMPAIGN_COMPLETE",
            "TEST_CAMPAIGN_COMPLETE_NO_PRODUCTION_EFFECT",
        },
    }
    internal_verdict = (
        "PASS" if all(internal_checks.values()) else "FAIL"
    )
    runtime_body = {
        "schema": "KC144.ExternalHandoffRuntimeState.V9",
        "release": "KC144.EXTERNAL.HANDOFF.RUNTIME.V9",
        "parent_release": "KC144.PARALLEL.CAMPAIGN.RUNTIME.V8",
        "handoff_id": HANDOFF_ID,
        "bundle_root": bundle["bundle_root"],
        "bundle_digest": bundle["bundle_digest"],
        "governance_contract_digest": governance_contract[
            "contract_digest"
        ],
        "governance_registry_digest": governance["registry_digest"],
        "source_harvest_contract_digest": harvest_contract[
            "contract_digest"
        ],
        "internal_readiness": {
            "verdict": internal_verdict,
            "checks": internal_checks,
        },
        "handoff_state_digest": state["state_digest"],
        "run_report_digest": run_report["report_digest"],
        "barrier": state["barrier"],
        "production_certificate_issued": v8_release[
            "production_certificate_issued"
        ],
        "production_truth_effect": "NONE",
        "frozen_crystal_mutated": False,
        "next_seed": state["next_seed"],
    }
    runtime = {
        **runtime_body,
        "runtime_state_digest": digest(runtime_body),
    }
    documents = {
        "threshold_governance_contract_v9.json": governance_contract,
        "threshold_governance_registry_v9.json": governance,
        "source_harvest_contract_v9.json": harvest_contract,
        "external_handoff_bundle_v9.json": bundle,
        "external_handoff_state_v9.json": state,
        "external_handoff_run_v9.json": run_report,
        "external_handoff_runtime_state_v9.json": runtime,
    }
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    release_body = {
        "schema": "KC144.ExternalHandoffRelease.V9",
        "release": "KC144.EXTERNAL.HANDOFF.RUNTIME.V9",
        "parent_release": v8_release["release"],
        "verdict": (
            "PASS"
            if v8_release["verdict"] == "PASS"
            and internal_verdict == "PASS"
            else "FAIL"
        ),
        "operational_status": state["barrier"],
        "governance_members": state["active_governance_members"],
        "governance_threshold": GOVERNANCE_THRESHOLD,
        "handoff_requests": bundle["request_count"],
        "handoff_packets": bundle["packet_count"],
        "production_certificate_issued": runtime[
            "production_certificate_issued"
        ],
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
        "next_seed": runtime["next_seed"],
    }
    release = {**release_body, "release_digest": digest(release_body)}
    (output / "external_handoff_release_v9.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
