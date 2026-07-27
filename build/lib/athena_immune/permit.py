from __future__ import annotations

from typing import Any

from .canonical import content_hash, utc_now
from .ic10 import IC10Evaluator
from .models import AdmissionClass, GateResult, GateVerdict, RoleAssignments


class ReentryPermitCompiler:
    """Compile a bounded reentry decision from IC10 and separation-of-powers state."""

    CRITICAL_GATES = {
        "I02_SCHEMA_AND_HASH_INTEGRITY",
        "I05_AUTHORITY_CONSENT_BOUNDARY",
    }

    def compile(
        self,
        *,
        permit_id: str,
        cycle_id: str,
        repaired_act_id: str,
        contradiction_packet_refs: list[str],
        repair_receipt_refs: list[str],
        trust_revision_refs: list[str],
        replay_receipt_ref: str,
        witness_root: str,
        gate_results: list[GateResult],
        omega_gate: bool,
        sigma_gate: bool,
        unresolved_residuals: list[str],
        blocking_residuals: list[str],
        admitted_scope: list[str],
        excluded_scope: list[str],
        allowed_operations: list[str],
        forbidden_operations: list[str],
        assignments: RoleAssignments,
        successor_seed_ref: str | None,
        expiry_condition: str = "SUPERSEDED_OR_REVOKED",
        revocation_conditions: list[str] | None = None,
        prior_permit_hash: str | None = None,
    ) -> dict[str, Any]:
        separation_errors = assignments.separation_errors()
        overall = IC10Evaluator.overall(gate_results)
        critical_failure = any(
            gate.gate_id in self.CRITICAL_GATES and gate.verdict is GateVerdict.FAIL
            for gate in gate_results
        )

        reasons: list[str] = []
        if not omega_gate:
            reasons.append("OMEGA_GATE_FAILED")
        if not sigma_gate:
            reasons.append("SIGMA_GATE_FAILED")
        reasons.extend(separation_errors)
        if blocking_residuals:
            reasons.append("BLOCKING_RESIDUAL_PRESENT")

        if critical_failure or not omega_gate or not sigma_gate or separation_errors:
            admission = AdmissionClass.REFUSED
        elif blocking_residuals or overall is GateVerdict.FAIL:
            admission = AdmissionClass.QUARANTINED
        elif overall is GateVerdict.HOLD:
            admission = AdmissionClass.DEFERRED
        elif overall is GateVerdict.NEAR or unresolved_residuals:
            admission = AdmissionClass.LIMITED
        else:
            admission = AdmissionClass.FULL

        reentry_allowed = admission in {AdmissionClass.FULL, AdmissionClass.LIMITED}
        if not reentry_allowed:
            successor_seed_ref = None
            allowed_operations = []

        permit = {
            "schema_version": "REENTRY_PERMIT/1",
            "permit_id": permit_id,
            "cycle_id": cycle_id,
            "repaired_act_id": repaired_act_id,
            "contradiction_packet_refs": sorted(set(contradiction_packet_refs)),
            "repair_receipt_refs": sorted(set(repair_receipt_refs)),
            "trust_revision_refs": sorted(set(trust_revision_refs)),
            "replay_receipt_ref": replay_receipt_ref,
            "witness_root": witness_root,
            "ic10_gate_vector": IC10Evaluator.vector(gate_results),
            "ic10_overall": overall.value,
            "omega_gate": "PASS" if omega_gate else "FAIL",
            "sigma_gate": "PASS" if sigma_gate else "FAIL",
            "unresolved_residuals": sorted(set(unresolved_residuals)),
            "blocking_residuals": sorted(set(blocking_residuals)),
            "admitted_scope": admitted_scope if reentry_allowed else [],
            "excluded_scope": sorted(set(excluded_scope)),
            "allowed_operations": allowed_operations,
            "forbidden_operations": sorted(set(forbidden_operations)),
            "admission_class": admission.value,
            "reentry_allowed": reentry_allowed,
            "decision_reasons": reasons or [f"IC10_{overall.value}"],
            "expiry_condition": expiry_condition,
            "revocation_conditions": revocation_conditions
            or [
                "SOURCE_DIGEST_CHANGED",
                "REPLAY_DIVERGED",
                "NEW_BLOCKING_RESIDUAL",
                "AUTHORITY_REVOKED",
            ],
            "immune_steward": assignments.immune_steward,
            "replay_auditor": assignments.replay_auditor,
            "meta_observer": assignments.meta_observer,
            "separation_of_roles_pass": not separation_errors,
            "successor_seed_ref": successor_seed_ref,
            "prior_permit_hash": prior_permit_hash,
            "created_at": utc_now(),
        }
        permit["packet_hash"] = content_hash(permit)
        return permit

