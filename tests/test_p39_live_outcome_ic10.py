from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from kc144_crystal.agent_receipts import canonical_bytes
from kc144_crystal.p39_runtime import (
    P39_CUTOFF,
    P39_IC10_GATES,
    P39_LANES,
    P39_LOOKUP_KEY,
    P39_THRESHOLD,
    build_ic10_convergence_return,
    build_ic10_enrollment,
    build_live_outcome,
    calibrate_weights,
    compile_live_outcome_corpus,
    compile_p39_cycle,
    compile_p39_release,
    empty_ic10_registry,
    enroll_ic10_signer,
    evaluate_ic10_convergence,
    p39_contract,
    p39_policy,
    verify_ic10_registry,
    verify_p39_cycle,
)


def live_outcomes() -> list[dict]:
    observer = Ed25519PrivateKey.generate()
    result = []
    for partition_index, partition in enumerate(("CALIBRATION", "HELD_OUT")):
        for index in range(12):
            route_index = index % 3
            result.append(
                build_live_outcome(
                    outcome_class=(
                        "TASK_OUTCOME" if index % 2 == 0 else "EMPIRICAL_RESULT"
                    ),
                    origin_class="CONNECTOR_OBSERVED",
                    observed_at=(
                        f"2026-07-29T{partition_index + 1:02d}:{index:02d}:00.000000Z"
                    ),
                    source_surface=f"SURFACE_{index % 3}",
                    source_commitment=(
                        "sha256:"
                        + f"{index + 100 * partition_index + 1:064x}"
                    ),
                    evidence_unit=(
                        "sha256:"
                        + f"{index + 1000 * partition_index + 1:064x}"
                    ),
                    route_id=f"ROUTE_{route_index}",
                    partition=partition,
                    value=float(1 if (index + route_index) % 3 else 0),
                    observer_id="external-observer",
                    private_key=observer,
                )
            )
    return result


def five_seat_registry():
    registry = empty_ic10_registry()
    keys = []
    for index in range(5):
        key = Ed25519PrivateKey.generate()
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
        import base64

        registry = enroll_ic10_signer(
            registry,
            enrollment,
            base64.urlsafe_b64encode(proof).decode().rstrip("="),
        )
        keys.append((key, enrollment))
    return keys, registry


def convergence_returns(keys, cycle, count=3):
    result = []
    for index, (key, enrollment) in enumerate(keys[:count]):
        result.append(
            build_ic10_convergence_return(
                candidate_root=cycle["state"]["candidate_root"],
                corpus_root=cycle["corpus"]["corpus_root"],
                calibration_digest=cycle["calibration"]["calibration_digest"],
                policy_digest=cycle["policy"]["policy_digest"],
                signer_id=enrollment["signer_id"],
                organization_id=enrollment["organization_id"],
                control_root=enrollment["control_root"],
                private_key=key,
                issued_at="2026-07-29T12:00:00.000000Z",
                expires_at="2026-07-30T12:00:00.000000Z",
                nonce=f"nonce-{index}",
            )
        )
    return result


