from __future__ import annotations

import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from kc144_crystal.agent_receipts import canonical_bytes
from kc144_crystal.p41_runtime import build_heldout_event, p41_source_manifest
from kc144_crystal.p42_runtime import (
    P42_LANES,
    P42_LOOKUP_KEY,
    P42_NEXT_SEED,
    PUBLIC_P41_RESULT_ID,
    ROLE_ENUMERATOR,
    ROLE_IC10,
    _ENROLLMENT_DOMAIN,
    build_p42_edge_authorization,
    build_p42_enumeration_witness,
    build_p42_signer_enrollment,
    compile_p42_cycle,
    compile_p42_release,
    empty_p42_signer_registry,
    enroll_p42_signer,
    p42_contract,
    p42_parallel_lineage,
    verify_p42_cycle,
)


def _key(index: int) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes([41 + index]) * 32)


def _proof(key: Ed25519PrivateKey, enrollment: dict) -> str:
    body = {
        name: value
        for name, value in enrollment.items()
        if name != "enrollment_digest"
    }
    return base64.urlsafe_b64encode(
        key.sign(_ENROLLMENT_DOMAIN + canonical_bytes(body))
    ).decode().rstrip("=")


def ready_registry() -> tuple[dict, Ed25519PrivateKey, Ed25519PrivateKey]:
    enum_key = _key(0)
    ic10_key = _key(1)
    registry = empty_p42_signer_registry()
    enum_enrollment = build_p42_signer_enrollment(
        signer_id="enumerator-1",
        organization_id="source-custodian-org",
        control_root="sha256:" + "a" * 64,
        role=ROLE_ENUMERATOR,
        public_key=enum_key.public_key(),
        valid_from="2026-07-28T08:00:00.000000Z",
        valid_until="2026-07-29T12:00:00.000000Z",
    )
    registry = enroll_p42_signer(
        registry,
        enum_enrollment,
        _proof(enum_key, enum_enrollment),
    )
    ic10_enrollment = build_p42_signer_enrollment(
        signer_id="ic10-authorizer-1",
        organization_id="independent-ic10-org",
        control_root="sha256:" + "b" * 64,
        role=ROLE_IC10,
        public_key=ic10_key.public_key(),
        valid_from="2026-07-28T08:00:00.000000Z",
        valid_until="2026-07-29T12:00:00.000000Z",
    )
    registry = enroll_p42_signer(
        registry,
        ic10_enrollment,
        _proof(ic10_key, ic10_enrollment),
    )
    return registry, enum_key, ic10_key


def ready_events() -> list[dict]:
    return [
        build_heldout_event(
            event_id=f"p42-outcome-{index}",
            outcome_class=(
                "TASK_OUTCOME" if index % 2 == 0 else "EMPIRICAL_RESULT"
            ),
            observed_at=f"2026-07-28T09:{index:02d}:00.000000Z",
            source_surface=f"SURFACE_{index % 3}",
            route_id=f"ROUTE_{index % 3}",
            detail=f"sealed outcome {index}",
        )
        for index in range(5)
    ]


def ready_inputs() -> tuple[dict, dict, list[dict], dict]:
    registry, enum_key, ic10_key = ready_registry()
    witness = build_p42_enumeration_witness(
        signer_id="enumerator-1",
        organization_id="source-custodian-org",
        control_root="sha256:" + "a" * 64,
        private_key=enum_key,
        issued_at="2026-07-28T08:30:00.000000Z",
    )
    events = ready_events()
    prepared = compile_p42_cycle(
        signer_registry=registry,
        enumeration_witness=witness,
        heldout_events=events,
        namespace="TEST",
    )
    candidate = prepared["edge_candidate"]
    enumeration = prepared["enumeration_evaluation"]
    cohort = prepared["heldout_cohort"]
    source = p41_source_manifest()
    authorization = build_p42_edge_authorization(
        transaction_root=candidate["transaction_root"],
        source_manifest_root=source["manifest_root"],
        repository_forest_root=candidate["repository_forest_root"],
        enumeration_evaluation_digest=enumeration["evaluation_digest"],
        heldout_cohort_root=cohort["cohort_root"],
        signer_id="ic10-authorizer-1",
        organization_id="independent-ic10-org",
        control_root="sha256:" + "b" * 64,
        private_key=ic10_key,
        issued_at="2026-07-28T09:30:00.000000Z",
        expires_at="2026-07-28T10:30:00.000000Z",
        nonce="p42-edge-auth-1",
    )
    return registry, witness, events, authorization


