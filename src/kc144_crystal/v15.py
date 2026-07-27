from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .application_v15 import (
    TRANSPORT_ID,
    BatchBoundCandidateApplication,
    application_publication_manifest,
    application_publication_manifest_integrity,
    application_publication_payload,
    application_publication_payload_integrity,
    application_receipt_ledger,
    application_receipt_ledger_integrity,
    application_transport_contract,
    public_application_receipt_ledger,
)
from .ceremony_v10 import ROLES
from .dispatch_v11 import challenge_batch_integrity
from .nomination_v14 import (
    nomination_call_manifest,
    nomination_role_call,
)
from .population import digest
from .v14 import compile_nomination_intake_runtime


def _next_seed(solution_status: str, application_count: int) -> str:
    if solution_status == "UNIQUE_PROVISIONAL_COHORT":
        return (
            "KC144.V15::DELIVER-FIVE-BATCH-BOUND-PARTICIPANT-"
            "PACKETS-AND-ROUTE-SIGNED-RETURNS"
        )
    if solution_status == "MULTIPLE_COHORTS":
        return (
            "KC144.V15::OBTAIN-SOURCE-AUTHORIZED-COHORT-SELECTION"
        )
    if solution_status == "SOLVER_BUDGET_EXHAUSTED":
        return (
            "KC144.V15::REFINE-APPLICATION-SET-OR-INCREASE-BOUNDED-"
            "SOLVER-BUDGET"
        )
    if application_count:
        return (
            "KC144.V15::INGEST-ADDITIONAL-INDEPENDENCE-QUALIFIED-"
            "BATCH-BOUND-APPLICATIONS"
        )
    return (
        "KC144.V15::PUBLISH-FIVE-BATCH-BOUND-CALL-PAYLOADS-AND-"
        "INGEST-REAL-APPLICATIONS"
    )