class P39LiveOutcomeIC10Tests(unittest.TestCase):
    def test_all_p39_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1] / "schemas" / "kc144"
        schemas = sorted(root.glob("p39-*.schema.json"))
        self.assertEqual(len(schemas), 4)
        for path in schemas:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                value["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )

    def test_contract_freezes_full_macrocycle(self) -> None:
        contract = p39_contract()
        self.assertEqual(contract["lookup_key"], P39_LOOKUP_KEY)
        self.assertEqual([row["lane"] for row in contract["lanes"]], list(P39_LANES))
        self.assertEqual(p39_policy()["ic10"]["threshold"], P39_THRESHOLD)

    def test_empty_corpus_is_honest_hold(self) -> None:
        corpus = compile_live_outcome_corpus([])
        calibration = calibrate_weights(corpus)
        self.assertEqual(corpus["status"], "CORPUS_HOLD")
        self.assertEqual(calibration["status"], "CALIBRATION_HOLD")
        self.assertEqual(calibration["canonical_weight_updates_executed"], 0)

    def test_signed_live_corpus_has_disjoint_partitions(self) -> None:
        corpus = compile_live_outcome_corpus(live_outcomes())
        self.assertEqual(corpus["status"], "CORPUS_READY")
        self.assertEqual(corpus["census"]["accepted"], 24)
        self.assertEqual(corpus["leaking_evidence_units"], [])

    def test_cross_partition_leakage_is_fatal(self) -> None:
        values = live_outcomes()
        held_out = next(row for row in values if row["partition"] == "HELD_OUT")
        calibration = next(
            row for row in values if row["partition"] == "CALIBRATION"
        )
        held_out["evidence_unit"] = calibration["evidence_unit"]
        corpus = compile_live_outcome_corpus(values)
        self.assertEqual(corpus["status"], "CORPUS_HOLD")
        self.assertTrue(corpus["leaking_evidence_units"])

    def test_same_partition_evidence_unit_cannot_inflate_census(self) -> None:
        values = live_outcomes()
        calibration = [
            row for row in values if row["partition"] == "CALIBRATION"
        ]
        calibration[1]["evidence_unit"] = calibration[0]["evidence_unit"]
        corpus = compile_live_outcome_corpus(values)
        self.assertEqual(corpus["status"], "CORPUS_HOLD")
        self.assertTrue(
            any(
                "E_DUPLICATE_EVIDENCE_UNIT" in row["errors"]
                for row in corpus["rejected"]
            )
        )

    def test_observation_tamper_fails_signature_and_digest(self) -> None:
        values = live_outcomes()
        values[0]["value"] = 1.0 - values[0]["value"]
        corpus = compile_live_outcome_corpus(values)
        rejected = corpus["rejected"]
        self.assertTrue(
            any("E_OBSERVATION_DIGEST" in row["errors"] for row in rejected)
        )
        self.assertTrue(any("E_SIGNATURE" in row["errors"] for row in rejected))

    def test_calibration_proposes_but_never_commits_weights(self) -> None:
        calibration = calibrate_weights(compile_live_outcome_corpus(live_outcomes()))
        self.assertEqual(calibration["status"], "CALIBRATION_READY")
        self.assertEqual(len(calibration["proposed_weights"]), 3)
        self.assertEqual(calibration["canonical_weight_updates_executed"], 0)
        self.assertFalse(calibration["production_mutated"])

    def test_incomplete_registry_is_valid_only_during_enrollment(self) -> None:
        registry = empty_ic10_registry()
        self.assertEqual(
            verify_ic10_registry(registry, allow_incomplete=True)["verdict"], "PASS"
        )
        self.assertEqual(verify_ic10_registry(registry)["verdict"], "FAIL")

    def test_fixed_registry_requires_five_independent_control_roots(self) -> None:
        _, registry = five_seat_registry()
        self.assertEqual(verify_ic10_registry(registry)["verdict"], "PASS")
        self.assertEqual(len(registry["entries"]), 5)
        self.assertFalse(registry["authority_granted_by_enrollment"])

    def test_duplicate_organization_cannot_enroll(self) -> None:
        keys, registry = five_seat_registry()
        key = Ed25519PrivateKey.generate()
        enrollment = build_ic10_enrollment(
            signer_id="sixth",
            organization_id=keys[0][1]["organization_id"],
            control_root="sha256:" + "9" * 64,
            public_key=key.public_key(),
            valid_from="2026-07-29T00:00:00.000000Z",
            valid_until="2026-07-30T00:00:00.000000Z",
        )
        proof = key.sign(
            b"KC144.P39.IC10-ENROLLMENT.V1\0" + canonical_bytes(enrollment)
        )
        import base64

        with self.assertRaises(Exception):
            enroll_ic10_signer(
                registry,
                enrollment,
                base64.urlsafe_b64encode(proof).decode().rstrip("="),
            )

    def test_two_of_five_does_not_converge(self) -> None:
        keys, registry = five_seat_registry()
        cycle = compile_p39_cycle(
            observations=live_outcomes(), signer_registry=registry
        )
        returns = convergence_returns(keys, cycle, count=2)
        final = compile_p39_cycle(
            observations=live_outcomes(),
            signer_registry=registry,
            ic10_returns=returns,
        )
        self.assertEqual(final["ic10_convergence"]["status"], "HOLD")
        self.assertEqual(final["successor_decision"]["decision"], "HOLD")

    def test_three_of_five_exactly_bound_returns_converge(self) -> None:
        outcomes = live_outcomes()
        keys, registry = five_seat_registry()
        first = compile_p39_cycle(
            observations=outcomes, signer_registry=registry
        )
        returns = convergence_returns(keys, first, count=3)
        final = compile_p39_cycle(
            observations=outcomes,
            signer_registry=registry,
            ic10_returns=returns,
        )
        self.assertEqual(final["ic10_convergence"]["status"], "CONVERGED")
        self.assertEqual(
            final["successor_decision"]["decision"], "SUCCESSOR_READY"
        )
        self.assertEqual(final["state"]["global_release"], "READY_FOR_P40_ACTIVATION")
        self.assertEqual(final["state"]["canonical_weight_updates_executed"], 0)
        self.assertFalse(final["state"]["successor_activated"])
        self.assertEqual(verify_p39_cycle(final)["verdict"], "PASS")

    def test_return_bound_to_other_corpus_fails_closed(self) -> None:
        outcomes = live_outcomes()
        keys, registry = five_seat_registry()
        first = compile_p39_cycle(
            observations=outcomes, signer_registry=registry
        )
        returns = convergence_returns(keys, first, count=3)
        returns[0]["corpus_root"] = "sha256:" + "f" * 64
        final = compile_p39_cycle(
            observations=outcomes,
            signer_registry=registry,
            ic10_returns=returns,
        )
        self.assertEqual(final["ic10_convergence"]["status"], "HOLD")

    def test_all_ten_ic10_gates_are_required(self) -> None:
        outcomes = live_outcomes()
        keys, registry = five_seat_registry()
        first = compile_p39_cycle(
            observations=outcomes, signer_registry=registry
        )
        returns = convergence_returns(keys, first, count=3)
        returns[0]["gates"] = returns[0]["gates"][:-1]
        final = compile_p39_cycle(
            observations=outcomes,
            signer_registry=registry,
            ic10_returns=returns,
        )
        self.assertEqual(len(P39_IC10_GATES), 10)
        self.assertEqual(final["ic10_convergence"]["status"], "HOLD")

    def test_default_cycle_is_replayable_hold(self) -> None:
        left = compile_p39_cycle()
        right = compile_p39_cycle()
        self.assertEqual(left, right)
        self.assertEqual(left["state"]["global_release"], "HOLD")
        self.assertEqual(left["state"]["truth_effect"], "NONE")
        self.assertEqual(verify_p39_cycle(left)["verdict"], "PASS")

    def test_cycle_tamper_is_detected(self) -> None:
        cycle = compile_p39_cycle()
        tampered = copy.deepcopy(cycle)
        tampered["state"]["production_mutated"] = True
        verification = verify_p39_cycle(tampered)
        self.assertEqual(verification["verdict"], "FAIL")
        self.assertIn("E_ENVELOPE_DIGEST", verification["errors"])
        self.assertIn("E_PROTECTED_STATE_ESCALATION", verification["errors"])

    def test_release_is_reproducible_candidate_hold(self) -> None:
        with (
            tempfile.TemporaryDirectory() as first,
            tempfile.TemporaryDirectory() as second,
        ):
            kwargs = {
                "implementation_commit": "a" * 40,
                "implementation_tree": "b" * 40,
            }
            left = compile_p39_release(first, **kwargs)
            right = compile_p39_release(second, **kwargs)
            self.assertEqual(left, right)
            self.assertEqual(left["status"], "CANDIDATE_HOLD")
            self.assertEqual(left["live_outcomes"], 0)
            self.assertEqual(left["independent_ic10_returns"], 0)
            self.assertEqual(
                (Path(first) / "SHA256SUMS").read_text(),
                (Path(second) / "SHA256SUMS").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