class P42ExactEdgeTransactionTests(unittest.TestCase):
    def test_all_p42_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1] / "schemas" / "kc144"
        schemas = sorted(root.glob("p42-*.schema.json"))
        self.assertEqual(len(schemas), 6)
        for path in schemas:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                value["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )

    def test_contract_is_whole_wave_and_returns_to_m12(self) -> None:
        contract = p42_contract()
        self.assertEqual(contract["lookup_key"], P42_LOOKUP_KEY)
        self.assertEqual(contract["next_seed"], P42_NEXT_SEED)
        self.assertEqual(len(contract["lanes"]), 10)
        self.assertEqual(
            [row["lane"] for row in contract["lanes"]],
            list(P42_LANES),
        )
        self.assertEqual(contract["route"][-1], "KC144.V1::GID144::M12")
        self.assertEqual(
            contract["public_parent"]["result_id"],
            PUBLIC_P41_RESULT_ID,
        )

    def test_default_cycle_is_honest_hold(self) -> None:
        cycle = compile_p42_cycle()
        self.assertEqual(cycle["enumeration_evaluation"]["status"], "HOLD")
        self.assertEqual(cycle["heldout_cohort"]["event_count"], 0)
        self.assertEqual(
            cycle["authorization_evaluation"]["status"],
            "HOLD",
        )
        self.assertEqual(
            cycle["edge_transaction"]["execution_status"],
            "HELD_NOT_EXECUTED",
        )
        self.assertEqual(
            cycle["post_edge_watch"]["status"],
            "HELD_NOT_ARMED",
        )
        self.assertFalse(cycle["state"]["production_mutated"])
        self.assertEqual(cycle["state"]["truth_effect"], "NONE")
        self.assertEqual(verify_p42_cycle(cycle)["verdict"], "PASS")

    def test_exact_enumeration_rejects_reordering(self) -> None:
        registry, enum_key, _ = ready_registry()
        rows = list(p41_source_manifest()["rows"])
        rows[0], rows[1] = rows[1], rows[0]
        witness = build_p42_enumeration_witness(
            signer_id="enumerator-1",
            organization_id="source-custodian-org",
            control_root="sha256:" + "a" * 64,
            private_key=enum_key,
            issued_at="2026-07-28T08:30:00.000000Z",
            ordered_rows=rows,
        )
        cycle = compile_p42_cycle(
            signer_registry=registry,
            enumeration_witness=witness,
        )
        self.assertEqual(cycle["enumeration_evaluation"]["status"], "HOLD")
        self.assertIn(
            "EXACT_ORDERED_ENUMERATION_MISMATCH",
            cycle["enumeration_evaluation"]["errors"],
        )

    def test_roles_must_be_independent(self) -> None:
        registry, enum_key, _ = ready_registry()
        enrollment = build_p42_signer_enrollment(
            signer_id="duplicate-control",
            organization_id="another-org",
            control_root="sha256:" + "a" * 64,
            role=ROLE_IC10,
            public_key=enum_key.public_key(),
            valid_from="2026-07-28T08:00:00.000000Z",
            valid_until="2026-07-29T12:00:00.000000Z",
        )
        with self.assertRaisesRegex(ValueError, "globally unique"):
            enroll_p42_signer(registry, enrollment, _proof(enum_key, enrollment))

    def test_test_namespace_simulates_without_mutation(self) -> None:
        registry, witness, events, authorization = ready_inputs()
        cycle = compile_p42_cycle(
            signer_registry=registry,
            enumeration_witness=witness,
            heldout_events=events,
            edge_authorizations=[authorization],
            namespace="TEST",
        )
        transaction = cycle["edge_transaction"]
        self.assertEqual(transaction["execution_status"], "SIMULATED_EXECUTION")
        self.assertFalse(transaction["ledger_mutated"])
        self.assertEqual(transaction["canonical_graph_mutations"], 0)
        self.assertFalse(transaction["production_mutated"])
        self.assertEqual(cycle["post_edge_watch"]["status"], "HELD_NOT_ARMED")
        self.assertEqual(verify_p42_cycle(cycle)["verdict"], "PASS")

    def test_production_executes_exactly_once_and_arms_watch(self) -> None:
        registry, witness, events, authorization = ready_inputs()
        first = compile_p42_cycle(
            signer_registry=registry,
            enumeration_witness=witness,
            heldout_events=events,
            edge_authorizations=[authorization],
            namespace="PRODUCTION",
            execution_time="2026-07-28T10:45:00.000000Z",
        )
        self.assertEqual(first["edge_transaction"]["execution_status"], "EXECUTED")
        self.assertEqual(first["edge_transaction"]["execution_count_after"], 1)
        self.assertEqual(first["edge_transaction"]["canonical_graph_mutations"], 1)
        self.assertEqual(first["post_edge_watch"]["status"], "ARMED")
        self.assertEqual(verify_p42_cycle(first)["verdict"], "PASS")

        second = compile_p42_cycle(
            signer_registry=registry,
            enumeration_witness=witness,
            heldout_events=events,
            edge_authorizations=[authorization],
            execution_ledger=first["edge_transaction"]["ledger_after"],
            namespace="PRODUCTION",
            execution_time="2026-07-28T11:00:00.000000Z",
        )
        self.assertEqual(
            second["edge_transaction"]["execution_status"],
            "ALREADY_EXECUTED_IDEMPOTENT",
        )
        self.assertEqual(second["edge_transaction"]["execution_count_after"], 1)
        self.assertFalse(second["edge_transaction"]["ledger_mutated"])
        self.assertEqual(second["edge_transaction"]["canonical_graph_mutations"], 0)

    def test_tampering_and_protected_state_escalation_are_detected(self) -> None:
        cycle = compile_p42_cycle()
        tampered = copy.deepcopy(cycle)
        tampered["state"]["parallel_p42_merges"] = 1
        result = verify_p42_cycle(tampered)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertIn("E_ENVELOPE_DIGEST", result["errors"])
        self.assertIn("E_PROTECTED_STATE_ESCALATION", result["errors"])

    def test_parallel_p42_is_never_merged(self) -> None:
        lineage = p42_parallel_lineage()
        self.assertEqual(
            lineage["relation"],
            "PARALLEL_LABEL_COLLISION_NOT_PARENT_NOT_MERGED",
        )
        self.assertFalse(lineage["merge_executed"])
        self.assertFalse(lineage["private_receipt_embedded"])

    def test_release_is_reproducible_and_nonmutating(self) -> None:
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            kwargs = {
                "implementation_commit": "a" * 40,
                "implementation_tree": "b" * 40,
            }
            left = compile_p42_release(first, **kwargs)
            right = compile_p42_release(second, **kwargs)
            self.assertEqual(left, right)
            self.assertEqual(left["status"], "CANDIDATE_HOLD")
            self.assertEqual(left["exact_enumeration_witnesses"], 0)
            self.assertEqual(left["heldout_outcomes"], 0)
            self.assertEqual(left["independent_ic10_authorizations"], 0)
            self.assertEqual(left["third_edge"], "HELD_NOT_EXECUTED")
            self.assertEqual(left["post_edge_watch"], "HELD_NOT_ARMED")
            self.assertFalse(left["production_mutated"])
            self.assertEqual(
                (Path(first) / "SHA256SUMS").read_text(),
                (Path(second) / "SHA256SUMS").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
