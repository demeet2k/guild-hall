from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .campaign_v8 import (
    CAMPAIGN_ID,
    authority_enrollment_contract,
    campaign_manifest,
    campaign_state,
    run_to_barrier,
)
from .evidence_v7 import empty_authority_registry
from .population import digest
from .repair import evidence_packet_contract
from .v7 import compile_production_evidence_kernel


def compile_parallel_campaign_runtime(
    output_directory: str | Path,
    *,
    ledger: Mapping[str, Any] | None = None,
    authority_registry: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    authorities = dict(authority_registry or empty_authority_registry())
    v7_release = compile_production_evidence_kernel(
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
    manifest = campaign_manifest()
    enrollment = authority_enrollment_contract()
    state = campaign_state(repair_ledger, authorities)
    barrier_run = run_to_barrier(repair_ledger, authorities, {})
    barrier_report = {
        key: value
        for key, value in barrier_run.items()
        if key not in {"ledger", "campaign_state"}
    }

    targets = evidence_packet_contract()["targets"]
    expected_by_kind = {
        kind: set(definition["subject_ids"])
        for kind, definition in targets.items()
    }
    actual_by_kind: dict[str, set[str]] = {
        kind: set() for kind in expected_by_kind
    }
    for shard in manifest["shards"]:
        actual_by_kind[shard["evidence_kind"]].update(
            shard["subject_ids"]
        )
    internal_checks = {
        "v7_kernel_pass": v7_release["verdict"] == "PASS",
        "campaign_identity_exact": manifest["campaign_id"] == CAMPAIGN_ID,
        "sixteen_shards_exact": manifest["shard_count"] == 16,
        "fourteen_way_frontier_exact": (
            manifest["maximum_parallel_width"] == 14
        ),
        "two_hundred_thirty_two_packets_exact": (
            manifest["packet_count"] == 232
        ),
        "target_partition_exact": actual_by_kind == expected_by_kind,
        "bridge_shard_exact": len(
            actual_by_kind["BRIDGE_CERTIFICATION"]
        )
        == 28,
        "domain_shards_exact": len(actual_by_kind["DOMAIN_POPULATION"])
        == 58,
        "replay_shards_exact": len(actual_by_kind["INDEPENDENT_REPLAY"])
        == 144,
        "defect_dependency_exact": next(
            shard
            for shard in manifest["shards"]
            if shard["shard_id"] == "B_DEFECT_CLOSURE"
        )["dependencies"]
        == [
            shard["shard_id"]
            for shard in manifest["shards"]
            if shard["phase"] == "A_FRONTIER"
        ],
        "promotion_dependency_exact": next(
            shard
            for shard in manifest["shards"]
            if shard["shard_id"] == "C_IC10_PROMOTION"
        )["dependencies"]
        == ["B_DEFECT_CLOSURE"],
        "holographic_reconstruction_present": set(
            manifest["hologram"]
        )
        == {
            "ID",
            "Coordinate",
            "Kernel",
            "Delta",
            "Routes",
            "Boundary",
            "Return",
            "Seed",
        },
        "authority_self_enrollment_forbidden": (
            enrollment["governance_effect"] == "NONE"
            and "cannot approve" in enrollment["anti_self_authorization_law"]
        ),
        "empty_run_stops_at_explicit_barrier": (
            barrier_run["status"] == "BARRIER"
            and bool(barrier_run["barrier"])
        ),
        "frozen_crystal_unchanged": (
            not state["frozen_crystal_mutated"]
            and not barrier_run["frozen_crystal_mutated"]
        ),
    }
    internal_verdict = (
        "PASS" if all(internal_checks.values()) else "FAIL"
    )
    runtime_body = {
        "schema": "KC144.ParallelCampaignRuntimeState.V8",
        "release": "KC144.PARALLEL.CAMPAIGN.RUNTIME.V8",
        "parent_release": "KC144.PRODUCTION.EVIDENCE.KERNEL.V7",
        "campaign_id": CAMPAIGN_ID,
        "campaign_manifest_digest": manifest["manifest_digest"],
        "authority_enrollment_contract_digest": enrollment[
            "contract_digest"
        ],
        "internal_readiness": {
            "verdict": internal_verdict,
            "checks": internal_checks,
        },
        "campaign_state_digest": state["state_digest"],
        "barrier_report_digest": barrier_report["report_digest"],
        "barrier": state["barrier"],
        "production_certificate_issued": v7_release[
            "production_certificate_issued"
        ],
        "production_truth_effect": "NONE",
        "frozen_crystal_mutated": False,
        "next_seed": state["next_seed"],
    }
    runtime_state = {
        **runtime_body,
        "runtime_state_digest": digest(runtime_body),
    }
    documents = {
        "authority_enrollment_contract_v8.json": enrollment,
        "parallel_campaign_manifest_v8.json": manifest,
        "parallel_campaign_state_v8.json": state,
        "run_to_barrier_v8.json": barrier_report,
        "parallel_campaign_runtime_state_v8.json": runtime_state,
    }
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    release_body = {
        "schema": "KC144.ParallelCampaignRelease.V8",
        "release": "KC144.PARALLEL.CAMPAIGN.RUNTIME.V8",
        "parent_release": v7_release["release"],
        "verdict": (
            "PASS"
            if v7_release["verdict"] == "PASS"
            and internal_verdict == "PASS"
            else "FAIL"
        ),
        "operational_status": state["barrier"],
        "campaign_shards": manifest["shard_count"],
        "campaign_packets": manifest["packet_count"],
        "maximum_parallel_width": manifest["maximum_parallel_width"],
        "completed_shards": state["completed_shards"],
        "production_certificate_issued": runtime_state[
            "production_certificate_issued"
        ],
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
        "next_seed": runtime_state["next_seed"],
    }
    release = {**release_body, "release_digest": digest(release_body)}
    (output / "parallel_campaign_release_v8.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
