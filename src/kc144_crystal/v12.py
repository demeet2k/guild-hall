from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .ceremony_v10 import ROLES, GovernanceEnrollmentResponse
from .dispatch_v11 import challenge_batch_integrity
from .handoff_v12 import (
    HANDOFF_BARRIER,
    HANDOFF_ID,
    participant_handoff_contract,
    participant_handoff_manifest,
    participant_handoff_manifest_integrity,
    participant_handoff_packet,
)
from .population import digest
from .v11 import compile_governance_dispatch_runtime


def compile_participant_handoff_runtime(
    output_directory: str | Path,
    *,
    ledger: Mapping[str, Any] | None = None,
    authority_registry: Mapping[str, Any] | None = None,
    governance_registry: Mapping[str, Any] | None = None,
    challenge_batch: Mapping[str, Any],
    responses: Sequence[GovernanceEnrollmentResponse] = (),
    verified_at: str | None = None,
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    batch = dict(challenge_batch)
    v11_release = compile_governance_dispatch_runtime(
        output,
        ledger=ledger,
        authority_registry=authority_registry,
        governance_registry=governance_registry,
        challenge_batch=batch,
        responses=responses,
        verified_at=verified_at,
    )
    contract = participant_handoff_contract()
    packets = [
        participant_handoff_packet(batch, role) for role in ROLES
    ]
    manifest = participant_handoff_manifest(batch, packets)
    router = json.loads(
        (output / "governance_response_router_v11.json").read_text(
            encoding="utf-8"
        )
    )
    counted = int(router["counted_response_count"])
    if counted == 0:
        operational_status = HANDOFF_BARRIER
        next_seed = manifest["next_seed"]
    else:
        operational_status = str(router["barrier"])
        next_seed = (
            "KC144.V12::EXTERNAL-RATIFICATION"
            if operational_status == "EXTERNAL_RATIFICATION_REQUIRED"
            else "KC144.V12::DELIVER-REMAINING-PACKETS-AND-ROUTE-RETURNS"
        )
    internal_checks = {
        "v11_runtime_pass": v11_release["verdict"] == "PASS",
        "batch_integrity": challenge_batch_integrity(batch),
        "five_packets_exact": len(packets) == 5
        and [packet["role"] for packet in packets] == list(ROLES),
        "all_packets_integral": all(
            packet["packet_digest"]
            == digest(
                {
                    key: value
                    for key, value in packet.items()
                    if key != "packet_digest"
                }
            )
            for packet in packets
        ),
        "manifest_integrity": participant_handoff_manifest_integrity(
            batch,
            manifest,
            packets,
        ),
        "no_recipient_fabrication": all(
            packet["recipient_identity_root"] is None
            and packet["delivery_receipt_root"] is None
            and packet["delivery_state"]
            == "READY_UNADDRESSED_UNDELIVERED"
            for packet in packets
        ),
        "no_governance_activation": not any(
            packet["governance_activated"] for packet in packets
        ),
        "truth_effect_none": all(
            packet["truth_effect"] == "NONE" for packet in packets
        ),
    }
    internal_verdict = (
        "PASS" if all(internal_checks.values()) else "FAIL"
    )
    runtime_body = {
        "schema": "KC144.ParticipantHandoffRuntimeState.V12",
        "release": "KC144.PARTICIPANT.HANDOFF.RUNTIME.V12",
        "parent_release": v11_release["release"],
        "handoff_id": HANDOFF_ID,
        "handoff_contract_digest": contract["contract_digest"],
        "batch_id": batch["batch_id"],
        "batch_root": batch["batch_root"],
        "manifest_root": manifest["manifest_root"],
        "prepared_packets": len(packets),
        "addressed_packets": counted,
        "delivered_packets": counted,
        "counted_responses": counted,
        "internal_readiness": {
            "verdict": internal_verdict,
            "checks": internal_checks,
        },
        "barrier": operational_status,
        "governance_activated": False,
        "production_certificate_issued": False,
        "production_truth_effect": "NONE",
        "frozen_crystal_mutated": False,
        "next_seed": next_seed,
    }
    runtime = {
        **runtime_body,
        "runtime_state_digest": digest(runtime_body),
    }
    documents: dict[str, Mapping[str, Any]] = {
        "participant_handoff_contract_v12.json": contract,
        "participant_handoff_manifest_v12.json": manifest,
        "participant_handoff_runtime_state_v12.json": runtime,
    }
    for packet in packets:
        role_slug = str(packet["role"]).lower()
        documents[f"participant_packet_{role_slug}_v12.json"] = packet
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    release_body = {
        "schema": "KC144.ParticipantHandoffRelease.V12",
        "release": "KC144.PARTICIPANT.HANDOFF.RUNTIME.V12",
        "parent_release": v11_release["release"],
        "verdict": (
            "PASS"
            if v11_release["verdict"] == "PASS"
            and internal_verdict == "PASS"
            else "FAIL"
        ),
        "operational_status": operational_status,
        "prepared_packets": len(packets),
        "addressed_packets": counted,
        "delivered_packets": counted,
        "counted_responses": counted,
        "required_responses": 5,
        "governance_activated": False,
        "production_certificate_issued": False,
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
        "next_seed": next_seed,
    }
    release = {**release_body, "release_digest": digest(release_body)}
    (output / "participant_handoff_release_v12.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
