from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit import audit_crystal
from .agent_receipts import (
    build_agent_run_plan,
    compile_agent_run_receipts,
    verify_agent_run_receipts,
)
from .application_v15 import (
    BatchBoundCandidateApplication,
    application_publication_payload,
    application_transport_contract,
    verify_batch_bound_application,
)
from .bridge2pc import CommitAuthorization, commit_bridge, prepare_bridge_commit
from .campaign_v8 import (
    AuthorityEnrollmentProof,
    authority_enrollment_contract,
    campaign_manifest,
    campaign_state,
    run_to_barrier,
    verify_authority_enrollment,
)
from .ceremony_v10 import (
    ROLES,
    GovernanceEnrollmentResponse,
    GovernanceRatification,
    activate_governance_society,
    assemble_pending_society,
    create_governance_challenge,
    governance_ceremony_contract,
    governance_ratification_contract,
    verify_enrollment_response,
    verify_governance_ratification,
)
from .dispatch_v11 import (
    governance_challenge_batch_state,
    governance_dispatch_contract,
    issue_governance_challenge_batch,
    route_governance_responses,
)
from .edge_manifest import freeze_edge_manifest
from .evidence_v7 import (
    SignedEvidenceEnvelope,
    admit_signed_envelope,
    production_evidence_contract,
    verify_signed_envelope,
)
from .holonomy import measure_holonomy, replay_ablation
from .handoff_v9 import (
    AuthorityPinProposal,
    handoff_bundle,
    pin_authority_from_proposal,
    run_handoff_to_barrier,
    source_harvest_contract,
    threshold_governance_contract,
    verify_authority_pin_proposal,
    verify_source_harvest,
)
from .handoff_v12 import (
    participant_handoff_contract,
    verify_response_for_handoff_packet,
)
from .navigation import (
    adjacency,
    bridge_registry,
    navigation_relations,
    navigation_report,
    shortest_path,
)
from .nomination_v14 import (
    SignedCandidateNomination,
    nomination_call_manifest,
    nomination_intake_contract,
    nomination_role_call,
    verify_signed_candidate_nomination,
)
from .population import crystallize, write_crystal
from .parallel_routes import compile_parallel_route_crystal
from .query import QueryBundle, compile_query, query_contract
from .repair import (
    M12EvidencePacket,
    admit_evidence,
    empty_repair_ledger,
    evidence_packet_contract,
    repair_plan,
)
from .station import build_station_bodies
from .session import SessionSpec, cold_reconstruct, compile_session
from .selection_v13 import (
    CandidateNomination,
    candidate_selection_contract,
    solve_candidate_cohort,
)
from .systematic import compile_systematic_framework, frontier_ledger
from .tool_registry import locate_mycelium_tool, mycelium_tool_registry
from .transform import (
    br_mirror,
    coactivation_sigma,
    grid_d4_view,
    kc27_transform,
    x16_schedule_rotate,
)
from .wave import WaveQuery, propagate
from .v4 import compile_mycelium_framework
from .v5 import compile_global_state, default_session_spec
from .v6 import compile_repair_framework
from .v7 import compile_production_evidence_kernel
from .v8 import compile_parallel_campaign_runtime
from .v9 import compile_external_handoff_runtime
from .v10 import compile_governance_ceremony_runtime
from .v11 import compile_governance_dispatch_runtime
from .v12 import compile_participant_handoff_runtime
from .v13 import compile_candidate_selection_runtime
from .v14 import compile_nomination_intake_runtime
from .v15 import compile_application_transport_runtime
from .witness import (
    BridgeWitnessPacket,
    bridge_witness_contract,
    evaluate_bridge_witness,
)


