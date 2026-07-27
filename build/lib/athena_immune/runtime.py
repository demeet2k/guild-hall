from __future__ import annotations

from pathlib import Path
from typing import Any

from .canonical import content_hash, merkle_root, utc_now
from .ic10 import IC10Context, IC10Evaluator
from .kc54 import KC54Auditor
from .ledger import AppendOnlyLedger
from .models import CycleResult, RoleAssignments, TrustEvidence, TrustVector
from .permit import ReentryPermitCompiler
from .qshrink import QShrinkCodec
from .scheduler import RepairScheduler
from .trust import TrustRevisionEngine


class ImmuneRuntime:
    """End-to-end executable Athena immune cycle."""

    def __init__(self, ledger: AppendOnlyLedger | str | Path = ":memory:") -> None:
        self.ledger = ledger if isinstance(ledger, AppendOnlyLedger) else AppendOnlyLedger(ledger)
        self.scheduler = RepairScheduler()
        self.ic10 = IC10Evaluator()
        self.trust = TrustRevisionEngine()
        self.permits = ReentryPermitCompiler()
        self.kc54 = KC54Auditor()
        self.qshrink = QShrinkCodec()

    def run_cycle(
        self,
        *,
        cycle_id: str,
        act: dict[str, Any],
        contradiction: dict[str, Any],
        repair_receipts: list[dict[str, Any]],
        prior_trust: TrustVector,
        trust_evidence: TrustEvidence,
        assignments: RoleAssignments,
        omega_gate: bool,
        sigma_gate: bool,
        source_addresses: list[str],
        next_route: str,
        admitted_scope: list[str],
        excluded_scope: list[str] | None = None,
        allowed_operations: list[str] | None = None,
        forbidden_operations: list[str] | None = None,
        blocking_residuals: list[str] | None = None,
        nonblocking_residuals: list[str] | None = None,
        replay_class: str = "EXACT",
    ) -> CycleResult:
        blocking_residuals = blocking_residuals or []
        nonblocking_residuals = nonblocking_residuals or []
        act_id = str(act.get("act_id") or f"{cycle_id}.ACT")
        contradiction_id = str(
            contradiction.get("contradiction_id") or f"{cycle_id}.CONTRADICTION"
        )

        act_packet = {
            "schema_version": "ACT_RECORD/1",
            "act_id": act_id,
            "cycle_id": cycle_id,
            **act,
            "created_at": str(act.get("created_at") or utc_now()),
        }
        act_packet["packet_hash"] = content_hash(act_packet)
        self.ledger.append("ACT_RECORD", act_id, cycle_id, act_packet)

        contradiction_packet = {
            "schema_version": "CONTRADICTION_PACKET/1",
            "contradiction_id": contradiction_id,
            "cycle_id": cycle_id,
            "parent_act_id": act_id,
            "route_address": next_route,
            **contradiction,
            "created_at": str(contradiction.get("created_at") or utc_now()),
        }
        contradiction_packet["packet_hash"] = content_hash(contradiction_packet)
        self.ledger.append(
            "CONTRADICTION_PACKET",
            contradiction_id,
            cycle_id,
            contradiction_packet,
        )

        repair_plan = self.scheduler.schedule(contradiction_packet)
        self.ledger.append(
            "REPAIR_PLAN",
            str(repair_plan["plan_id"]),
            cycle_id,
            repair_plan,
        )

        repair_refs: list[str] = []
        layer_matches: list[bool] = []
        normalized_receipts: list[dict[str, Any]] = []
        expected_layers = {
            str(item["residual_code"]): str(item["damaged_layer"])
            for item in repair_plan["items"]
        }
        for index, receipt in enumerate(repair_receipts, start=1):
            repair_id = str(receipt.get("repair_id") or f"{cycle_id}.RECEIPT.{index:03d}")
            normalized = {
                "schema_version": "REPAIR_RECEIPT/1",
                "repair_id": repair_id,
                "cycle_id": cycle_id,
                **receipt,
                "created_at": str(receipt.get("created_at") or utc_now()),
            }
            normalized["packet_hash"] = content_hash(normalized)
            self.ledger.append("REPAIR_RECEIPT", repair_id, cycle_id, normalized)
            repair_refs.append(repair_id)
            normalized_receipts.append(normalized)
            expected = expected_layers.get(str(receipt.get("residual_code")))
            layer_matches.append(
                expected is not None
                and expected == str(receipt.get("repair_layer"))
                and str(receipt.get("status")) == "VERIFIED"
            )

        replay_receipt_id = f"{cycle_id}.REPLAY"
        replay_receipt = {
            "schema_version": "REPLAY_RECEIPT/1",
            "replay_receipt_id": replay_receipt_id,
            "cycle_id": cycle_id,
            "classification": replay_class,
            "repair_receipt_refs": repair_refs,
            "created_at": utc_now(),
        }
        replay_receipt["packet_hash"] = content_hash(replay_receipt)
        self.ledger.append(
            "REPLAY_RECEIPT",
            replay_receipt_id,
            cycle_id,
            replay_receipt,
        )

        witness_refs = sorted(
            set(contradiction_packet.get("witness_refs", []))
            | set(contradiction_packet.get("counterwitness_refs", []))
        )
        trust_revision_id = f"{cycle_id}.TRUST"
        trust_revision = self.trust.revise(
            revision_id=trust_revision_id,
            cycle_id=cycle_id,
            contradiction_id=contradiction_id,
            subject_edge=str(contradiction_packet.get("subject_edge", "ATHENA→CLAIM")),
            prior=prior_trust,
            evidence=trust_evidence,
            evidence_refs=witness_refs,
            repair_receipt_refs=repair_refs,
            replay_receipt_ref=replay_receipt_id,
            residual_refs=blocking_residuals + nonblocking_residuals,
            proposer=assignments.proposer,
            reviewer=assignments.integrator,
            replay_auditor=assignments.replay_auditor,
        )
        self.ledger.append(
            "TRUST_REVISION_ENTRY",
            trust_revision_id,
            cycle_id,
            trust_revision,
        )

        reserved_seed_id = f"{cycle_id}.SUCCESSOR"
        gate_context = IC10Context(
            address_ok=bool(contradiction_packet.get("route_address")),
            schema_hash_ok=True,
            witness_refs=witness_refs,
            warrant_typed=bool(contradiction_packet.get("proposition_a_warrant"))
            and bool(contradiction_packet.get("proposition_b_warrant")),
            contradiction_classified=bool(contradiction_packet.get("contradiction_classes")),
            authority_ok=bool(contradiction_packet.get("authority_ok", True)),
            consent_ok=bool(contradiction_packet.get("consent_ok", True)),
            repair_layer_match=bool(layer_matches) and all(layer_matches),
            replay_class=replay_class,
            trust_delta_justified=self.trust.justified(trust_revision),
            residual_scope_declared=True,
            blocking_residuals=blocking_residuals,
            nonblocking_residuals=nonblocking_residuals,
            successor_seed_ref=reserved_seed_id,
            reentry_target_declared=bool(next_route),
        )
        gates = self.ic10.evaluate(gate_context)

        permit_id = f"{cycle_id}.PERMIT"
        permit = self.permits.compile(
            permit_id=permit_id,
            cycle_id=cycle_id,
            repaired_act_id=act_id,
            contradiction_packet_refs=[contradiction_id],
            repair_receipt_refs=repair_refs,
            trust_revision_refs=[trust_revision_id],
            replay_receipt_ref=replay_receipt_id,
            witness_root=merkle_root(witness_refs),
            gate_results=gates,
            omega_gate=omega_gate,
            sigma_gate=sigma_gate,
            unresolved_residuals=nonblocking_residuals,
            blocking_residuals=blocking_residuals,
            admitted_scope=admitted_scope,
            excluded_scope=excluded_scope or [],
            allowed_operations=allowed_operations or ["REENTER", "RESEED"],
            forbidden_operations=forbidden_operations or ["OVERWRITE_HISTORY"],
            assignments=assignments,
            successor_seed_ref=reserved_seed_id,
        )
        self.ledger.append("REENTRY_PERMIT", permit_id, cycle_id, permit)

        full_cycle = {
            "act": act_packet,
            "contradiction": contradiction_packet,
            "repair_plan": repair_plan,
            "repair_receipts": normalized_receipts,
            "replay_receipt": replay_receipt,
            "trust_revision": trust_revision,
            "reentry_permit": permit,
        }

        successor_seed: dict[str, Any] | None = None
        replay_certificate: dict[str, Any] | None = None
        if permit["reentry_allowed"]:
            successor_seed = self.qshrink.build_seed(
                seed_id=reserved_seed_id,
                cycle_id=cycle_id,
                full_cycle=full_cycle,
                gate_vector=permit["ic10_gate_vector"],
                residual_vector={
                    "blocking": blocking_residuals,
                    "nonblocking": nonblocking_residuals,
                },
                source_addresses=source_addresses,
                next_route=next_route,
            )
            self.ledger.append(
                "SUCCESSOR_SEED",
                reserved_seed_id,
                cycle_id,
                successor_seed,
            )
            replay_certificate = self.qshrink.replay(
                certificate_id=f"{cycle_id}.QSHRINK.REPLAY",
                seed=successor_seed,
                full_cycle=full_cycle,
            )
            self.ledger.append(
                "REPLAY_CERTIFICATE",
                str(replay_certificate["certificate_id"]),
                cycle_id,
                replay_certificate,
            )

        forward_route = [
            {
                "packet_type": entry["packet_type"],
                "packet_id": entry["packet_id"],
                "payload_hash": entry["payload_hash"],
            }
            for entry in self.ledger.entries(cycle_id=cycle_id)
        ]
        reconstructed = [dict(event) for event in forward_route]
        kc54_receipt = self.kc54.audit(
            receipt_id=f"{cycle_id}.KC54",
            cycle_id=cycle_id,
            forward_route=forward_route,
            reconstructed_inverse_route=reconstructed,
            preserved_invariants=[
                "APPEND_ONLY_HISTORY",
                "WITNESS_BEFORE_TRUST_DELTA",
                "REPAIR_REPLAY_TRUST_PERMIT_ORDER",
                "NO_SEED_WITHOUT_PERMIT",
            ],
            alternate_branches=list(contradiction_packet.get("alternate_branches", [])),
            unresolved_frontier=blocking_residuals + nonblocking_residuals,
        )
        self.ledger.append(
            "KC54_CONJUGATE_RECEIPT",
            str(kc54_receipt["receipt_id"]),
            cycle_id,
            kc54_receipt,
        )

        return CycleResult(
            cycle_id=cycle_id,
            contradiction_packet=contradiction_packet,
            repair_plan=repair_plan,
            trust_revision=trust_revision,
            gate_results=gates,
            reentry_permit=permit,
            successor_seed=successor_seed,
            replay_certificate=replay_certificate,
            kc54_receipt=kc54_receipt,
        )

