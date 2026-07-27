from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from kc144_crystal.agent_receipts import content_address
from kc144_crystal.cli import build_parser
from kc144_crystal.navigation import navigation_relations
from kc144_crystal.systematic import compile_systematic_framework
from kc144_crystal.tool_registry import (
    agent_run_receipt_tool_descriptor,
    locate_mycelium_tool,
    mycelium_tool_registry,
)
from kc144_crystal.v4 import compile_mycelium_framework


LOOKUP_KEY = "KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS"


class MyceliumToolRegistryTests(unittest.TestCase):
    def test_descriptor_coordinates_are_derived_and_complete(self) -> None:
        descriptor = agent_run_receipt_tool_descriptor()
        self.assertEqual(
            [
                (row["gid"], row["station"], row["grid"])
                for row in descriptor["coordinate_bindings"]
            ],
            [
                (3, "H03", "R01C03"),
                (5, "H05", "R01C05"),
                (6, "H06", "R01C06"),
                (135, "M03", "R12C03"),
                (141, "M09", "R12C09"),
                (144, "M12", "R12C12"),
            ],
        )
        body = {
            key: value
            for key, value in descriptor.items()
            if key != "descriptor_digest"
        }
        self.assertEqual(
            descriptor["descriptor_digest"],
            content_address("kc144.mycelium.tool-descriptor", body),
        )

    def test_exact_key_and_complete_alias_resolve(self) -> None:
        exact = locate_mycelium_tool(LOOKUP_KEY)
        alias = locate_mycelium_tool("Parallel_Audit-Chain")
        self.assertEqual(exact["status"], "FOUND")
        self.assertEqual(exact["resolution"], "EXACT_LOOKUP_KEY")
        self.assertEqual(alias["status"], "FOUND")
        self.assertEqual(alias["resolution"], "EXACT_ALIAS")
        self.assertEqual(alias["resolved_lookup_key"], LOOKUP_KEY)

    def test_unknown_lookup_cannot_execute(self) -> None:
        report = locate_mycelium_tool("similar sounding unknown tool")
        self.assertEqual(report["status"], "NOT_FOUND")
        self.assertEqual(report["commands"], {})
        self.assertEqual(report["coordinate_routes"], [])

    def test_h06_routes_are_exact_and_expose_br019(self) -> None:
        report = locate_mycelium_tool(LOOKUP_KEY)
        routes = {row["gid"]: row for row in report["coordinate_routes"]}
        self.assertEqual(routes[3]["path"], [6, 1, 2, 3])
        self.assertEqual(routes[5]["path"], [6, 5])
        self.assertEqual(routes[6]["path"], [6])
        self.assertEqual(
            routes[135]["path"],
            [6, 1, 144, 143, 142, 141, 140, 139, 138, 137, 136, 135],
        )
        self.assertEqual(routes[141]["path"], [6, 1, 144, 143, 142, 141])
        self.assertEqual(routes[144]["path"], [6, 1, 144])
        for gid in (3, 5, 6):
            self.assertEqual(routes[gid]["open_bridge_ids"], [])
            self.assertEqual(routes[gid]["standing"], "STRUCTURAL_ROUTE")
        for gid in (135, 141, 144):
            self.assertEqual(routes[gid]["open_bridge_ids"], ["BR019"])
            self.assertEqual(
                routes[gid]["standing"],
                "DECLARED_ROUTE_WITH_OPEN_TRANSPORT_CERTIFICATION",
            )

    def test_registry_overlay_does_not_mutate_base_graph(self) -> None:
        before = json.dumps(navigation_relations("both"), sort_keys=True)
        mycelium_tool_registry()
        locate_mycelium_tool(LOOKUP_KEY)
        after = json.dumps(navigation_relations("both"), sort_keys=True)
        self.assertEqual(before, after)

    def test_route_budget_marks_unreachable_anchors_without_hiding_tool(self) -> None:
        report = locate_mycelium_tool(LOOKUP_KEY, route_budget=0)
        self.assertEqual(report["status"], "FOUND")
        routes = {row["gid"]: row for row in report["coordinate_routes"]}
        self.assertEqual(routes[6]["standing"], "STRUCTURAL_ROUTE")
        self.assertTrue(
            all(
                routes[gid]["standing"] == "OUTSIDE_ROUTE_BUDGET"
                for gid in (3, 5, 135, 141, 144)
            )
        )

    def test_cli_parser_accepts_every_descriptor_command(self) -> None:
        parser = build_parser()
        commands = agent_run_receipt_tool_descriptor()["commands"]
        for key in ("locate", "plan", "run", "verify"):
            argv = [
                token
                for token in commands[key][1:]
                if not token.startswith("{")
            ]
            if key == "plan":
                argv.append("snapshot.json")
            elif key == "run":
                argv.insert(1, "snapshot.json")
            elif key == "verify":
                argv.insert(1, "bundle.json")
                argv.append("snapshot.json")
            parser.parse_args(argv)

    def test_systematic_and_v4_compilers_emit_locatable_tool(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_systematic_framework(temporary)
            registry = json.loads(
                (Path(temporary) / "tool_registry_v1.json").read_text()
            )
            self.assertIn(LOOKUP_KEY, registry["descriptors"])
            self.assertEqual(
                release["mycelium_tools"]["registry_digest"],
                registry["registry_digest"],
            )
        with tempfile.TemporaryDirectory() as temporary:
            release = compile_mycelium_framework(temporary)
            location = json.loads(
                (Path(temporary) / "agent_run_receipt_location.json").read_text()
            )
            self.assertEqual(location["status"], "FOUND")
            self.assertEqual(release["tool_runtime"]["coordinate_routes"], 6)


if __name__ == "__main__":
    unittest.main()
