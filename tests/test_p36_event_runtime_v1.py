from __future__ import annotations

import copy
import itertools
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from kc144_crystal.agent_receipts import content_address
from kc144_crystal.p36_runtime import (
    HEART_PARENT,
    P35_STATE_PARENT,
    P36_LOOKUP_KEY,
    P36_RETURN_ADDRESS,
    build_event,
    build_subscription,
    compile_p36_cycle,
    compile_p36_release,
    p36_contract,
    p36_tool_registry,
    public_projection,
    synthetic_subscription_registry,
    unbound_p35_subscription_registry,
    verify_lane_receipt,
    verify_p36_cycle,
)


CUTOFF = "2026-07-28T00:00:00.000000Z"
BASE = content_address("test.base", {"state": "P35"})
SOURCE = content_address("test.source", {"source": "opaque"})
IMPLEMENTATION = content_address("test.handler", {"version": 1})


def event(
    event_class: str = "CARRIER_STATE_CHANGE",
    *,
    origin: str = "TEST",
    observed_at: str = "2026-07-27T23:59:59.000000Z",
    consent: tuple[str, ...] = ("CURRENT_TASK_EXECUTION",),
    partition: int = 0,
    source_verified: bool = True,
    private_key: Ed25519PrivateKey | None = None,
    public_summary: dict | None = None,
) -> dict:
    return build_event(
        event_class=event_class,
        origin_class=origin,
        observed_at=observed_at,
        source_surface="TEST_SURFACE",
        source_commitment=SOURCE,
        source_version="v1",
        public_summary=(
            public_summary
            if public_summary is not None
            else {"partition": partition, "change_class": "TEST"}
        ),
        consent_scope=consent,
        source_verified=source_verified,
        private_key=private_key,
    )


def handlers(registry: dict) -> dict:
    return {
        row["action_id"]: (
            lambda request, action_id=row["action_id"]: {
                "schema": "KC144.TestReadOnlyOutput.V1",
                "action_id": action_id,
                "event_ids": request["event_ids"],
                "truth_effect": "NONE",
                "authority_effect": "NONE",
                "evidence_effect": "NONE",
            }
        )
        for row in registry["subscriptions"]
    }