def _json(value: object) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def _csv(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="kc144-crystal")
    commands = parser.add_subparsers(dest="command", required=True)

    build = commands.add_parser("build", help="generate the complete registry")
    build.add_argument("--output", default="registry/crystal.json")
    build.add_argument("--atlas")

    audit = commands.add_parser("audit", help="audit a freshly generated crystal")
    audit.add_argument("--output")

    inspect = commands.add_parser("inspect", help="inspect a generated seat")
    inspect.add_argument("gid", type=int)

    rotate = commands.add_parser("rotate", help="apply a typed transformation")
    rotate.add_argument("gid", type=int)
    rotate.add_argument(
        "operation",
        choices=("grid-r90", "x16-next", "br-mirror", "kc27-J", "sigma"),
    )

    body = commands.add_parser("body", help="inspect a complete station body")
    body.add_argument("gid", type=int)

    navigate = commands.add_parser("navigate", help="compile a shortest declared route")
    navigate.add_argument("start", type=int)
    navigate.add_argument("target", type=int)

    commands.add_parser("navigation-audit", help="audit the complete declared graph")
    commands.add_parser("bridges", help="emit the declared inter-band bridge ledger")
    commands.add_parser("holonomy", help="measure the five-route holonomy")
    commands.add_parser("replay-ablation", help="show the non-live replay counterfactual")
    commands.add_parser("frontier", help="emit the systematic open-obligation ledger")

    wave = commands.add_parser("wave", help="run a bounded parallel navigation wave")
    wave.add_argument("--starts", default="6", help="comma-separated GIDs")
    wave.add_argument("--budget", type=int, default=18)
    wave.add_argument("--query-id", default="KC144.V3.CLI.WAVE")

    parallel_routes = commands.add_parser(
        "parallel-routes",
        help="compile five KC144 route simulations and reduce them deterministically",
    )
    parallel_routes.add_argument("--workers", type=int, default=5)
    parallel_routes.add_argument("--output")
    parallel_routes.add_argument("--immutable-commit")
    parallel_routes.add_argument("--immutable-tree")
    parallel_routes.add_argument("--compiler-commit")
    parallel_routes.add_argument("--compiler-tree")

    commands.add_parser(
        "mycelium-tools",
        help="emit the content-addressed mycelium tool registry",
    )
    locate_tool = commands.add_parser(
        "mycelium-locate",
        help="resolve one exact tool lookup key or complete alias",
    )
    locate_tool.add_argument("query")
    locate_tool.add_argument("--starts", default="6")
    locate_tool.add_argument("--budget", type=int, default=18)

    agent_plan = commands.add_parser(
        "agent-run-plan",
        help="compile a content-addressed plan for a parallel-route snapshot",
    )
    agent_plan.add_argument("source")

    agent_run = commands.add_parser(
        "agent-run-receipts",
        help="execute and seal a deterministic agent-run receipt bundle",
    )
    agent_run.add_argument("source")
    agent_run.add_argument("--workers", type=int, default=5)
    agent_run.add_argument("--output")
    agent_run.add_argument("--runtime-commit")
    agent_run.add_argument("--runtime-tree")
    agent_run.add_argument("--source-snapshot-digest")

    agent_verify = commands.add_parser(
        "agent-run-verify",
        help="verify a content-addressed agent-run receipt bundle",
    )
    agent_verify.add_argument("bundle")
    agent_verify.add_argument("--source")

    systematic = commands.add_parser("systematic", help="compile every V3 registry")
    systematic.add_argument("--output", default="registry/v3")

    query = commands.add_parser("query", help="compile an H06 QueryBundle")
    query.add_argument("--file", help="JSON QueryBundle; overrides query flags")
    query.add_argument("--query-id", default="KC144.V4.CLI.QUERY")
    query.add_argument("--goal")
    query.add_argument("--terms", default="")
    query.add_argument("--domains", default="")
    query.add_argument("--operators", default="")
    query.add_argument("--invariants", default="")
    query.add_argument("--boundaries", default="")
    query.add_argument(
        "--evidence-floor",
        default="STRUCTURAL",
        choices=(
            "STRUCTURAL",
            "SOURCE_DECLARED",
            "INDEPENDENT_REPLAY",
            "PROMOTABLE",
        ),
    )
    query.add_argument("--starts", default="6")
    query.add_argument("--budget", type=int, default=18)
    query.add_argument(
        "--return-mode",
        default="RETURN_ARM",
        choices=("NONE", "RETRACE", "TYPED_RETRACE", "RETURN_ARM"),
    )
    query.add_argument("--max-results", type=int, default=12)

    commands.add_parser("query-contract", help="emit the V4 H06 query contract")
    bridge_witness = commands.add_parser(
        "bridge-witness", help="evaluate a beta transport-witness packet"
    )
    bridge_witness.add_argument("packet")
    commands.add_parser(
        "bridge-witness-contract", help="emit the V4 beta witness contract"
    )
    mycelium = commands.add_parser("mycelium", help="compile the complete V4 runtime")
    mycelium.add_argument("--output", default="registry/v4")

    commands.add_parser("edge-manifest", help="freeze the typed V5 edge manifest")
    session = commands.add_parser("session", help="compile a V5 traversal session")
    session.add_argument("--file", help="JSON SessionSpec; defaults to V5 constellation")
    cold = commands.add_parser("cold-reconstruct", help="replay a V5 reentry seed")
    cold.add_argument("seed")
    bridge_prepare = commands.add_parser(
        "bridge-prepare", help="prepare a beta bridge commit"
    )
    bridge_prepare.add_argument("packet")
    bridge_commit = commands.add_parser(
        "bridge-commit", help="evaluate phase two of a beta bridge commit"
    )
    bridge_commit.add_argument("packet")
    bridge_commit.add_argument("preparation")
    bridge_commit.add_argument("authorization")
    bridge_commit.add_argument(
        "--namespace", choices=("PRODUCTION", "TEST"), default="PRODUCTION"
    )
    global_state = commands.add_parser(
        "global-state", help="compile the complete V5 global state"
    )
    global_state.add_argument("--output", default="registry/v5")
    commands.add_parser(
        "m12-evidence-contract", help="emit the V6 typed evidence contract"
    )
    m12_plan = commands.add_parser(
        "m12-repair-plan", help="compile the dependency-aware M12 repair plan"
    )
    m12_plan.add_argument("--ledger", help="existing V6 repair ledger")
    m12_admit = commands.add_parser(
        "m12-evidence-admit", help="admit one packet to a V6 evidence overlay"
    )
    m12_admit.add_argument("packet")
    m12_admit.add_argument("ledger")
    m12_admit.add_argument("--output", help="write the resulting ledger")
    repair = commands.add_parser(
        "repair", help="compile the complete V6 M12 repair framework"
    )
    repair.add_argument("--output", default="registry/v6")
    commands.add_parser(
        "production-evidence-contract",
        help="emit the V7 cryptographic production-evidence contract",
    )
    evidence_verify = commands.add_parser(
        "evidence-envelope-verify",
        help="verify one signed V7 evidence envelope without mutation",
    )
    evidence_verify.add_argument("envelope")
    evidence_verify.add_argument("ledger")
    evidence_verify.add_argument("authorities")
    evidence_admit = commands.add_parser(
        "evidence-envelope-admit",
        help="atomically admit one cryptographically verified V7 envelope",
    )
    evidence_admit.add_argument("envelope")
    evidence_admit.add_argument("ledger")
    evidence_admit.add_argument("authorities")
    evidence_admit.add_argument("--output")
    evidence_kernel = commands.add_parser(
        "evidence-kernel",
        help="compile the complete V7 production-evidence kernel",
    )
    evidence_kernel.add_argument("--output", default="registry/v7")
    evidence_kernel.add_argument("--ledger")
    evidence_kernel.add_argument("--authorities")
    commands.add_parser(
        "authority-enrollment-contract",
        help="emit the V8 proof-of-possession enrollment boundary",
    )
    enrollment_verify = commands.add_parser(
        "authority-enrollment-verify",
        help="verify a V8 authority proof without granting authority",
    )
    enrollment_verify.add_argument("proof")
    commands.add_parser(
        "campaign-manifest",
        help="emit the exact V8 16-shard campaign topology",
    )
    campaign_status = commands.add_parser(
        "campaign-state",
        help="compute V8 ready subgraphs and the current true barrier",
    )
    campaign_status.add_argument("ledger")
    campaign_status.add_argument("authorities")
    campaign_run = commands.add_parser(
        "campaign-run",
        help="run every supplied ready V8 shard to the next barrier",
    )
    campaign_run.add_argument("ledger")
    campaign_run.add_argument("authorities")
    campaign_run.add_argument(
        "envelopes",
        help="JSON object mapping shard IDs to signed V7 envelopes",
    )
    campaign_run.add_argument("--output", help="write the resulting ledger")
    campaign_runtime = commands.add_parser(
        "campaign-runtime",
        help="compile the complete V8 parallel campaign runtime",
    )
    campaign_runtime.add_argument("--output", default="registry/v8")
    campaign_runtime.add_argument("--ledger")
    campaign_runtime.add_argument("--authorities")
    commands.add_parser(
        "threshold-governance-contract",
        help="emit the V9 3-of-5 authority-governance law",
    )
    commands.add_parser(
        "source-harvest-contract",
        help="emit the V9 harvest-once/fan-out evidence law",
    )
    harvest_verify = commands.add_parser(
        "source-harvest-verify",
        help="verify a V9 source manifest against the active handoff",
    )
    harvest_verify.add_argument("source_manifest")
    harvest_verify.add_argument("ledger")
    handoff_export = commands.add_parser(
        "handoff-bundle",
        help="compile the content-addressed V9 external request bundle",
    )
    handoff_export.add_argument("ledger")
    pin_verify = commands.add_parser(
        "authority-pin-verify",
        help="verify a V9 threshold authority-pin proposal",
    )
    pin_verify.add_argument("proposal")
    pin_verify.add_argument("governance")
    pin_verify.add_argument("authorities")
    pin_verify.add_argument("--verified-at", required=True)
    pin_admit = commands.add_parser(
        "authority-pin-admit",
        help="pin a candidate only after valid V9 threshold approval",
    )
    pin_admit.add_argument("proposal")
    pin_admit.add_argument("governance")
    pin_admit.add_argument("authorities")
    pin_admit.add_argument("--verified-at", required=True)
    pin_admit.add_argument("--output")
    handoff_run = commands.add_parser(
        "handoff-run",
        help="validate V9 handoff bindings and run ready campaign shards",
    )
    handoff_run.add_argument("ledger")
    handoff_run.add_argument("authorities")
    handoff_run.add_argument("envelopes")
    handoff_run.add_argument("--output")
    handoff_runtime = commands.add_parser(
        "handoff-runtime",
        help="compile the complete V9 external handoff runtime",
    )
    handoff_runtime.add_argument("--output", default="registry/v9")
    handoff_runtime.add_argument("--ledger")
    handoff_runtime.add_argument("--authorities")
    handoff_runtime.add_argument("--governance")
    commands.add_parser(
        "governance-ceremony-contract",
        help="emit the V10 participant-enrollment ceremony law",
    )
    commands.add_parser(
        "governance-ratification-contract",
        help="emit the V10 external-ratification law",
    )
    challenge = commands.add_parser(
        "governance-challenge",
        help="create a random role-bound V10 enrollment challenge",
    )
    challenge.add_argument("--role", required=True)
    challenge.add_argument("--authority-registry-digest", required=True)
    challenge.add_argument("--handoff-bundle-root", required=True)
    challenge.add_argument("--issued-at", required=True)
    challenge.add_argument("--expires-at", required=True)
    challenge.add_argument("--nonce")
    response_verify = commands.add_parser(
        "governance-response-verify",
        help="verify one signed V10 participant response",
    )
    response_verify.add_argument("response")
    response_verify.add_argument("--verified-at", required=True)
    society = commands.add_parser(
        "governance-society-assemble",
        help="assemble five responses into a pending society",
    )
    society.add_argument("responses", help="JSON array of five responses")
    society.add_argument("--verified-at", required=True)
    society.add_argument("--output")
    ratification = commands.add_parser(
        "governance-ratification-verify",
        help="verify external checkpoints over a pending society",
    )
    ratification.add_argument("pending_society")
    ratification.add_argument("ratification")
    ratification.add_argument("--verified-at", required=True)
    activation = commands.add_parser(
        "governance-activate",
        help="activate a ratified V10 governance society",
    )
    activation.add_argument("pending_society")
    activation.add_argument("ratification")
    activation.add_argument("--verified-at", required=True)
    activation.add_argument("--output")
    ceremony_runtime = commands.add_parser(
        "governance-ceremony",
        help="compile the complete V10 governance ceremony runtime",
    )
    ceremony_runtime.add_argument("--output", default="registry/v10")
    ceremony_runtime.add_argument("--ledger")
    ceremony_runtime.add_argument("--authorities")
    ceremony_runtime.add_argument("--governance")
    commands.add_parser(
        "governance-dispatch-contract",
        help="emit the V11 immutable challenge-dispatch law",
    )
    challenge_batch = commands.add_parser(
        "governance-challenge-batch",
        help="issue one immutable random challenge for each V11 role",
    )
    challenge_batch.add_argument(
        "--authority-registry-digest",
        required=True,
    )
    challenge_batch.add_argument("--handoff-bundle-root", required=True)
    challenge_batch.add_argument("--issued-at", required=True)
    challenge_batch.add_argument("--expires-at", required=True)
    challenge_batch.add_argument("--output", required=True)
    batch_state = commands.add_parser(
        "governance-challenge-batch-state",
        help="verify V11 challenge-batch integrity and lifecycle",
    )
    batch_state.add_argument("batch")
    batch_state.add_argument("--checked-at", required=True)
    response_route = commands.add_parser(
        "governance-response-route",
        help="route all supplied V11 responses as one intake wave",
    )
    response_route.add_argument("batch")
    response_route.add_argument(
        "responses",
        help="JSON array of zero to five participant responses",
    )
    response_route.add_argument("--verified-at", required=True)
    response_route.add_argument("--output")
    dispatch_runtime = commands.add_parser(
        "governance-dispatch",
        help="compile the complete V11 dispatch and intake runtime",
    )
    dispatch_runtime.add_argument("--output", default="registry/v11")
    dispatch_runtime.add_argument("--ledger")
    dispatch_runtime.add_argument("--authorities")
    dispatch_runtime.add_argument("--governance")
    dispatch_runtime.add_argument("--challenge-batch")
    dispatch_runtime.add_argument("--responses")
    dispatch_runtime.add_argument("--verified-at")
    commands.add_parser(
        "participant-handoff-contract",
        help="emit the V12 five-role external handoff law",
    )
    handoff_verify = commands.add_parser(
        "participant-handoff-verify",
        help="verify one signed response against its exact V12 packet",
    )
    handoff_verify.add_argument("batch")
    handoff_verify.add_argument("packet")
    handoff_verify.add_argument("response")
    handoff_verify.add_argument("--verified-at", required=True)
    participant_handoff = commands.add_parser(
        "participant-handoff",
        help="compile the complete V12 participant handoff runtime",
    )
    participant_handoff.add_argument("--output", default="registry/v12")
    participant_handoff.add_argument("--challenge-batch", required=True)
    participant_handoff.add_argument("--ledger")
    participant_handoff.add_argument("--authorities")
    participant_handoff.add_argument("--governance")
    participant_handoff.add_argument("--responses")
    participant_handoff.add_argument("--verified-at")
    commands.add_parser(
        "candidate-selection-contract",
        help="emit the V13 independence-qualified cohort law",
    )
    candidate_solve = commands.add_parser(
        "candidate-cohort-solve",
        help="solve all V13 role assignments without arbitrary selection",
    )
    candidate_solve.add_argument("nominations")
    candidate_solve.add_argument("--checked-at", required=True)
    candidate_solve.add_argument("--node-budget", type=int, default=100_000)
    candidate_runtime = commands.add_parser(
        "candidate-selection",
        help="compile the complete V13 candidate selection runtime",
    )
    candidate_runtime.add_argument("--output", default="registry/v13")
    candidate_runtime.add_argument("--challenge-batch", required=True)
    candidate_runtime.add_argument("--nominations")
    candidate_runtime.add_argument("--checked-at")
    candidate_runtime.add_argument(
        "--node-budget",
        type=int,
        default=100_000,
    )
    commands.add_parser(
        "nomination-intake-contract",
        help="emit the V14 signed candidate-intake law",
    )
    nomination_call = commands.add_parser(
        "nomination-role-call",
        help="emit one V14 role-bound candidate call",
    )
    nomination_call.add_argument("batch")
    nomination_call.add_argument("--role", required=True)
    nomination_verify = commands.add_parser(
        "candidate-nomination-verify",
        help="verify one signed V14 candidate nomination",
    )
    nomination_verify.add_argument("envelope")
    nomination_verify.add_argument("--checked-at", required=True)
    nomination_runtime = commands.add_parser(
        "nomination-intake",
        help="compile the complete V14 signed nomination intake runtime",
    )
    nomination_runtime.add_argument("--output", default="registry/v14")
    nomination_runtime.add_argument("--challenge-batch", required=True)
    nomination_runtime.add_argument("--envelopes")
    nomination_runtime.add_argument("--checked-at")
    nomination_runtime.add_argument(
        "--node-budget",
        type=int,
        default=100_000,
    )
    commands.add_parser(
        "application-transport-contract",
        help="emit the V15 batch-bound application transport law",
    )
    publication_payload = commands.add_parser(
        "application-publication-payload",
        help="emit one V15 publication-ready role-call payload",
    )
    publication_payload.add_argument("batch")
    publication_payload.add_argument("--role", required=True)
    application_verify = commands.add_parser(
        "candidate-application-verify",
        help="verify one batch-bound V15 candidate application",
    )
    application_verify.add_argument("batch")
    application_verify.add_argument("application")
    application_verify.add_argument("--checked-at", required=True)
    application_runtime = commands.add_parser(
        "application-transport",
        help="compile the complete V15 application transport runtime",
    )
    application_runtime.add_argument("--output", default="registry/v15")
    application_runtime.add_argument("--challenge-batch", required=True)
    application_runtime.add_argument("--applications")
    application_runtime.add_argument("--checked-at")
    application_runtime.add_argument(
        "--node-budget",
        type=int,
        default=100_000,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "build":
        document = write_crystal(args.output, args.atlas)
        _json(
            {
                "status": document["status"],
                "digest": document["digest"],
                "output": str(Path(args.output)),
            }
        )
        return 0

    if args.command == "audit":
        report = audit_crystal()
        if args.output:
            Path(args.output).write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        _json(report)
        return 0 if report["verdict"] == "PASS" else 1

    if args.command == "inspect":
        crystal = crystallize()
        if not 1 <= args.gid <= 144:
            raise SystemExit("gid must be 1..144")
        _json(crystal["seats"][args.gid - 1])
        return 0

    if args.command == "body":
        if not 1 <= args.gid <= 144:
            raise SystemExit("gid must be 1..144")
        _json(build_station_bodies()[args.gid - 1])
        return 0

    if args.command == "navigate":
        if not (1 <= args.start <= 144 and 1 <= args.target <= 144):
            raise SystemExit("start and target must be 1..144")
        graph = adjacency(navigation_relations())
        path = shortest_path(args.start, args.target, graph)
        _json(
            {
                "source": args.start,
                "target": args.target,
                "path": path,
                "hops": max(0, len(path) - 1),
                "verdict": "FOUND" if path else "UNREACHABLE",
                "standing": "DECLARED_GRAPH_ROUTE_NOT_TRANSPORT_CERTIFICATION",
            }
        )
        return 0

    if args.command == "navigation-audit":
        _json(navigation_report())
        return 0

    if args.command == "bridges":
        _json(bridge_registry())
        return 0

    if args.command == "holonomy":
        _json(measure_holonomy())
        return 0

    if args.command == "replay-ablation":
        _json(replay_ablation())
        return 0

    if args.command == "frontier":
        _json(frontier_ledger())
        return 0

    if args.command == "wave":
        starts = tuple(int(value) for value in args.starts.split(",") if value)
        _json(propagate(WaveQuery(args.query_id, starts, args.budget)))
        return 0

    if args.command == "parallel-routes":
        binding_values = {
            "immutable_commit": args.immutable_commit,
            "immutable_tree": args.immutable_tree,
            "compiler_commit": args.compiler_commit,
            "compiler_tree": args.compiler_tree,
        }
        supplied = {key: value for key, value in binding_values.items() if value}
        if supplied and len(supplied) != len(binding_values):
            raise SystemExit("all four coordinate-binding options are required together")
        result = compile_parallel_route_crystal(
            executor_workers=args.workers,
            coordinate_binding=supplied or None,
        )
        if args.output:
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(
                    result,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            _json(
                {
                    "schema": result["schema"],
                    "output": str(destination),
                    "crystal_digest": result["crystal_digest"],
                    "simulations": len(result["simulations"]),
                    "maximum_parallel_width": result["scheduler"][
                        "maximum_parallel_width"
                    ],
                    "production_truth_effect": result["production_truth_effect"],
                }
            )
        else:
            _json(result)
        return 0

    if args.command == "mycelium-tools":
        _json(mycelium_tool_registry())
        return 0

    if args.command == "mycelium-locate":
        starts = tuple(int(value) for value in _csv(args.starts))
        report = locate_mycelium_tool(
            args.query,
            start_coordinates=starts,
            route_budget=args.budget,
        )
        _json(report)
        return 0 if report["status"] == "FOUND" else 2

    if args.command == "agent-run-plan":
        source = json.loads(Path(args.source).read_text(encoding="utf-8"))
        _json(build_agent_run_plan(source))
        return 0

    if args.command == "agent-run-receipts":
        source = json.loads(Path(args.source).read_text(encoding="utf-8"))
        binding_values = {
            "runtime_commit": args.runtime_commit,
            "runtime_tree": args.runtime_tree,
            "source_snapshot_digest": args.source_snapshot_digest,
        }
        supplied = {key: value for key, value in binding_values.items() if value}
        if supplied and len(supplied) != len(binding_values):
            raise SystemExit(
                "all three runtime-binding options are required together"
            )
        report = compile_agent_run_receipts(
            source,
            executor_workers=args.workers,
            runtime_binding=supplied or None,
        )
        if args.output:
            destination = Path(args.output)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                json.dumps(
                    report,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n",
                encoding="utf-8",
            )
            _json(
                {
                    "schema": report["schema"],
                    "output": str(destination),
                    "run_id": report["manifest"]["run_id"],
                    "manifest_digest": report["manifest"]["manifest_digest"],
                    "audit_root": report["manifest"]["audit_root"],
                    "accepted_receipts": len(report["receipts"]),
                    "production_truth_effect": report[
                        "production_truth_effect"
                    ],
                }
            )
        else:
            _json(report)
        return 0

    if args.command == "agent-run-verify":
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        source = (
            json.loads(Path(args.source).read_text(encoding="utf-8"))
            if args.source
            else None
        )
        report = verify_agent_run_receipts(bundle, source_crystal=source)
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "systematic":
        release = compile_systematic_framework(args.output)
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "query":
        if args.file:
            query_value = json.loads(Path(args.file).read_text(encoding="utf-8"))
            bundle = QueryBundle.from_dict(query_value)
        else:
            if not args.goal:
                raise SystemExit("--goal is required when --file is not supplied")
            bundle = QueryBundle(
                query_id=args.query_id,
                goal=args.goal,
                terms=_csv(args.terms),
                domains=_csv(args.domains),
                operators=_csv(args.operators),
                invariants=_csv(args.invariants),
                boundaries=_csv(args.boundaries),
                evidence_floor=args.evidence_floor,
                start_coordinates=tuple(
                    int(value) for value in _csv(args.starts)
                ),
                route_budget=args.budget,
                return_mode=args.return_mode,
                max_results=args.max_results,
            )
        report = compile_query(bundle)
        _json(report)
        return 0 if report["status"] == "COMPILED" else 2

    if args.command == "query-contract":
        _json(query_contract())
        return 0

    if args.command == "bridge-witness":
        packet = BridgeWitnessPacket.from_dict(
            json.loads(Path(args.packet).read_text(encoding="utf-8"))
        )
        report = evaluate_bridge_witness(packet)
        _json(report)
        return 0 if report["verdict"] == "CERTIFIED" else 2

    if args.command == "bridge-witness-contract":
        _json(bridge_witness_contract())
        return 0

    if args.command == "mycelium":
        release = compile_mycelium_framework(args.output)
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "edge-manifest":
        _json(freeze_edge_manifest())
        return 0

    if args.command == "session":
        spec = (
            SessionSpec.from_dict(
                json.loads(Path(args.file).read_text(encoding="utf-8"))
            )
            if args.file
            else default_session_spec()
        )
        _json(compile_session(spec))
        return 0

    if args.command == "cold-reconstruct":
        report = cold_reconstruct(
            json.loads(Path(args.seed).read_text(encoding="utf-8"))
        )
        _json(report)
        return 0 if report["verdict"] == "PASS" else 1

    if args.command == "bridge-prepare":
        packet = BridgeWitnessPacket.from_dict(
            json.loads(Path(args.packet).read_text(encoding="utf-8"))
        )
        report = prepare_bridge_commit(packet)
        _json(report)
        return 0 if report["status"] == "PREPARED" else 2

    if args.command == "bridge-commit":
        packet = BridgeWitnessPacket.from_dict(
            json.loads(Path(args.packet).read_text(encoding="utf-8"))
        )
        preparation = json.loads(
            Path(args.preparation).read_text(encoding="utf-8")
        )
        authorization = CommitAuthorization(
            **json.loads(Path(args.authorization).read_text(encoding="utf-8"))
        )
        report = commit_bridge(
            preparation,
            packet,
            authorization,
            namespace=args.namespace,
        )
        _json(report)
        return 0 if report["status"] == "COMMITTED" else 2

    if args.command == "global-state":
        release = compile_global_state(args.output)
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "m12-evidence-contract":
        _json(evidence_packet_contract())
        return 0

    if args.command == "m12-repair-plan":
        ledger = (
            json.loads(Path(args.ledger).read_text(encoding="utf-8"))
            if args.ledger
            else empty_repair_ledger()
        )
        _json(repair_plan(ledger))
        return 0

    if args.command == "m12-evidence-admit":
        packet = M12EvidencePacket.from_dict(
            json.loads(Path(args.packet).read_text(encoding="utf-8"))
        )
        ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
        report = admit_evidence(ledger, packet)
        if args.output and report["status"] == "ADMITTED":
            Path(args.output).write_text(
                json.dumps(report["ledger"], indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        _json(report)
        return 0 if report["status"] == "ADMITTED" else 2

    if args.command == "repair":
        release = compile_repair_framework(args.output)
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "production-evidence-contract":
        _json(production_evidence_contract())
        return 0

    if args.command in {
        "evidence-envelope-verify",
        "evidence-envelope-admit",
    }:
        envelope = SignedEvidenceEnvelope.from_dict(
            json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        )
        ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
        authorities = json.loads(
            Path(args.authorities).read_text(encoding="utf-8")
        )
        report = (
            verify_signed_envelope(envelope, authorities, ledger)
            if args.command == "evidence-envelope-verify"
            else admit_signed_envelope(ledger, envelope, authorities)
        )
        if (
            args.command == "evidence-envelope-admit"
            and args.output
            and report["status"] == "ADMITTED"
        ):
            Path(args.output).write_text(
                json.dumps(report["ledger"], indent=2, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
        _json(report)
        successful = (
            report["verdict"] == "PASS"
            if args.command == "evidence-envelope-verify"
            else report["status"] == "ADMITTED"
        )
        return 0 if successful else 2

    if args.command == "evidence-kernel":
        ledger = (
            json.loads(Path(args.ledger).read_text(encoding="utf-8"))
            if args.ledger
            else None
        )
        authorities = (
            json.loads(
                Path(args.authorities).read_text(encoding="utf-8")
            )
            if args.authorities
            else None
        )
        release = compile_production_evidence_kernel(
            args.output,
            ledger=ledger,
            authority_registry=authorities,
        )
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "authority-enrollment-contract":
        _json(authority_enrollment_contract())
        return 0

    if args.command == "authority-enrollment-verify":
        proof = AuthorityEnrollmentProof.from_dict(
            json.loads(Path(args.proof).read_text(encoding="utf-8"))
        )
        report = verify_authority_enrollment(proof)
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "campaign-manifest":
        _json(campaign_manifest())
        return 0

    if args.command == "campaign-state":
        ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
        authorities = json.loads(
            Path(args.authorities).read_text(encoding="utf-8")
        )
        _json(campaign_state(ledger, authorities))
        return 0

    if args.command == "campaign-run":
        ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
        authorities = json.loads(
            Path(args.authorities).read_text(encoding="utf-8")
        )
        raw_envelopes = json.loads(
            Path(args.envelopes).read_text(encoding="utf-8")
        )
        envelopes = {
            shard_id: SignedEvidenceEnvelope.from_dict(value)
            for shard_id, value in raw_envelopes.items()
        }
        report = run_to_barrier(ledger, authorities, envelopes)
        if args.output and report["admitted_shards"]:
            Path(args.output).write_text(
                json.dumps(report["ledger"], indent=2, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
        _json(report)
        return 0 if not report["held_shards"] else 2

    if args.command == "campaign-runtime":
        ledger = (
            json.loads(Path(args.ledger).read_text(encoding="utf-8"))
            if args.ledger
            else None
        )
        authorities = (
            json.loads(
                Path(args.authorities).read_text(encoding="utf-8")
            )
            if args.authorities
            else None
        )
        release = compile_parallel_campaign_runtime(
            args.output,
            ledger=ledger,
            authority_registry=authorities,
        )
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "threshold-governance-contract":
        _json(threshold_governance_contract())
        return 0

    if args.command == "source-harvest-contract":
        _json(source_harvest_contract())
        return 0

    if args.command == "source-harvest-verify":
        source_manifest = json.loads(
            Path(args.source_manifest).read_text(encoding="utf-8")
        )
        ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
        report = verify_source_harvest(
            source_manifest,
            handoff_bundle(ledger),
        )
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "handoff-bundle":
        ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
        _json(handoff_bundle(ledger))
        return 0

    if args.command in {"authority-pin-verify", "authority-pin-admit"}:
        proposal = AuthorityPinProposal.from_dict(
            json.loads(Path(args.proposal).read_text(encoding="utf-8"))
        )
        governance = json.loads(
            Path(args.governance).read_text(encoding="utf-8")
        )
        authorities = json.loads(
            Path(args.authorities).read_text(encoding="utf-8")
        )
        report = (
            verify_authority_pin_proposal(
                proposal,
                governance,
                authorities,
                verified_at=args.verified_at,
            )
            if args.command == "authority-pin-verify"
            else pin_authority_from_proposal(
                proposal,
                governance,
                authorities,
                verified_at=args.verified_at,
            )
        )
        if (
            args.command == "authority-pin-admit"
            and args.output
            and report["status"] == "PINNED"
        ):
            Path(args.output).write_text(
                json.dumps(report["registry"], indent=2, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
        _json(report)
        successful = (
            report["verdict"] == "PASS"
            if args.command == "authority-pin-verify"
            else report["status"] == "PINNED"
        )
        return 0 if successful else 2

    if args.command == "handoff-run":
        ledger = json.loads(Path(args.ledger).read_text(encoding="utf-8"))
        authorities = json.loads(
            Path(args.authorities).read_text(encoding="utf-8")
        )
        envelopes = {
            shard_id: SignedEvidenceEnvelope.from_dict(value)
            for shard_id, value in json.loads(
                Path(args.envelopes).read_text(encoding="utf-8")
            ).items()
        }
        report = run_handoff_to_barrier(
            ledger,
            authorities,
            envelopes,
        )
        if args.output and report["campaign_report"]["admitted_shards"]:
            Path(args.output).write_text(
                json.dumps(report["ledger"], indent=2, ensure_ascii=False)
                + "\n",
                encoding="utf-8",
            )
        _json(report)
        return 0 if not report["handoff_held_shards"] else 2

    if args.command == "handoff-runtime":
        ledger = (
            json.loads(Path(args.ledger).read_text(encoding="utf-8"))
            if args.ledger
            else None
        )
        authorities = (
            json.loads(
                Path(args.authorities).read_text(encoding="utf-8")
            )
            if args.authorities
            else None
        )
        governance = (
            json.loads(
                Path(args.governance).read_text(encoding="utf-8")
            )
            if args.governance
            else None
        )
        release = compile_external_handoff_runtime(
            args.output,
            ledger=ledger,
            authority_registry=authorities,
            governance_registry=governance,
        )
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "governance-ceremony-contract":
        _json(governance_ceremony_contract())
        return 0

    if args.command == "governance-ratification-contract":
        _json(governance_ratification_contract())
        return 0

    if args.command == "governance-challenge":
        challenge = create_governance_challenge(
            args.role,
            authority_registry_digest=args.authority_registry_digest,
            handoff_bundle_root=args.handoff_bundle_root,
            issued_at=args.issued_at,
            expires_at=args.expires_at,
            nonce=args.nonce,
        )
        _json(challenge.to_dict())
        return 0

    if args.command == "governance-response-verify":
        response = GovernanceEnrollmentResponse.from_dict(
            json.loads(Path(args.response).read_text(encoding="utf-8"))
        )
        report = verify_enrollment_response(
            response,
            verified_at=args.verified_at,
        )
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "governance-society-assemble":
        responses = [
            GovernanceEnrollmentResponse.from_dict(value)
            for value in json.loads(
                Path(args.responses).read_text(encoding="utf-8")
            )
        ]
        report = assemble_pending_society(
            responses,
            verified_at=args.verified_at,
        )
        if args.output and report["verdict"] == "PASS":
            Path(args.output).write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command in {
        "governance-ratification-verify",
        "governance-activate",
    }:
        pending = json.loads(
            Path(args.pending_society).read_text(encoding="utf-8")
        )
        ratification = GovernanceRatification.from_dict(
            json.loads(Path(args.ratification).read_text(encoding="utf-8"))
        )
        report = (
            verify_governance_ratification(
                pending,
                ratification,
                verified_at=args.verified_at,
            )
            if args.command == "governance-ratification-verify"
            else activate_governance_society(
                pending,
                ratification,
                verified_at=args.verified_at,
            )
        )
        if (
            args.command == "governance-activate"
            and args.output
            and report["status"] == "ACTIVATED"
        ):
            Path(args.output).write_text(
                json.dumps(
                    report["governance_registry"],
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
        _json(report)
        successful = (
            report["verdict"] == "PASS"
            if args.command == "governance-ratification-verify"
            else report["status"] == "ACTIVATED"
        )
        return 0 if successful else 2

    if args.command == "governance-ceremony":
        ledger = (
            json.loads(Path(args.ledger).read_text(encoding="utf-8"))
            if args.ledger
            else None
        )
        authorities = (
            json.loads(
                Path(args.authorities).read_text(encoding="utf-8")
            )
            if args.authorities
            else None
        )
        governance = (
            json.loads(
                Path(args.governance).read_text(encoding="utf-8")
            )
            if args.governance
            else None
        )
        release = compile_governance_ceremony_runtime(
            args.output,
            ledger=ledger,
            authority_registry=authorities,
            governance_registry=governance,
        )
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "governance-dispatch-contract":
        _json(governance_dispatch_contract())
        return 0

    if args.command == "governance-challenge-batch":
        batch = issue_governance_challenge_batch(
            authority_registry_digest=args.authority_registry_digest,
            handoff_bundle_root=args.handoff_bundle_root,
            issued_at=args.issued_at,
            expires_at=args.expires_at,
        )
        Path(args.output).write_text(
            json.dumps(batch, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        _json(batch)
        return 0

    if args.command == "governance-challenge-batch-state":
        batch = json.loads(Path(args.batch).read_text(encoding="utf-8"))
        report = governance_challenge_batch_state(
            batch,
            checked_at=args.checked_at,
        )
        _json(report)
        return 0 if report["integrity"] == "PASS" else 2

    if args.command == "governance-response-route":
        batch = json.loads(Path(args.batch).read_text(encoding="utf-8"))
        responses = [
            GovernanceEnrollmentResponse.from_dict(value)
            for value in json.loads(
                Path(args.responses).read_text(encoding="utf-8")
            )
        ]
        report = route_governance_responses(
            batch,
            responses,
            verified_at=args.verified_at,
        )
        if args.output:
            Path(args.output).write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        _json(report)
        return (
            0
            if report["batch_state"]["integrity"] == "PASS"
            else 2
        )

    if args.command == "governance-dispatch":
        ledger = (
            json.loads(Path(args.ledger).read_text(encoding="utf-8"))
            if args.ledger
            else None
        )
        authorities = (
            json.loads(
                Path(args.authorities).read_text(encoding="utf-8")
            )
            if args.authorities
            else None
        )
        governance = (
            json.loads(
                Path(args.governance).read_text(encoding="utf-8")
            )
            if args.governance
            else None
        )
        batch = (
            json.loads(
                Path(args.challenge_batch).read_text(encoding="utf-8")
            )
            if args.challenge_batch
            else None
        )
        responses = (
            tuple(
                GovernanceEnrollmentResponse.from_dict(value)
                for value in json.loads(
                    Path(args.responses).read_text(encoding="utf-8")
                )
            )
            if args.responses
            else ()
        )
        if responses and not args.verified_at:
            raise SystemExit(
                "--verified-at is required when --responses is supplied"
            )
        release = compile_governance_dispatch_runtime(
            args.output,
            ledger=ledger,
            authority_registry=authorities,
            governance_registry=governance,
            challenge_batch=batch,
            responses=responses,
            verified_at=args.verified_at,
        )
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "participant-handoff-contract":
        _json(participant_handoff_contract())
        return 0

    if args.command == "participant-handoff-verify":
        batch = json.loads(Path(args.batch).read_text(encoding="utf-8"))
        packet = json.loads(Path(args.packet).read_text(encoding="utf-8"))
        response = GovernanceEnrollmentResponse.from_dict(
            json.loads(Path(args.response).read_text(encoding="utf-8"))
        )
        report = verify_response_for_handoff_packet(
            batch,
            packet,
            response,
            verified_at=args.verified_at,
        )
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "participant-handoff":
        ledger = (
            json.loads(Path(args.ledger).read_text(encoding="utf-8"))
            if args.ledger
            else None
        )
        authorities = (
            json.loads(
                Path(args.authorities).read_text(encoding="utf-8")
            )
            if args.authorities
            else None
        )
        governance = (
            json.loads(
                Path(args.governance).read_text(encoding="utf-8")
            )
            if args.governance
            else None
        )
        batch = json.loads(
            Path(args.challenge_batch).read_text(encoding="utf-8")
        )
        responses = (
            tuple(
                GovernanceEnrollmentResponse.from_dict(value)
                for value in json.loads(
                    Path(args.responses).read_text(encoding="utf-8")
                )
            )
            if args.responses
            else ()
        )
        if responses and not args.verified_at:
            raise SystemExit(
                "--verified-at is required when --responses is supplied"
            )
        release = compile_participant_handoff_runtime(
            args.output,
            ledger=ledger,
            authority_registry=authorities,
            governance_registry=governance,
            challenge_batch=batch,
            responses=responses,
            verified_at=args.verified_at,
        )
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "candidate-selection-contract":
        _json(candidate_selection_contract())
        return 0

    if args.command == "candidate-cohort-solve":
        nominations = tuple(
            CandidateNomination.from_dict(value)
            for value in json.loads(
                Path(args.nominations).read_text(encoding="utf-8")
            )
        )
        report = solve_candidate_cohort(
            nominations,
            checked_at=args.checked_at,
            node_budget=args.node_budget,
        )
        _json(report)
        return 0

    if args.command == "candidate-selection":
        batch = json.loads(
            Path(args.challenge_batch).read_text(encoding="utf-8")
        )
        nominations = (
            tuple(
                CandidateNomination.from_dict(value)
                for value in json.loads(
                    Path(args.nominations).read_text(encoding="utf-8")
                )
            )
            if args.nominations
            else ()
        )
        release = compile_candidate_selection_runtime(
            args.output,
            challenge_batch=batch,
            nominations=nominations,
            checked_at=args.checked_at,
            node_budget=args.node_budget,
        )
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "nomination-intake-contract":
        _json(nomination_intake_contract())
        return 0

    if args.command == "nomination-role-call":
        batch = json.loads(
            Path(args.batch).read_text(encoding="utf-8")
        )
        _json(nomination_role_call(batch, args.role))
        return 0

    if args.command == "candidate-nomination-verify":
        envelope = SignedCandidateNomination.from_dict(
            json.loads(
                Path(args.envelope).read_text(encoding="utf-8")
            )
        )
        report = verify_signed_candidate_nomination(
            envelope,
            checked_at=args.checked_at,
        )
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "nomination-intake":
        batch = json.loads(
            Path(args.challenge_batch).read_text(encoding="utf-8")
        )
        envelopes = (
            tuple(
                SignedCandidateNomination.from_dict(value)
                for value in json.loads(
                    Path(args.envelopes).read_text(encoding="utf-8")
                )
            )
            if args.envelopes
            else ()
        )
        release = compile_nomination_intake_runtime(
            args.output,
            challenge_batch=batch,
            envelopes=envelopes,
            checked_at=args.checked_at,
            node_budget=args.node_budget,
        )
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    if args.command == "application-transport-contract":
        _json(application_transport_contract())
        return 0

    if args.command == "application-publication-payload":
        batch = json.loads(
            Path(args.batch).read_text(encoding="utf-8")
        )
        calls = [nomination_role_call(batch, role) for role in ROLES]
        manifest = nomination_call_manifest(batch, calls)
        call = next(
            value for value in calls if value["role"] == args.role
        )
        _json(application_publication_payload(batch, call, manifest))
        return 0

    if args.command == "candidate-application-verify":
        batch = json.loads(
            Path(args.batch).read_text(encoding="utf-8")
        )
        application = BatchBoundCandidateApplication.from_dict(
            json.loads(
                Path(args.application).read_text(encoding="utf-8")
            )
        )
        calls = [nomination_role_call(batch, role) for role in ROLES]
        manifest = nomination_call_manifest(batch, calls)
        report = verify_batch_bound_application(
            batch,
            calls,
            manifest,
            application,
            checked_at=args.checked_at,
        )
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "application-transport":
        batch = json.loads(
            Path(args.challenge_batch).read_text(encoding="utf-8")
        )
        applications = (
            tuple(
                BatchBoundCandidateApplication.from_dict(value)
                for value in json.loads(
                    Path(args.applications).read_text(encoding="utf-8")
                )
            )
            if args.applications
            else ()
        )
        release = compile_application_transport_runtime(
            args.output,
            challenge_batch=batch,
            applications=applications,
            checked_at=args.checked_at,
            node_budget=args.node_budget,
        )
        _json(release)
        return 0 if release["verdict"] == "PASS" else 1

    transforms = {
        "grid-r90": lambda: grid_d4_view(args.gid, "r90"),
        "x16-next": lambda: x16_schedule_rotate(args.gid, 1, 1),
        "br-mirror": lambda: br_mirror(args.gid),
        "kc27-J": lambda: kc27_transform(args.gid, signs=(-1, -1, -1)),
        "sigma": lambda: coactivation_sigma(args.gid),
    }
    _json(transforms[args.operation]().to_dict())
    return 0
