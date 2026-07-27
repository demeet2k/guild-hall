from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from kc144_crystal.agent_receipts import content_address
from kc144_crystal.tool_dispatch import (
    PUBLISHED_PARENT_COMMIT,
    PUBLISHED_PARENT_TREE,
    ToolDispatchError,
    build_dispatch_head_registry,
    build_tool_dispatch_request,
    compile_tool_dispatch_plan,
    compile_tool_dispatch_runtime,
    dispatch_mycelium_tool,
    verify_tool_dispatch_result,
)
from kc144_crystal.tool_registry import (
    AGENT_RECEIPT_LOOKUP_KEY,
    DISPATCH_LOOKUP_KEY,
    P31_LIVE_LOOKUP_KEY,
    locate_mycelium_tool,
    mycelium_tool_registry,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / (
    "registry/parallel-navigation/v1/snapshots/sha256/c8/"
    "c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d.json"
)
BUNDLE = ROOT / (
    "registry/agent-runs/v1/runs/sha256/02/"
    "0277d691593684417720414f2a2fd00436811e86d946cdc4eb2b1c0e975beb04.json"
)


class ToolDispatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = json.loads(SOURCE.read_text(encoding="utf-8"))
        cls.bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
        cls.heads = build_dispatch_head_registry(
            implementation_commit=PUBLISHED_PARENT_COMMIT,
            implementation_tree=PUBLISHED_PARENT_TREE,
        )
        cls.request = build_tool_dispatch_request(
            lookup_query=AGENT_RECEIPT_LOOKUP_KEY,
            operation="verify",
            inputs={
                "parallel_route_snapshot": cls.source,
                "run_receipt_bundle": cls.bundle,
            },
            head_registry=cls.heads,
            allowed_capabilities=("VERIFY_RUN_REPLAY",),
            expected_output_schema="KC144.AgentRunVerification.V1",
        )
        cls.result = dispatch_mycelium_tool(
            cls.request, head_registry=cls.heads
        )

    def test_registry_has_four_distinct_cards(self) -> None:
        registry = mycelium_tool_registry()
        self.assertEqual(len(registry["descriptors"]), 4)
        self.assertIn(DISPATCH_LOOKUP_KEY, registry["descriptors"])
        self.assertIn(P31_LIVE_LOOKUP_KEY, registry["descriptors"])
        self.assertEqual(
            len(
                {
                    card["descriptor_digest"]
                    for card in registry["descriptors"].values()
                }
            ),
            4,
        )

    def test_locate_dispatch_key_and_alias(self) -> None:
        exact = locate_mycelium_tool(DISPATCH_LOOKUP_KEY)
        alias = locate_mycelium_tool("Dynamic_Tool-Dispatch")
        self.assertEqual(exact["status"], "FOUND")
        self.assertEqual(alias["status"], "FOUND")
        self.assertEqual(alias["resolved_lookup_key"], DISPATCH_LOOKUP_KEY)

    def test_plan_has_five_parallel_preflights_then_reduce_and_return(self) -> None:
        plan = compile_tool_dispatch_plan(
            self.request, head_registry=self.heads
        )
        self.assertEqual(plan["status"], "READY")
        self.assertEqual(len(plan["preflight_reports"]), 5)
        self.assertEqual([len(wave) for wave in plan["execution_waves"]], [5, 1, 1])
        self.assertTrue(all(row["status"] == "PASS" for row in plan["preflight_reports"]))

    def test_capacities_one_through_five_are_byte_identical(self) -> None:
        products = [
            json.dumps(
                dispatch_mycelium_tool(
                    self.request,
                    head_registry=self.heads,
                    executor_workers=workers,
                ),
                sort_keys=True,
                separators=(",", ":"),
            )
            for workers in range(1, 6)
        ]
        self.assertTrue(all(product == products[0] for product in products))

    def test_real_registered_handler_executes_and_replays(self) -> None:
        self.assertEqual(self.result["status"], "EXECUTED")
        self.assertEqual(self.result["output"]["verdict"], "PASS")
        verification = verify_tool_dispatch_result(
            self.result, head_registry=self.heads
        )
        self.assertEqual(verification["verdict"], "PASS")
        self.assertEqual(verification["replay_status"], "REPLAY_STABLE")

    def test_kc54_return_is_exact_and_br019_remains_open(self) -> None:
        holonomy = self.result["holonomy_receipt"]
        self.assertTrue(holonomy["exact_retrace"])
        self.assertEqual(holonomy["translation_defect"], 0)
        self.assertIn("BR019", holonomy["open_bridge_ids"])
        self.assertFalse(holonomy["content_transport_certified"])

    def test_unknown_tool_is_blocked_with_addressed_result(self) -> None:
        request = build_tool_dispatch_request(
            lookup_query="almost a tool",
            operation="verify",
            inputs={},
            head_registry=self.heads,
            allowed_capabilities=(),
        )
        result = dispatch_mycelium_tool(request, head_registry=self.heads)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("E_TOOL_NOT_FOUND", result["error_codes"])
        self.assertRegex(result["result_digest"], r"^sha256:[0-9a-f]{64}$")

    def test_missing_capability_and_input_fail_closed(self) -> None:
        request = build_tool_dispatch_request(
            lookup_query=AGENT_RECEIPT_LOOKUP_KEY,
            operation="verify",
            inputs={},
            head_registry=self.heads,
            allowed_capabilities=(),
        )
        result = dispatch_mycelium_tool(request, head_registry=self.heads)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("E_CAPABILITY_DENIED", result["error_codes"])
        self.assertIn("E_INPUT_SCHEMA", result["error_codes"])
        self.assertIsNone(result["output"])

    def test_unknown_operation_is_blocked(self) -> None:
        request = build_tool_dispatch_request(
            lookup_query=AGENT_RECEIPT_LOOKUP_KEY,
            operation="shell",
            inputs={},
            head_registry=self.heads,
            allowed_capabilities=(),
        )
        result = dispatch_mycelium_tool(request, head_registry=self.heads)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("E_OPERATION_UNKNOWN", result["error_codes"])

    def test_p31_is_exactly_locatable_but_not_substituted(self) -> None:
        request = build_tool_dispatch_request(
            lookup_query=P31_LIVE_LOOKUP_KEY,
            operation="navigate",
            inputs={"query": "route through P31"},
            head_registry=self.heads,
            allowed_capabilities=("P31_LIVE_RUNTIME",),
        )
        result = dispatch_mycelium_tool(request, head_registry=self.heads)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("E_EXTERNAL_RUNTIME_REQUIRED", result["error_codes"])
        self.assertIn("E_HANDLER_UNREGISTERED", result["error_codes"])

    def test_stale_heads_and_request_tamper_fail_closed(self) -> None:
        stale = copy.deepcopy(self.heads)
        stale["implementation_head"]["tree"] = "1" * 40
        request = copy.deepcopy(self.request)
        request["head_registry_digest"] = stale["registry_digest"]
        request_body = {key: value for key, value in request.items() if key != "request_id"}
        request["request_id"] = content_address("kc144.dispatch.request", request_body)
        result = dispatch_mycelium_tool(request, head_registry=stale)
        self.assertEqual(result["status"], "BLOCKED")
        self.assertIn("E_HEAD_REGISTRY_DIGEST", result["error_codes"])

        tampered = copy.deepcopy(self.result)
        tampered["output"]["verdict"] = "FAIL"
        verification = verify_tool_dispatch_result(
            tampered, head_registry=self.heads
        )
        self.assertEqual(verification["verdict"], "FAIL")
        self.assertIn("E_RESULT_DIGEST", verification["errors"])
        self.assertIn("E_REPLAY_DRIFT", verification["errors"])

    def test_route_budget_and_authority_escalation_are_blocked(self) -> None:
        short = build_tool_dispatch_request(
            lookup_query=DISPATCH_LOOKUP_KEY,
            operation="registry",
            inputs={},
            head_registry=self.heads,
            allowed_capabilities=("RESOLVE_EXACT_TOOL_CARD",),
            route_budget=0,
        )
        short_result = dispatch_mycelium_tool(short, head_registry=self.heads)
        self.assertIn("E_ROUTE_BUDGET", short_result["error_codes"])
        escalated = copy.deepcopy(self.request)
        escalated["governance_authority_granted"] = True
        body = {key: value for key, value in escalated.items() if key != "request_id"}
        escalated["request_id"] = content_address("kc144.dispatch.request", body)
        result = dispatch_mycelium_tool(escalated, head_registry=self.heads)
        self.assertIn("E_AUTHORITY_ESCALATION", result["error_codes"])
        self.assertEqual(result["status"], "BLOCKED")

    def test_bad_capacity_is_programmer_error(self) -> None:
        with self.assertRaises(ToolDispatchError):
            compile_tool_dispatch_plan(
                self.request, head_registry=self.heads, executor_workers=6
            )

    def test_runtime_compiler_emits_complete_release(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_tool_dispatch_runtime(
                temporary,
                implementation_commit=PUBLISHED_PARENT_COMMIT,
                implementation_tree=PUBLISHED_PARENT_TREE,
                parallel_route_snapshot=self.source,
                run_receipt_bundle=self.bundle,
            )
            self.assertEqual(release["dispatch_status"], "EXECUTED")
            self.assertEqual(release["verification_verdict"], "PASS")
            self.assertEqual(release["preflight_lanes"], 5)
            self.assertEqual(
                len(list(Path(temporary).rglob("*.json"))),
                9,
            )


if __name__ == "__main__":
    unittest.main()
