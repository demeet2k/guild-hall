from __future__ import annotations

import base64
import copy
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from kc144_crystal.agent_receipts import canonical_bytes
from kc144_crystal.p39_runtime import (
    build_ic10_convergence_return,
    build_ic10_enrollment,
    build_live_outcome,
    compile_p39_cycle,
    empty_ic10_registry,
    enroll_ic10_signer,
)
from kc144_crystal.p40_runtime import (
    P40_LANES,
    P40_LOOKUP_KEY,
    PUBLIC_P39_RESULT_ID,
    SIBLING_P39_PARENT_ID,
    SIBLING_P40_RESULT_ID,
    build_canonical_weight_state,
    compile_p40_cycle,
    compile_p40_release,
    p40_contract,
    p40_sibling_capsule,
    verify_p40_cycle,
)


def _key(index: int) -> Ed25519PrivateKey:
    return Ed25519PrivateKey.from_private_bytes(bytes([index + 1]) * 32)


def ready_p39_cycle() -> dict:
    observer = _key(20)
    outcomes = []
    for partition_index, partition in enumerate(("CALIBRATION", "HELD_OUT")):
        for index in range(12):
            route_index = index % 3
            outcomes.append(
                build_live_outcome(
                    outcome_class=(
                        "TASK_OUTCOME" if index % 2 == 0 else "EMPIRICAL_RESULT"
                    ),
                    origin_class="CONNECTOR_OBSERVED",
                    observed_at=(
                        f"2026-07-29T{partition_index + 1:02d}:"
                        f"{index:02d}:00.000000Z"
                    ),
                    source_surface=f"SURFACE_{index % 3}",
                    source_commitment=(
                        "sha256:" + f"{index + 100 * partition_index + 1:064x}"
                    ),
                    evidence_unit=(
                        "sha256:" + f"{index + 1000 * partition_index + 1:064x}"
                    ),
                    route_id=f"ROUTE_{route_index}",
                    partition=partition,
                    value=float(1 if (index + route_index) % 3 else 0),
                    observer_id="independent-observer",
                    private_key=observer,
                )
            )
    registry = empty_ic10_registry()
    signers = []
    for index in range(5):
        key = _key(index)
        enrollment = build_ic10_enrollment(
            signer_id=f"signer-{index}",
            organization_id=f"organization-{index}",
            control_root="sha256:" + f"{index + 500:064x}",
            public_key=key.public_key(),
            valid_from="2026-07-29T00:00:00.000000Z",
            valid_until="2026-07-30T23:59:59.000000Z",
        )
        proof = key.sign(
            b"KC144.P39.IC10-ENROLLMENT.V1\0" + canonical_bytes(enrollment)
        )
        registry = enroll_ic10_signer(
            registry,
            enrollment,
            base64.urlsafe_b64encode(proof).decode().rstrip("="),
        )
        signers.append((key, enrollment))
    first = compile_p39_cycle(observations=outcomes, signer_registry=registry)
    returns = []
    for index, (key, enrollment) in enumerate(signers[:3]):
        returns.append(
            build_ic10_convergence_return(
                candidate_root=first["state"]["candidate_root"],
                corpus_root=first["corpus"]["corpus_root"],
                calibration_digest=first["calibration"]["calibration_digest"],
                policy_digest=first["policy"]["policy_digest"],
                signer_id=enrollment["signer_id"],
                organization_id=enrollment["organization_id"],
                control_root=enrollment["control_root"],
                private_key=key,
                issued_at="2026-07-29T12:00:00.000000Z",
                expires_at="2026-07-30T12:00:00.000000Z",
                nonce=f"p40-ready-{index}",
            )
        )
    return compile_p39_cycle(
        observations=outcomes,
        signer_registry=registry,
        ic10_returns=returns,
    )


def three_route_state() -> dict:
    return build_canonical_weight_state(
        [
            {"route_id": "ROUTE_0", "weight": 0.333333333333},
            {"route_id": "ROUTE_1", "weight": 0.333333333333},
            {"route_id": "ROUTE_2", "weight": 0.333333333334},
        ]
    )