class P36EventRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = synthetic_subscription_registry()
        cls.handlers = handlers(cls.registry)

    def compile(self, events, **kwargs):
        return compile_p36_cycle(
            events=events,
            subscription_registry=kwargs.pop(
                "subscription_registry", self.registry
            ),
            base_state_digest=BASE,
            cutoff=CUTOFF,
            handlers=kwargs.pop("handlers", self.handlers),
            **kwargs,
        )

    def test_contract_locks_three_distinct_parents_and_five_lanes(self) -> None:
        contract = p36_contract()
        self.assertEqual(contract["lineage"]["state_parent"], P35_STATE_PARENT)
        self.assertNotEqual(
            contract["lineage"]["state_parent"],
            contract["lineage"]["runtime_parent"],
        )
        self.assertEqual(contract["lineage"]["heart_parent"], HEART_PARENT)
        self.assertEqual(len(contract["lanes"]), 5)
        self.assertEqual(contract["census"]["action_subscriptions"], 360)

    def test_all_p36_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1] / "schemas" / "kc144"
        schemas = sorted(root.glob("p36-*.schema.json"))
        self.assertEqual(len(schemas), 4)
        for path in schemas:
            value = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(
                value["$schema"],
                "https://json-schema.org/draft/2020-12/schema",
            )

    def test_unbound_zero_event_cycle_is_receipted_noop_hold(self) -> None:
        cycle = self.compile(
            [],
            subscription_registry=unbound_p35_subscription_registry(),
            handlers={},
        )
        self.assertEqual(len(cycle["lane_receipts"]), 5)
        self.assertEqual(cycle["delta"]["status"], "NOOP_HOLD")
        self.assertEqual(cycle["delta"]["global_state"], "HOLD")
        self.assertEqual(cycle["delta"]["production_events_observed"], 0)
        self.assertEqual(cycle["delta"]["real_outcome_events"], 0)
        self.assertIn(
            "EXACT_P35_SUBSCRIPTION_BODIES_UNBOUND",
            cycle["delta"]["residuals"],
        )
        self.assertEqual(cycle["return_receipt"]["return"], P36_RETURN_ADDRESS)
        self.assertEqual(verify_p36_cycle(cycle)["verdict"], "PASS")

    def test_event_order_permutations_are_byte_identical(self) -> None:
        events = [
            event(partition=0),
            event(
                event_class="GATE_STATE_CHANGE",
                partition=1,
                observed_at="2026-07-27T23:59:58.000000Z",
            ),
            event(
                event_class="LINEAGE_CHANGE",
                partition=2,
                observed_at="2026-07-27T23:59:57.000000Z",
            ),
        ]
        products = {
            json.dumps(
                self.compile(list(order)),
                sort_keys=True,
                separators=(",", ":"),
            )
            for order in itertools.permutations(events)
        }
        self.assertEqual(len(products), 1)

    def test_exact_duplicate_delivery_is_idempotent(self) -> None:
        packet = event()
        once = self.compile([packet])
        twice = self.compile([packet, copy.deepcopy(packet)])
        self.assertEqual(
            once["delta"]["coverage"], twice["delta"]["coverage"]
        )
        watch = twice["lane_receipts"][0]["payload"]
        self.assertEqual(watch["duplicate_delivery_count"], 1)

    def test_synthetic_event_never_counts_as_production_or_outcome(self) -> None:
        cycle = self.compile([event()])
        self.assertGreater(cycle["delta"]["coverage"]["executed_action_count"], 0)
        self.assertEqual(cycle["delta"]["production_events_observed"], 0)
        self.assertEqual(cycle["delta"]["real_outcome_events"], 0)
        self.assertEqual(cycle["delta"]["truth_credit_assigned"], 0)
        self.assertEqual(cycle["delta"]["independent_witness_count"], 0)

    def test_user_choice_is_real_outcome_but_not_empirical_evidence(self) -> None:
        packet = event("USER_CHOICE", origin="USER_OBSERVED", partition=1)
        cycle = self.compile([packet])
        self.assertEqual(cycle["delta"]["real_outcome_events"], 1)
        self.assertEqual(cycle["delta"]["independent_witness_count"], 0)
        self.assertEqual(cycle["delta"]["evidence_effect"], "NONE")
        self.assertEqual(
            cycle["lane_receipts"][4]["payload"]["status"],
            "REGISTRY_HOLD",
        )

    def test_unknown_event_class_is_quarantined(self) -> None:
        packet = event("UNKNOWN_EVENT")
        cycle = self.compile([packet])
        validation = cycle["lane_receipts"][0]["payload"]["validation"][0]
        self.assertEqual(validation["status"], "QUARANTINED")
        self.assertIn("E_EVENT_CLASS", validation["errors"])
        self.assertEqual(cycle["delta"]["coverage"]["executed_action_count"], 0)

    def test_future_event_is_deferred_to_next_epoch(self) -> None:
        packet = event(observed_at="2026-07-28T00:00:01.000000Z")
        cycle = self.compile([packet])
        validation = cycle["lane_receipts"][0]["payload"]["validation"][0]
        self.assertEqual(validation["status"], "DEFERRED_HOLD")
        self.assertIn("E_AFTER_EPOCH_CUTOFF", validation["holds"])

    def test_missing_consent_is_deferred_hold(self) -> None:
        cycle = self.compile([event(consent=("LOCAL_ANALYSIS",))])
        validation = cycle["lane_receipts"][0]["payload"]["validation"][0]
        self.assertEqual(validation["status"], "DEFERRED_HOLD")
        self.assertIn("E_CONSENT_INSUFFICIENT", validation["holds"])

    def test_unverified_source_is_quarantined(self) -> None:
        cycle = self.compile([event(source_verified=False)])
        validation = cycle["lane_receipts"][0]["payload"]["validation"][0]
        self.assertEqual(validation["status"], "QUARANTINED")
        self.assertIn("E_SOURCE_AUTHENTICITY", validation["errors"])

    def test_private_field_in_public_summary_is_quarantined(self) -> None:
        packet = event(public_summary={"partition": 0, "document_id": "SECRET"})
        cycle = self.compile([packet])
        validation = cycle["lane_receipts"][0]["payload"]["validation"][0]
        self.assertIn(
            "E_PRIVATE_FIELD_IN_PUBLIC_SUMMARY", validation["errors"]
        )

    def test_signed_event_and_lane_receipts_verify(self) -> None:
        key = Ed25519PrivateKey.generate()
        packet = event(private_key=key)
        cycle = self.compile([packet], private_key=key)
        self.assertTrue(
            all(
                verify_lane_receipt(
                    receipt,
                    public_keys={
                        receipt["signature"]["key_id"]: key.public_key()
                    },
                )["verdict"]
                == "PASS"
                for receipt in cycle["lane_receipts"]
            )
        )
        self.assertNotIn(
            "TRUSTED_SIGNED_RECEIPTS_UNAVAILABLE",
            cycle["delta"]["residuals"],
        )

    def test_signed_event_mutation_is_quarantined(self) -> None:
        key = Ed25519PrivateKey.generate()
        packet = event(private_key=key)
        packet["public_summary"]["partition"] = 3
        cycle = self.compile([packet], private_key=key)
        validation = cycle["lane_receipts"][0]["payload"]["validation"][0]
        self.assertEqual(validation["status"], "QUARANTINED")
        self.assertIn("E_EVENT_ID", validation["errors"])
        self.assertIn("E_SIGNATURE_INVALID", validation["errors"])

    def test_unmatched_event_executes_zero_actions(self) -> None:
        cycle = self.compile([event(partition=99)])
        self.assertEqual(cycle["delta"]["coverage"]["affected_action_count"], 0)
        self.assertEqual(cycle["delta"]["coverage"]["executed_action_count"], 0)

    def test_missing_handlers_receipt_every_affected_action_as_deferred(self) -> None:
        cycle = self.compile([event()], handlers={})
        coverage = cycle["delta"]["coverage"]
        self.assertGreater(coverage["affected_action_count"], 0)
        self.assertEqual(
            coverage["affected_action_count"],
            coverage["deferred_action_count"],
        )
        self.assertEqual(coverage["missing_resolution_count"], 0)
        self.assertTrue(coverage["all_and_only_affected"])

    def test_handler_cannot_smuggle_truth_or_authority(self) -> None:
        bad = {
            row["action_id"]: lambda request: {
                "truth_credit_assigned": 1,
                "governance_authority_granted": True,
            }
            for row in self.registry["subscriptions"]
        }
        cycle = self.compile([event()], handlers=bad)
        execution = cycle["lane_receipts"][4]["payload"]
        self.assertTrue(
            all(
                row["status"] == "EXECUTION_FAILED"
                for row in execution["execution_receipts"]
            )
        )
        self.assertEqual(cycle["delta"]["status"], "ABORTED_HOLD")
        self.assertFalse(cycle["delta"]["governance_authority_granted"])

    def test_parent_receipt_replay_is_stable_then_detects_tamper(self) -> None:
        parent_cycle = self.compile([])
        parent = parent_cycle["lane_receipts"][0]
        stable = self.compile([], parent_receipts=[parent])
        self.assertEqual(
            stable["lane_receipts"][1]["payload"]["status"],
            "REPLAY_STABLE",
        )
        tampered = copy.deepcopy(parent)
        tampered["payload"]["status"] = "TAMPER"
        drift = self.compile([], parent_receipts=[tampered])
        self.assertEqual(
            drift["lane_receipts"][1]["payload"]["status"],
            "REPLAY_DRIFT",
        )
        self.assertEqual(drift["delta"]["status"], "ABORTED_HOLD")

    def test_public_projection_excludes_private_source_material(self) -> None:
        sentinel = "PRIVATE-SENTINEL-SHOULD-NEVER-EXPORT"
        packet = event(
            public_summary={"partition": 0, "change_class": "SAFE"},
        )
        packet["private_capsule"] = {"source_text": sentinel}
        cycle = self.compile([packet])
        projection = public_projection(cycle)
        self.assertNotIn(sentinel, json.dumps(projection))
        self.assertFalse(projection["private_source_material_included"])

    def test_cycle_tamper_is_detected(self) -> None:
        cycle = self.compile([])
        tampered = copy.deepcopy(cycle)
        tampered["delta"]["global_state"] = "OK"
        verification = verify_p36_cycle(tampered)
        self.assertEqual(verification["verdict"], "FAIL")
        self.assertIn("E_ENVELOPE_DIGEST", verification["errors"])
        self.assertIn("E_DELTA_DIGEST", verification["errors"])
        self.assertIn("E_AUTHORITY_ESCALATION", verification["errors"])

    def test_custom_subscription_predicate_is_bounded_and_deterministic(self) -> None:
        subscription = build_subscription(
            action_id="TEST::CUSTOM",
            front_ids=("TEST::FRONT",),
            event_classes=("USER_CHOICE",),
            predicate={
                "all": [
                    {"eq": ["origin_class", "TEST"]},
                    {"in": ["public_summary.partition", [2, 3]]},
                ]
            },
            implementation_digest=IMPLEMENTATION,
            standing="SYNTHETIC_TEST_FIXTURE",
        )
        self.assertRegex(subscription["subscription_id"], r"^sha256:[0-9a-f]{64}$")

    def test_tool_registry_adds_adapter_and_macrocycle_without_claiming_v1(self) -> None:
        registry = p36_tool_registry()
        self.assertIn("KC144.P31::EXACT_RUNTIME_ADAPTER", registry["descriptors"])
        self.assertIn(P36_LOOKUP_KEY, registry["descriptors"])
        self.assertEqual(
            registry["parent_registry_lookup_key"],
            "KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH",
        )
        self.assertEqual(registry["production_authority"], "HOLD")

    def test_release_is_candidate_hold_and_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            kwargs = {
                "implementation_commit": "1" * 40,
                "implementation_tree": "2" * 40,
            }
            left = compile_p36_release(first, **kwargs)
            right = compile_p36_release(second, **kwargs)
            self.assertEqual(left, right)
            self.assertEqual(left["status"], "CANDIDATE_HOLD")
            self.assertTrue(left["result_id"].startswith("KC144.P36.CANDIDATE::"))
            self.assertEqual(
                (Path(first) / "SHA256SUMS").read_text(),
                (Path(second) / "SHA256SUMS").read_text(),
            )


if __name__ == "__main__":
    unittest.main()
