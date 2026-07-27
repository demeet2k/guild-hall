from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import GateResult, GateVerdict


@dataclass(slots=True)
class IC10Context:
    address_ok: bool
    schema_hash_ok: bool
    witness_refs: list[str]
    warrant_typed: bool
    contradiction_classified: bool
    authority_ok: bool
    consent_ok: bool
    repair_layer_match: bool
    replay_class: str
    trust_delta_justified: bool
    residual_scope_declared: bool
    blocking_residuals: list[str] = field(default_factory=list)
    nonblocking_residuals: list[str] = field(default_factory=list)
    successor_seed_ref: str | None = None
    reentry_target_declared: bool = True


class IC10Evaluator:
    """Reason-bearing ten-gate immune evaluation."""

    def evaluate(self, context: IC10Context) -> list[GateResult]:
        results = [
            self._boolean_gate(
                "I01_ADDRESS_INTEGRITY",
                context.address_ok,
                "ADDRESS_VALID",
                "ADDRESS_INVALID",
            ),
            self._boolean_gate(
                "I02_SCHEMA_AND_HASH_INTEGRITY",
                context.schema_hash_ok,
                "SCHEMA_HASH_VALID",
                "SCHEMA_OR_HASH_INVALID",
            ),
            self._witness_gate(context),
            self._boolean_gate(
                "I04_CONTRADICTION_CLASSIFICATION",
                context.contradiction_classified,
                "CONTRADICTION_TYPED",
                "CONTRADICTION_UNTYPED",
            ),
            self._authority_gate(context),
            self._boolean_gate(
                "I06_REPAIR_LAYER_MATCH",
                context.repair_layer_match,
                "REPAIR_MATCHES_DAMAGED_LAYER",
                "REPAIR_LAYER_MISMATCH",
            ),
            self._replay_gate(context.replay_class),
            self._boolean_gate(
                "I08_TRUST_DELTA_JUSTIFICATION",
                context.trust_delta_justified,
                "TRUST_DELTA_WITNESSED",
                "TRUST_DELTA_UNWITNESSED",
            ),
            self._residual_gate(context),
            self._closure_gate(context),
        ]
        return results

    @staticmethod
    def overall(results: list[GateResult]) -> GateVerdict:
        verdicts = {result.verdict for result in results}
        if GateVerdict.FAIL in verdicts:
            return GateVerdict.FAIL
        if GateVerdict.HOLD in verdicts:
            return GateVerdict.HOLD
        if GateVerdict.NEAR in verdicts:
            return GateVerdict.NEAR
        return GateVerdict.PASS

    @staticmethod
    def vector(results: list[GateResult]) -> dict[str, str]:
        return {result.gate_id: result.verdict.value for result in results}

    @staticmethod
    def _boolean_gate(
        gate_id: str,
        passed: bool,
        pass_reason: str,
        fail_reason: str,
    ) -> GateResult:
        return GateResult(
            gate_id=gate_id,
            verdict=GateVerdict.PASS if passed else GateVerdict.FAIL,
            reason_codes=[pass_reason if passed else fail_reason],
            required_repairs=[] if passed else [f"REPAIR::{fail_reason}"],
        )

    @staticmethod
    def _witness_gate(context: IC10Context) -> GateResult:
        if not context.witness_refs:
            return GateResult(
                gate_id="I03_WITNESS_AND_WARRANT",
                verdict=GateVerdict.FAIL,
                reason_codes=["NO_WITNESS"],
                required_repairs=["BIND_WITNESS"],
            )
        if not context.warrant_typed:
            return GateResult(
                gate_id="I03_WITNESS_AND_WARRANT",
                verdict=GateVerdict.HOLD,
                reason_codes=["WARRANT_UNTYPED"],
                witness_refs=context.witness_refs,
                required_repairs=["TYPE_WARRANT"],
            )
        return GateResult(
            gate_id="I03_WITNESS_AND_WARRANT",
            verdict=GateVerdict.PASS,
            reason_codes=["WITNESS_BOUND", "WARRANT_TYPED"],
            witness_refs=context.witness_refs,
        )

    @staticmethod
    def _authority_gate(context: IC10Context) -> GateResult:
        reasons: list[str] = []
        if not context.authority_ok:
            reasons.append("AUTHORITY_VIOLATION")
        if not context.consent_ok:
            reasons.append("CONSENT_VIOLATION")
        return GateResult(
            gate_id="I05_AUTHORITY_CONSENT_BOUNDARY",
            verdict=GateVerdict.PASS if not reasons else GateVerdict.FAIL,
            reason_codes=reasons or ["AUTHORITY_VALID", "CONSENT_VALID"],
            required_repairs=[f"REPAIR::{reason}" for reason in reasons],
        )

    @staticmethod
    def _replay_gate(replay_class: str) -> GateResult:
        if replay_class == "EXACT":
            return GateResult(
                gate_id="I07_REPLAY_EQUIVALENCE",
                verdict=GateVerdict.PASS,
                reason_codes=["REPLAY_EXACT"],
            )
        if replay_class == "LAW_EQUIV":
            return GateResult(
                gate_id="I07_REPLAY_EQUIVALENCE",
                verdict=GateVerdict.NEAR,
                reason_codes=["REPLAY_LAW_EQUIVALENT"],
            )
        if replay_class == "RESIDUALIZED":
            return GateResult(
                gate_id="I07_REPLAY_EQUIVALENCE",
                verdict=GateVerdict.HOLD,
                reason_codes=["REPLAY_RESIDUALIZED"],
                required_repairs=["CLOSE_REPLAY_RESIDUAL"],
            )
        return GateResult(
            gate_id="I07_REPLAY_EQUIVALENCE",
            verdict=GateVerdict.FAIL,
            reason_codes=["REPLAY_ILLEGAL"],
            required_repairs=["REPAIR_REPLAY_ROUTE"],
        )

    @staticmethod
    def _residual_gate(context: IC10Context) -> GateResult:
        if context.blocking_residuals:
            return GateResult(
                gate_id="I09_RESIDUAL_SCOPE_HONESTY",
                verdict=GateVerdict.FAIL,
                reason_codes=["BLOCKING_RESIDUAL_PRESENT"],
                residual_refs=context.blocking_residuals,
                required_repairs=["CLOSE_BLOCKING_RESIDUAL"],
            )
        if not context.residual_scope_declared:
            return GateResult(
                gate_id="I09_RESIDUAL_SCOPE_HONESTY",
                verdict=GateVerdict.HOLD,
                reason_codes=["RESIDUAL_SCOPE_UNDECLARED"],
                required_repairs=["DECLARE_RESIDUAL_SCOPE"],
            )
        if context.nonblocking_residuals:
            return GateResult(
                gate_id="I09_RESIDUAL_SCOPE_HONESTY",
                verdict=GateVerdict.NEAR,
                reason_codes=["NONBLOCKING_RESIDUAL_PRESERVED"],
                residual_refs=context.nonblocking_residuals,
            )
        return GateResult(
            gate_id="I09_RESIDUAL_SCOPE_HONESTY",
            verdict=GateVerdict.PASS,
            reason_codes=["NO_BLOCKING_RESIDUAL", "RESIDUAL_SCOPE_DECLARED"],
        )

    @staticmethod
    def _closure_gate(context: IC10Context) -> GateResult:
        if not context.reentry_target_declared:
            return GateResult(
                gate_id="I10_REENTRY_SUCCESSOR_CLOSURE",
                verdict=GateVerdict.FAIL,
                reason_codes=["REENTRY_TARGET_MISSING"],
                required_repairs=["DECLARE_REENTRY_TARGET"],
            )
        if context.successor_seed_ref is None:
            return GateResult(
                gate_id="I10_REENTRY_SUCCESSOR_CLOSURE",
                verdict=GateVerdict.HOLD,
                reason_codes=["SUCCESSOR_SEED_PENDING_PERMIT"],
            )
        return GateResult(
            gate_id="I10_REENTRY_SUCCESSOR_CLOSURE",
            verdict=GateVerdict.PASS,
            reason_codes=["REENTRY_TARGET_DECLARED", "SUCCESSOR_SEED_RESERVED"],
        )

    @classmethod
    def report(cls, results: list[GateResult]) -> dict[str, Any]:
        return {
            "schema_version": "IC10_GATE_REPORT/1",
            "overall": cls.overall(results).value,
            "gate_vector": cls.vector(results),
            "gates": [result.to_dict() for result in results],
        }

