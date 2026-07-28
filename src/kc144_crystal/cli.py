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
from .p31_adapter import ExactP31Archive, navigate_exact_p31
from .p36_runtime import (
    compile_p36_cycle,
    compile_p36_release,
    p36_contract,
    p36_tool_registry,
    public_projection,
    verify_p36_cycle,
)
from .p37_reconciliation import (
    bind_exact_p35_registry,
    p37_public_reconciliation,
)
from .p38_runtime import (
    P38_CUTOFF,
    compile_multi_crystal_query,
    compile_p38_cycle,
    compile_p38_release,
    coordinate_tensor_144,
    p38_contract,
    route_source_events,
    verify_p38_cycle,
)
from .p39_runtime import (
    P39_CUTOFF,
    calibrate_weights,
    compile_live_outcome_corpus,
    compile_p39_cycle,
    compile_p39_release,
    p39_contract,
    p39_policy,
    verify_p39_cycle,
)
from .p40_runtime import (
    P40_CUTOFF,
    build_canonical_weight_state,
    compile_p40_cycle,
    compile_p40_release,
    p40_contract,
    p40_sibling_capsule,
    verify_p40_cycle,
)
from .p41_runtime import (
    compile_p41_cycle,
    compile_p41_release,
    freeze_heldout_cohort,
    p41_contract,
    p41_repository_forest,
    p41_source_manifest,
    verify_p41_cycle,
)
from .p42_runtime import (
    compile_p42_cycle,
    compile_p42_release,
    p42_contract,
    verify_p42_cycle,
)
from .p43_runtime import (
    compile_p43_cycle,
    compile_p43_release,
    p43_contract,
    verify_p43_cycle,
)
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
from .tool_dispatch import (
    build_dispatch_head_registry,
    compile_tool_dispatch_runtime,
    compile_tool_dispatch_plan,
    dispatch_mycelium_tool,
    tool_dispatch_contract,
    verify_tool_dispatch_result,
)
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

    commands.add_parser(
        "tool-dispatch-contract",
        help="emit the fail-closed content-addressed dispatch contract",
    )
    dispatch_heads = commands.add_parser(
        "tool-dispatch-heads",
        help="freeze the code-identity head registry for dispatch replay",
    )
    dispatch_heads.add_argument("--implementation-commit", required=True)
    dispatch_heads.add_argument("--implementation-tree", required=True)
    dispatch_heads.add_argument("--supersedes-registry-digest")
    dispatch_plan = commands.add_parser(
        "tool-dispatch-plan",
        help="compile five-lane preflight for a dispatch request",
    )
    dispatch_plan.add_argument("request")
    dispatch_plan.add_argument("heads")
    dispatch_plan.add_argument("--workers", type=int, default=5)
    dispatch_run = commands.add_parser(
        "tool-dispatch",
        help="execute only an exactly registered in-process tool handler",
    )
    dispatch_run.add_argument("request")
    dispatch_run.add_argument("heads")
    dispatch_run.add_argument("--workers", type=int, default=5)
    dispatch_run.add_argument("--output")
    dispatch_verify = commands.add_parser(
        "tool-dispatch-verify",
        help="verify and cold-replay a dispatch result",
    )
    dispatch_verify.add_argument("result")
    dispatch_verify.add_argument("heads")
    dispatch_verify.add_argument(
        "--no-cold-replay", action="store_true"
    )
    dispatch_runtime = commands.add_parser(
        "tool-dispatch-runtime",
        help="compile the complete frozen V1 tool-dispatch release",
    )
    dispatch_runtime.add_argument("--output", default="registry/tool-dispatch/v1")
    dispatch_runtime.add_argument("--implementation-commit", required=True)
    dispatch_runtime.add_argument("--implementation-tree", required=True)
    dispatch_runtime.add_argument("--source", required=True)
    dispatch_runtime.add_argument("--bundle", required=True)

    p31_status = commands.add_parser(
        "p31-exact-status",
        help="verify and inspect the exact immutable P31 runtime archive",
    )
    p31_status.add_argument("--archive", required=True)
    p31_navigate = commands.add_parser(
        "p31-exact-navigate",
        help="navigate through the exact P31 archive adapter",
    )
    p31_navigate.add_argument("query")
    p31_navigate.add_argument("--archive", required=True)
    p31_navigate.add_argument("--policy", default="minimum_defect")
    p31_navigate.add_argument("--hop-budget", type=int)
    commands.add_parser(
        "p36-contract",
        help="emit the source-steered five-lane P36 contract",
    )
    commands.add_parser(
        "p36-tools",
        help="emit the versioned P31-adapter and P36 tool registry",
    )
    p36_cycle = commands.add_parser(
        "p36-cycle",
        help="compile one bounded caller-supplied P36 event epoch",
    )
    p36_cycle.add_argument("events", help="JSON array of event envelopes")
    p36_cycle.add_argument("subscriptions", help="subscription registry JSON")
    p36_cycle.add_argument("--base-state-digest", required=True)
    p36_cycle.add_argument("--cutoff", required=True)
    p36_cycle.add_argument("--parent-receipts")
    p36_cycle.add_argument("--output")
    p36_verify = commands.add_parser(
        "p36-verify",
        help="verify one frozen P36 macrocycle without connector reads",
    )
    p36_verify.add_argument("envelope")
    p36_project = commands.add_parser(
        "p36-public-project",
        help="emit the privacy-safe public projection of a P36 macrocycle",
    )
    p36_project.add_argument("envelope")
    p36_release = commands.add_parser(
        "p36-release",
        help="materialize the candidate-HOLD P36 reference release",
    )
    p36_release.add_argument("--output", default="registry/p36-dispatch/v1")
    p36_release.add_argument("--implementation-commit", required=True)
    p36_release.add_argument("--implementation-tree", required=True)

    commands.add_parser(
        "p37-reconcile",
        help="emit the non-collapsing public-P36/source-P37 reconciliation",
    )
    p35_bind = commands.add_parser(
        "p35-registry-bind",
        help="verify and commit to all exact P35 subscription registry bytes",
    )
    p35_bind.add_argument("directory")
    commands.add_parser(
        "p38-contract",
        help="emit the seven-lane P38 Meta Navigator V2 contract",
    )
    commands.add_parser(
        "p38-coordinate-tensor",
        help="emit all 144 simultaneous mathematical transformation views",
    )
    p38_query = commands.add_parser(
        "p38-query",
        help="compile one typed query across the selected crystal lenses",
    )
    p38_query.add_argument("query")
    p38_source = commands.add_parser(
        "p38-source-route",
        help="route typed source events without conflating source surfaces",
    )
    p38_source.add_argument("events")
    p38_source.add_argument("--cutoff", default=P38_CUTOFF)
    p38_cycle = commands.add_parser(
        "p38-cycle",
        help="compile one complete seven-lane P38 macrocycle",
    )
    p38_cycle.add_argument("query")
    p38_cycle.add_argument("registry_binding")
    p38_cycle.add_argument("--source-events")
    p38_cycle.add_argument("--outcomes")
    p38_cycle.add_argument("--signer-registry")
    p38_cycle.add_argument("--ic10-returns")
    p38_cycle.add_argument("--cutoff", default=P38_CUTOFF)
    p38_cycle.add_argument("--output")
    p38_verify = commands.add_parser(
        "p38-verify",
        help="verify one frozen P38 macrocycle",
    )
    p38_verify.add_argument("envelope")
    p38_release = commands.add_parser(
        "p38-release",
        help="materialize the candidate-HOLD P38 reference release",
    )
    p38_release.add_argument("--output", default="registry/p38-meta-navigator/v1")
    p38_release.add_argument("--implementation-commit", required=True)
    p38_release.add_argument("--implementation-tree", required=True)
    p38_release.add_argument("--registry-directory")
    p38_release.add_argument("--source-events")
    commands.add_parser(
        "p39-contract",
        help="emit the P39 live-outcome and three-of-five IC10 contract",
    )
    commands.add_parser(
        "p39-policy",
        help="emit the deterministic P39 calibration and convergence policy",
    )
    p39_corpus = commands.add_parser(
        "p39-corpus",
        help="verify and partition signed live outcome observations",
    )
    p39_corpus.add_argument("observations")
    p39_corpus.add_argument("--cutoff", default=P39_CUTOFF)
    p39_calibrate = commands.add_parser(
        "p39-calibrate",
        help="propose deterministic weights from a verified P39 corpus",
    )
    p39_calibrate.add_argument("corpus")
    p39_cycle = commands.add_parser(
        "p39-cycle",
        help="compile one complete P39 outcome/IC10 macrocycle",
    )
    p39_cycle.add_argument("--observations")
    p39_cycle.add_argument("--signer-registry")
    p39_cycle.add_argument("--ic10-returns")
    p39_cycle.add_argument("--cutoff", default=P39_CUTOFF)
    p39_cycle.add_argument("--output")
    p39_verify = commands.add_parser(
        "p39-verify",
        help="verify one frozen P39 macrocycle",
    )
    p39_verify.add_argument("envelope")
    p39_release = commands.add_parser(
        "p39-release",
        help="materialize the honest-HOLD P39 reference release",
    )
    p39_release.add_argument("--output", default="registry/p39-live-outcome/v1")
    p39_release.add_argument("--implementation-commit", required=True)
    p39_release.add_argument("--implementation-tree", required=True)
    commands.add_parser(
        "p40-contract",
        help="emit the lineage-safe P40 activation transaction contract",
    )
    commands.add_parser(
        "p40-sibling",
        help="emit the exact reference-only sibling P40 lineage capsule",
    )
    p40_state = commands.add_parser(
        "p40-state",
        help="compile a canonical weight state for compare-and-swap activation",
    )
    p40_state.add_argument("--weights")
    p40_state.add_argument("--generation", type=int, default=0)
    p40_state.add_argument("--parent-state-root")
    p40_cycle = commands.add_parser(
        "p40-cycle",
        help="compile one complete P40 authorization/commit/watch macrocycle",
    )
    p40_cycle.add_argument("--p39-cycle")
    p40_cycle.add_argument("--canonical-state")
    p40_cycle.add_argument("--expected-base-state-root")
    p40_cycle.add_argument("--sibling-capsule")
    p40_cycle.add_argument(
        "--namespace", choices=("PRODUCTION", "TEST"), default="PRODUCTION"
    )
    p40_cycle.add_argument("--cutoff", default=P40_CUTOFF)
    p40_cycle.add_argument("--output")
    p40_verify = commands.add_parser(
        "p40-verify",
        help="verify and cold-replay one frozen P40 macrocycle",
    )
    p40_verify.add_argument("envelope")
    p40_release = commands.add_parser(
        "p40-release",
        help="materialize the lineage-safe honest-HOLD P40 reference release",
    )
    p40_release.add_argument(
        "--output", default="registry/p40-activation/v1"
    )
    p40_release.add_argument("--implementation-commit", required=True)
    p40_release.add_argument("--implementation-tree", required=True)
    commands.add_parser(
        "p41-contract",
        help="emit the P41 source/tree/cohort/edge/IC10 contract",
    )
    commands.add_parser(
        "p41-source",
        help="emit the nonleaking 29-body source commitment manifest",
    )
    commands.add_parser(
        "p41-trees",
        help="emit the exact public AthenachkaCollective repository forest",
    )
    p41_cohort = commands.add_parser(
        "p41-cohort",
        help="freeze a nonleaking held-out outcome cohort",
    )
    p41_cohort.add_argument("--events")
    p41_cycle = commands.add_parser(
        "p41-cycle",
        help="compile one complete P41 source/tree/cohort/edge/IC10 macrocycle",
    )
    p41_cycle.add_argument("--events")
    p41_cycle.add_argument("--ic10-registry")
    p41_cycle.add_argument("--ic10-returns")
    p41_cycle.add_argument(
        "--namespace", choices=("PRODUCTION", "TEST"), default="PRODUCTION"
    )
    p41_cycle.add_argument("--output")
    p41_verify = commands.add_parser(
        "p41-verify",
        help="verify and cold-replay one frozen P41 macrocycle",
    )
    p41_verify.add_argument("envelope")
    p41_release = commands.add_parser(
        "p41-release",
        help="materialize the nonleaking honest-HOLD P41 reference release",
    )
    p41_release.add_argument(
        "--output", default="registry/p41-source-tree-cohort/v1"
    )
    p41_release.add_argument("--implementation-commit", required=True)
    p41_release.add_argument("--implementation-tree", required=True)
    commands.add_parser(
        "p42-contract",
        help="emit the P42 enumeration/outcome/authorization/edge transaction contract",
    )
    p42_cycle = commands.add_parser(
        "p42-cycle",
        help="compile one complete P42 exactly-once edge transaction macrocycle",
    )
    p42_cycle.add_argument("--signer-registry")
    p42_cycle.add_argument("--enumeration-witness")
    p42_cycle.add_argument("--events")
    p42_cycle.add_argument("--edge-authorizations")
    p42_cycle.add_argument("--execution-ledger")
    p42_cycle.add_argument("--post-edge-events")
    p42_cycle.add_argument(
        "--namespace", choices=("PRODUCTION", "TEST"), default="PRODUCTION"
    )
    p42_cycle.add_argument("--execution-time")
    p42_cycle.add_argument("--output")
    p42_verify = commands.add_parser(
        "p42-verify",
        help="verify and cold-replay one frozen P42 macrocycle",
    )
    p42_verify.add_argument("envelope")
    p42_release = commands.add_parser(
        "p42-release",
        help="materialize the honest-HOLD P42 reference release",
    )
    p42_release.add_argument(
        "--output", default="registry/p42-edge-transaction/v1"
    )
    p42_release.add_argument("--implementation-commit", required=True)
    p42_release.add_argument("--implementation-tree", required=True)
    commands.add_parser(
        "p43-contract",
        help="emit the P43 admission, exactly-once finality, and forward-watch contract",
    )
    p43_cycle = commands.add_parser(
        "p43-cycle",
        help="compile one complete P43 admission/finality macrocycle",
    )
    p43_cycle.add_argument("--signer-registry")
    p43_cycle.add_argument("--enumeration-witness")
    p43_cycle.add_argument("--events")
    p43_cycle.add_argument("--edge-authorizations")
    p43_cycle.add_argument("--execution-ledger")
    p43_cycle.add_argument("--post-edge-events")
    p43_cycle.add_argument(
        "--namespace", choices=("PRODUCTION", "TEST"), default="PRODUCTION"
    )
    p43_cycle.add_argument("--execution-time")
    p43_cycle.add_argument("--output")
    p43_verify = commands.add_parser(
        "p43-verify",
        help="verify and cold-replay one frozen P43 macrocycle",
    )
    p43_verify.add_argument("envelope")
    p43_release = commands.add_parser(
        "p43-release",
        help="materialize the honest-HOLD P43 reference release",
    )
    p43_release.add_argument(
        "--output", default="registry/p43-admission-finality/v1"
    )
    p43_release.add_argument("--implementation-commit", required=True)
    p43_release.add_argument("--implementation-tree", required=True)

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

    if args.command == "tool-dispatch-contract":
        _json(tool_dispatch_contract())
        return 0

    if args.command == "tool-dispatch-heads":
        _json(
            build_dispatch_head_registry(
                implementation_commit=args.implementation_commit,
                implementation_tree=args.implementation_tree,
                supersedes_registry_digest=args.supersedes_registry_digest,
            )
        )
        return 0

    if args.command == "tool-dispatch-plan":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        heads = json.loads(Path(args.heads).read_text(encoding="utf-8"))
        report = compile_tool_dispatch_plan(
            request,
            head_registry=heads,
            executor_workers=args.workers,
        )
        _json(report)
        return 0 if report["status"] == "READY" else 2

    if args.command == "tool-dispatch":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        heads = json.loads(Path(args.heads).read_text(encoding="utf-8"))
        report = dispatch_mycelium_tool(
            request,
            head_registry=heads,
            executor_workers=args.workers,
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
        _json(report)
        return 0 if report["status"] == "EXECUTED" else 2

    if args.command == "tool-dispatch-verify":
        result = json.loads(Path(args.result).read_text(encoding="utf-8"))
        heads = json.loads(Path(args.heads).read_text(encoding="utf-8"))
        report = verify_tool_dispatch_result(
            result,
            head_registry=heads,
            cold_replay=not args.no_cold_replay,
        )
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "tool-dispatch-runtime":
        source = json.loads(Path(args.source).read_text(encoding="utf-8"))
        bundle = json.loads(Path(args.bundle).read_text(encoding="utf-8"))
        report = compile_tool_dispatch_runtime(
            args.output,
            implementation_commit=args.implementation_commit,
            implementation_tree=args.implementation_tree,
            parallel_route_snapshot=source,
            run_receipt_bundle=bundle,
        )
        _json(report)
        return (
            0
            if report["dispatch_status"] == "EXECUTED"
            and report["verification_verdict"] == "PASS"
            else 2
        )

    if args.command == "p31-exact-status":
        _json(ExactP31Archive(args.archive).status())
        return 0

    if args.command == "p31-exact-navigate":
        report = navigate_exact_p31(
            args.query,
            archive_path=args.archive,
            policy=args.policy,
            hop_budget=args.hop_budget,
        )
        _json(report)
        return 0 if report["receipt"]["verified"] else 2

    if args.command == "p36-contract":
        _json(p36_contract())
        return 0

    if args.command == "p36-tools":
        _json(p36_tool_registry())
        return 0

    if args.command == "p36-cycle":
        events = json.loads(Path(args.events).read_text(encoding="utf-8"))
        subscriptions = json.loads(
            Path(args.subscriptions).read_text(encoding="utf-8")
        )
        parent_receipts = (
            json.loads(Path(args.parent_receipts).read_text(encoding="utf-8"))
            if args.parent_receipts
            else []
        )
        report = compile_p36_cycle(
            events=events,
            subscription_registry=subscriptions,
            base_state_digest=args.base_state_digest,
            cutoff=args.cutoff,
            parent_receipts=parent_receipts,
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
        _json(report)
        return 0 if report["delta"]["status"] != "ABORTED_HOLD" else 2

    if args.command == "p36-verify":
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        report = verify_p36_cycle(envelope)
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "p36-public-project":
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        _json(public_projection(envelope))
        return 0

    if args.command == "p36-release":
        report = compile_p36_release(
            args.output,
            implementation_commit=args.implementation_commit,
            implementation_tree=args.implementation_tree,
        )
        _json(report)
        return 0 if report["verification_verdict"] == "PASS" else 2

    if args.command == "p37-reconcile":
        _json(p37_public_reconciliation())
        return 0

    if args.command == "p35-registry-bind":
        _json(bind_exact_p35_registry(args.directory))
        return 0

    if args.command == "p38-contract":
        _json(p38_contract())
        return 0

    if args.command == "p38-coordinate-tensor":
        _json(coordinate_tensor_144())
        return 0

    if args.command == "p38-query":
        query_value = json.loads(Path(args.query).read_text(encoding="utf-8"))
        _json(compile_multi_crystal_query(query_value))
        return 0

    if args.command == "p38-source-route":
        events = json.loads(Path(args.events).read_text(encoding="utf-8"))
        report = route_source_events(events, cutoff=args.cutoff)
        _json(report)
        return 0 if not any(
            row["status"] == "REJECTED" for row in report["receipts"]
        ) else 2

    if args.command == "p38-cycle":
        query_value = json.loads(Path(args.query).read_text(encoding="utf-8"))
        binding = json.loads(
            Path(args.registry_binding).read_text(encoding="utf-8")
        )
        source_events = (
            json.loads(Path(args.source_events).read_text(encoding="utf-8"))
            if args.source_events
            else []
        )
        outcomes = (
            json.loads(Path(args.outcomes).read_text(encoding="utf-8"))
            if args.outcomes
            else []
        )
        signer_registry = (
            json.loads(
                Path(args.signer_registry).read_text(encoding="utf-8")
            )
            if args.signer_registry
            else None
        )
        ic10_returns = (
            json.loads(Path(args.ic10_returns).read_text(encoding="utf-8"))
            if args.ic10_returns
            else []
        )
        report = compile_p38_cycle(
            query=query_value,
            registry_binding=binding,
            source_events=source_events,
            outcomes=outcomes,
            signer_registry=signer_registry,
            ic10_returns=ic10_returns,
            cutoff=args.cutoff,
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
        _json(report)
        return 0 if verify_p38_cycle(report)["verdict"] == "PASS" else 2

    if args.command == "p38-verify":
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        report = verify_p38_cycle(envelope)
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "p38-release":
        source_events = (
            json.loads(Path(args.source_events).read_text(encoding="utf-8"))
            if args.source_events
            else []
        )
        report = compile_p38_release(
            args.output,
            implementation_commit=args.implementation_commit,
            implementation_tree=args.implementation_tree,
            registry_directory=args.registry_directory,
            source_events=source_events,
        )
        _json(report)
        return 0 if report["verification_verdict"] == "PASS" else 2

    if args.command == "p39-contract":
        _json(p39_contract())
        return 0

    if args.command == "p39-policy":
        _json(p39_policy())
        return 0

    if args.command == "p39-corpus":
        observations = json.loads(
            Path(args.observations).read_text(encoding="utf-8")
        )
        report = compile_live_outcome_corpus(
            observations,
            cutoff=args.cutoff,
        )
        _json(report)
        return 0 if report["status"] == "CORPUS_READY" else 2

    if args.command == "p39-calibrate":
        corpus = json.loads(Path(args.corpus).read_text(encoding="utf-8"))
        report = calibrate_weights(corpus)
        _json(report)
        return 0 if report["status"] == "CALIBRATION_READY" else 2

    if args.command == "p39-cycle":
        observations = (
            json.loads(Path(args.observations).read_text(encoding="utf-8"))
            if args.observations
            else []
        )
        signer_registry = (
            json.loads(
                Path(args.signer_registry).read_text(encoding="utf-8")
            )
            if args.signer_registry
            else None
        )
        ic10_returns = (
            json.loads(Path(args.ic10_returns).read_text(encoding="utf-8"))
            if args.ic10_returns
            else []
        )
        report = compile_p39_cycle(
            observations=observations,
            signer_registry=signer_registry,
            ic10_returns=ic10_returns,
            cutoff=args.cutoff,
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
        _json(report)
        return 0 if verify_p39_cycle(report)["verdict"] == "PASS" else 2

    if args.command == "p39-verify":
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        report = verify_p39_cycle(envelope)
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "p39-release":
        report = compile_p39_release(
            args.output,
            implementation_commit=args.implementation_commit,
            implementation_tree=args.implementation_tree,
        )
        _json(report)
        return 0 if report["verification_verdict"] == "PASS" else 2

    if args.command == "p40-contract":
        _json(p40_contract())
        return 0

    if args.command == "p40-sibling":
        _json(p40_sibling_capsule())
        return 0

    if args.command == "p40-state":
        weights = (
            json.loads(Path(args.weights).read_text(encoding="utf-8"))
            if args.weights
            else []
        )
        _json(
            build_canonical_weight_state(
                weights,
                generation=args.generation,
                parent_state_root=args.parent_state_root,
            )
        )
        return 0

    if args.command == "p40-cycle":
        parent = (
            json.loads(Path(args.p39_cycle).read_text(encoding="utf-8"))
            if args.p39_cycle
            else None
        )
        canonical_state = (
            json.loads(
                Path(args.canonical_state).read_text(encoding="utf-8")
            )
            if args.canonical_state
            else None
        )
        sibling = (
            json.loads(
                Path(args.sibling_capsule).read_text(encoding="utf-8")
            )
            if args.sibling_capsule
            else None
        )
        report = compile_p40_cycle(
            p39_cycle=parent,
            canonical_state=canonical_state,
            expected_base_state_root=args.expected_base_state_root,
            sibling_capsule=sibling,
            namespace=args.namespace,
            cutoff=args.cutoff,
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
        _json(report)
        return 0 if verify_p40_cycle(report)["verdict"] == "PASS" else 2

    if args.command == "p40-verify":
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        report = verify_p40_cycle(envelope)
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "p40-release":
        report = compile_p40_release(
            args.output,
            implementation_commit=args.implementation_commit,
            implementation_tree=args.implementation_tree,
        )
        _json(report)
        return 0 if report["verification_verdict"] == "PASS" else 2

    if args.command == "p41-contract":
        _json(p41_contract())
        return 0

    if args.command == "p41-source":
        _json(p41_source_manifest())
        return 0

    if args.command == "p41-trees":
        _json(p41_repository_forest())
        return 0

    if args.command == "p41-cohort":
        events = (
            json.loads(Path(args.events).read_text(encoding="utf-8"))
            if args.events
            else []
        )
        _json(freeze_heldout_cohort(events))
        return 0

    if args.command == "p41-cycle":
        events = (
            json.loads(Path(args.events).read_text(encoding="utf-8"))
            if args.events
            else []
        )
        registry = (
            json.loads(
                Path(args.ic10_registry).read_text(encoding="utf-8")
            )
            if args.ic10_registry
            else None
        )
        returns = (
            json.loads(
                Path(args.ic10_returns).read_text(encoding="utf-8")
            )
            if args.ic10_returns
            else []
        )
        report = compile_p41_cycle(
            heldout_events=events,
            ic10_registry=registry,
            ic10_returns=returns,
            namespace=args.namespace,
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
        _json(report)
        return 0 if verify_p41_cycle(report)["verdict"] == "PASS" else 2

    if args.command == "p41-verify":
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        report = verify_p41_cycle(envelope)
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "p41-release":
        report = compile_p41_release(
            args.output,
            implementation_commit=args.implementation_commit,
            implementation_tree=args.implementation_tree,
        )
        _json(report)
        return 0 if report["verification_verdict"] == "PASS" else 2

    if args.command == "p42-contract":
        _json(p42_contract())
        return 0

    if args.command == "p42-cycle":
        def read_optional(path: str | None, default: object) -> object:
            return (
                json.loads(Path(path).read_text(encoding="utf-8"))
                if path
                else default
            )

        kwargs = {
            "signer_registry": read_optional(args.signer_registry, None),
            "enumeration_witness": read_optional(
                args.enumeration_witness, None
            ),
            "heldout_events": read_optional(args.events, []),
            "edge_authorizations": read_optional(
                args.edge_authorizations, []
            ),
            "execution_ledger": read_optional(args.execution_ledger, []),
            "post_edge_events": read_optional(args.post_edge_events, []),
            "namespace": args.namespace,
        }
        if args.execution_time:
            kwargs["execution_time"] = args.execution_time
        report = compile_p42_cycle(**kwargs)
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
        _json(report)
        return 0 if verify_p42_cycle(report)["verdict"] == "PASS" else 2

    if args.command == "p42-verify":
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        report = verify_p42_cycle(envelope)
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "p42-release":
        report = compile_p42_release(
            args.output,
            implementation_commit=args.implementation_commit,
            implementation_tree=args.implementation_tree,
        )
        _json(report)
        return 0 if report["verification_verdict"] == "PASS" else 2

    if args.command == "p43-contract":
        _json(p43_contract())
        return 0

    if args.command == "p43-cycle":
        def read_p43_optional(path: str | None, default: object) -> object:
            return (
                json.loads(Path(path).read_text(encoding="utf-8"))
                if path
                else default
            )

        kwargs = {
            "signer_registry": read_p43_optional(args.signer_registry, None),
            "enumeration_witness": read_p43_optional(
                args.enumeration_witness, None
            ),
            "heldout_events": read_p43_optional(args.events, []),
            "edge_authorizations": read_p43_optional(
                args.edge_authorizations, []
            ),
            "execution_ledger": read_p43_optional(args.execution_ledger, []),
            "post_edge_events": read_p43_optional(args.post_edge_events, []),
            "namespace": args.namespace,
        }
        if args.execution_time:
            kwargs["execution_time"] = args.execution_time
        report = compile_p43_cycle(**kwargs)
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
        _json(report)
        return 0 if verify_p43_cycle(report)["verdict"] == "PASS" else 2

    if args.command == "p43-verify":
        envelope = json.loads(Path(args.envelope).read_text(encoding="utf-8"))
        report = verify_p43_cycle(envelope)
        _json(report)
        return 0 if report["verdict"] == "PASS" else 2

    if args.command == "p43-release":
        report = compile_p43_release(
            args.output,
            implementation_commit=args.implementation_commit,
            implementation_tree=args.implementation_tree,
        )
        _json(report)
        return 0 if report["verification_verdict"] == "PASS" else 2

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