class P40ActivationTransactionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.ready_p39 = ready_p39_cycle()

    def test_all_p40_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1] / "schemas" / "kc144"
        schemas = sorted(root.glob("p40-*.schema.json"))
        self.assertEqual(len(schemas), 4)
        for path in schemas:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                value["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )

    def test_contract_freezes_eight_lane_macrocycle(self) -> None:
        contract = p40_contract()
        self.assertEqual(contract["lookup_key"], P40_LOOKUP_KEY)
        self.assertEqual([row["lane"] for row in contract["lanes"]], list(P40_LANES))
        self.assertIn(
            "SIBLING_REFERENCE_IS_NOT_MERGE_PARENT",
            contract["noncollapse"],
        )

    def test_sibling_is_exact_and_not_the_public_parent(self) -> None:
        capsule = p40_sibling_capsule()
        self.assertEqual(capsule["result_id"], SIBLING_P40_RESULT_ID)
        self.assertEqual(capsule["parent_result_id"], SIBLING_P39_PARENT_ID)
        self.assertNotEqual(capsule["parent_result_id"], PUBLIC_P39_RESULT_ID)
        self.assertEqual(
            capsule["admissibility"],
            "REFERENCE_ONLY_NOT_PARENT_NOT_MERGED",
        )

    def test_default_cycle_is_replayable_hold(self) -> None:
        left = compile_p40_cycle()
        right = compile_p40_cycle()
        self.assertEqual(left, right)
        self.assertEqual(left["state"]["global_release"], "HOLD")
        self.assertEqual(left["state"]["canonical_weight_updates_executed"], 0)
        self.assertFalse(left["state"]["successor_activated"])
        self.assertEqual(
            left["post_activation_watch"]["status"], "HELD_NOT_ARMED"
        )
        self.assertEqual(verify_p40_cycle(left)["verdict"], "PASS")

    def test_verified_ready_p39_and_exact_cas_commit_once(self) -> None:
        base = three_route_state()
        cycle = compile_p40_cycle(
            p39_cycle=self.ready_p39,
            canonical_state=base,
            expected_base_state_root=base["state_root"],
            namespace="PRODUCTION",
        )
        transaction = cycle["activation_transaction"]
        self.assertEqual(transaction["status"], "COMMITTED")
        self.assertEqual(transaction["canonical_weight_updates_executed"], 3)
        self.assertTrue(transaction["successor_activated"])
        self.assertTrue(transaction["production_mutated"])
        self.assertEqual(cycle["post_activation_watch"]["status"], "ARMED")
        self.assertEqual(cycle["state"]["global_release"], "ACTIVATED")
        self.assertEqual(verify_p40_cycle(cycle)["verdict"], "PASS")

    def test_test_namespace_never_claims_production_mutation(self) -> None:
        base = three_route_state()
        cycle = compile_p40_cycle(
            p39_cycle=self.ready_p39,
            canonical_state=base,
            expected_base_state_root=base["state_root"],
            namespace="TEST",
        )
        transaction = cycle["activation_transaction"]
        self.assertEqual(transaction["status"], "COMMITTED")
        self.assertTrue(transaction["test_simulation"])
        self.assertFalse(transaction["production_mutated"])
        self.assertEqual(cycle["state"]["global_release"], "SIMULATED_READY")
        self.assertEqual(verify_p40_cycle(cycle)["verdict"], "PASS")

    def test_compare_and_swap_mismatch_fails_closed(self) -> None:
        base = three_route_state()
        cycle = compile_p40_cycle(
            p39_cycle=self.ready_p39,
            canonical_state=base,
            expected_base_state_root="sha256:" + "f" * 64,
        )
        self.assertEqual(cycle["activation_transaction"]["status"], "HOLD")
        self.assertEqual(
            cycle["activation_transaction"]["compare_and_swap"], "FAIL"
        )
        self.assertFalse(cycle["state"]["successor_activated"])
        self.assertEqual(verify_p40_cycle(cycle)["verdict"], "PASS")

    def test_route_set_mismatch_fails_closed(self) -> None:
        base = build_canonical_weight_state(
            [{"route_id": "OTHER_ROUTE", "weight": 1.0}]
        )
        cycle = compile_p40_cycle(
            p39_cycle=self.ready_p39,
            canonical_state=base,
            expected_base_state_root=base["state_root"],
        )
        self.assertFalse(cycle["activation_transaction"]["route_set_compatible"])
        self.assertEqual(cycle["activation_transaction"]["status"], "HOLD")

    def test_tampered_p39_cycle_cannot_authorize(self) -> None:
        tampered = copy.deepcopy(self.ready_p39)
        tampered["state"]["canonical_successor_decision"] = "HOLD"
        base = three_route_state()
        cycle = compile_p40_cycle(
            p39_cycle=tampered,
            canonical_state=base,
            expected_base_state_root=base["state_root"],
        )
        self.assertEqual(cycle["public_parent_binding"]["authorization"], "HOLD")
        self.assertEqual(cycle["activation_transaction"]["status"], "HOLD")

    def test_sibling_tamper_is_quarantined_and_detected(self) -> None:
        sibling = p40_sibling_capsule()
        sibling["boundary"]["held_out_outcomes"] = 5
        cycle = compile_p40_cycle(sibling_capsule=sibling)
        self.assertEqual(cycle["sibling_binding"]["status"], "QUARANTINED")
        verification = verify_p40_cycle(cycle)
        self.assertEqual(verification["verdict"], "FAIL")
        self.assertIn("E_SIBLING_CAPSULE", verification["errors"])

    def test_committed_cycle_is_deterministic_and_idempotent(self) -> None:
        base = three_route_state()
        kwargs = {
            "p39_cycle": self.ready_p39,
            "canonical_state": base,
            "expected_base_state_root": base["state_root"],
            "namespace": "PRODUCTION",
        }
        self.assertEqual(compile_p40_cycle(**kwargs), compile_p40_cycle(**kwargs))

    def test_cycle_tamper_is_detected(self) -> None:
        cycle = compile_p40_cycle()
        tampered = copy.deepcopy(cycle)
        tampered["state"]["sibling_merges"] = 1
        verification = verify_p40_cycle(tampered)
        self.assertEqual(verification["verdict"], "FAIL")
        self.assertIn("E_ENVELOPE_DIGEST", verification["errors"])
        self.assertIn("E_PROTECTED_STATE_ESCALATION", verification["errors"])

    def test_release_is_reproducible_honest_hold(self) -> None:
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            kwargs = {
                "implementation_commit": "a" * 40,
                "implementation_tree": "b" * 40,
            }
            left = compile_p40_release(first, **kwargs)
            right = compile_p40_release(second, **kwargs)
            self.assertEqual(left, right)
            self.assertEqual(left["status"], "CANDIDATE_HOLD")
            self.assertEqual(left["p39_authorization"], "HOLD")
            self.assertEqual(left["sibling_merges"], 0)
            self.assertFalse(left["production_mutated"])
            self.assertEqual(
                (Path(first) / "SHA256SUMS").read_text(),
                (Path(second) / "SHA256SUMS").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