def compile_application_transport_runtime(
    output_directory: str | Path,
    *,
    challenge_batch: Mapping[str, Any],
    applications: Sequence[BatchBoundCandidateApplication] = (),
    checked_at: str | None = None,
    node_budget: int = 100_000,
) -> dict[str, Any]:
    output = Path(output_directory)
    output.mkdir(parents=True, exist_ok=True)
    batch = dict(challenge_batch)
    effective_time = checked_at or str(batch["issued_at"])
    calls = [nomination_role_call(batch, role) for role in ROLES]
    call_manifest = nomination_call_manifest(batch, calls)
    ledger_internal = application_receipt_ledger(
        batch,
        calls,
        call_manifest,
        applications,
        checked_at=effective_time,
    )
    admitted_envelopes = ledger_internal["_admitted_envelopes"]
    receipt_ledger = public_application_receipt_ledger(
        ledger_internal
    )
    v14_release = compile_nomination_intake_runtime(
        output,
        challenge_batch=batch,
        envelopes=admitted_envelopes,
        checked_at=effective_time,
        node_budget=node_budget,
    )
    assignment = json.loads(
        (
            output / "cohort_packet_assignment_manifest_v14.json"
        ).read_text(encoding="utf-8")
    )
    contract = application_transport_contract()
    payloads = [
        application_publication_payload(
            batch,
            call,
            call_manifest,
        )
        for call in calls
    ]
    publication_manifest = application_publication_manifest(
        batch,
        call_manifest,
        calls,
        payloads,
    )
    solution_status = str(v14_release["solution_status"])
    if not applications:
        barrier = "FIVE_EXTERNAL_BATCH_BOUND_APPLICATIONS_REQUIRED"
    else:
        barrier = str(v14_release["operational_status"])
    next_seed = _next_seed(solution_status, len(applications))
    internal_checks = {
        "v14_runtime_pass": v14_release["verdict"] == "PASS",
        "batch_integrity": challenge_batch_integrity(batch),
        "five_payloads_exact": (
            len(payloads) == 5
            and [payload["role"] for payload in payloads]
            == list(ROLES)
        ),
        "all_payloads_integral": all(
            application_publication_payload_integrity(
                batch,
                call,
                call_manifest,
                payload,
            )
            for call, payload in zip(calls, payloads)
        ),
        "publication_manifest_integrity": (
            application_publication_manifest_integrity(
                batch,
                call_manifest,
                calls,
                payloads,
                publication_manifest,
            )
        ),
        "receipt_ledger_integrity": (
            application_receipt_ledger_integrity(
                batch,
                calls,
                call_manifest,
                applications,
                receipt_ledger,
                checked_at=effective_time,
            )
        ),
        "v14_receipt_count_exact": (
            v14_release["submission_count"]
            == receipt_ledger["admitted_application_count"]
        ),
        "no_cross_batch_release": all(
            receipt["routing_verdict"] != "PASS"
            or receipt["status"] == "INNER_V14_ENVELOPE_RELEASED"
            for receipt in receipt_ledger["receipts"]
        ),
        "no_fabricated_publication": (
            publication_manifest["published_payload_count"] == 0
            and not publication_manifest["publication_claimed"]
        ),
        "no_fabricated_delivery": (
            assignment["delivered_packets"] == 0
        ),
        "no_authority_grant": (
            not assignment["governance_authority_granted"]
        ),
        "truth_effect_none": assignment["truth_effect"] == "NONE",
    }
    internal_verdict = (
        "PASS" if all(internal_checks.values()) else "FAIL"
    )
    runtime_body = {
        "schema": "KC144.ApplicationTransportRuntimeState.V15",
        "release": "KC144.CANDIDATE.APPLICATION.TRANSPORT.RUNTIME.V15",
        "parent_release": v14_release["release"],
        "transport_id": TRANSPORT_ID,
        "transport_contract_digest": contract["contract_digest"],
        "batch_id": batch["batch_id"],
        "batch_root": batch["batch_root"],
        "call_manifest_root": call_manifest["manifest_root"],
        "publication_manifest_root": publication_manifest[
            "manifest_root"
        ],
        "application_receipt_ledger_root": receipt_ledger[
            "ledger_root"
        ],
        "assignment_root": assignment["assignment_root"],
        "prepared_publication_payloads": 5,
        "published_publication_payloads": 0,
        "application_count": receipt_ledger["application_count"],
        "admitted_application_count": receipt_ledger[
            "admitted_application_count"
        ],
        "held_application_count": receipt_ledger[
            "held_application_count"
        ],
        "solution_status": solution_status,
        "assigned_packet_count": v14_release[
            "assigned_packet_count"
        ],
        "delivered_packet_count": 0,
        "internal_readiness": {
            "verdict": internal_verdict,
            "checks": internal_checks,
        },
        "barrier": barrier,
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
        "application_transport_contract_v15.json": contract,
        "application_publication_manifest_v15.json": (
            publication_manifest
        ),
        "application_receipt_ledger_v15.json": receipt_ledger,
        "application_transport_runtime_state_v15.json": runtime,
    }
    for payload in payloads:
        role_slug = str(payload["role"]).lower()
        documents[
            f"application_publication_{role_slug}_v15.json"
        ] = payload
    for filename, document in documents.items():
        (output / filename).write_text(
            json.dumps(document, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    release_body = {
        "schema": "KC144.ApplicationTransportRelease.V15",
        "release": "KC144.CANDIDATE.APPLICATION.TRANSPORT.RUNTIME.V15",
        "parent_release": v14_release["release"],
        "verdict": (
            "PASS"
            if v14_release["verdict"] == "PASS"
            and internal_verdict == "PASS"
            else "FAIL"
        ),
        "operational_status": barrier,
        "prepared_publication_payloads": 5,
        "published_publication_payloads": 0,
        "application_count": receipt_ledger["application_count"],
        "admitted_application_count": receipt_ledger[
            "admitted_application_count"
        ],
        "held_application_count": receipt_ledger[
            "held_application_count"
        ],
        "solution_status": solution_status,
        "assigned_packet_count": v14_release[
            "assigned_packet_count"
        ],
        "delivered_packet_count": 0,
        "governance_activated": False,
        "production_certificate_issued": False,
        "frozen_crystal_mutated": False,
        "added_artifacts": sorted(documents),
        "next_seed": next_seed,
    }
    release = {**release_body, "release_digest": digest(release_body)}
    (output / "application_transport_release_v15.json").write_text(
        json.dumps(release, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return release
