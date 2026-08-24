from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "elemental_identity",
    ROOT / "tools" / "athena_synapse_elemental_identity_audit.py",
)
module = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(module)

REGISTRY = ROOT / "registry" / "ATHENA_SYNAPSE_ELEMENTAL_IDENTITY_V1.json"


def registry():
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def test_observed_elemental_identity_collisions_are_valid_but_held():
    report = module.audit_identity(registry())
    assert report["ok"]
    assert report["standing"] == "HOLD_ELEMENT_PROFILE_INFERENCE"
    assert report["node_count"] == 4
    assert report["repository_count"] == 4
    assert report["distinct_tree_count"] == 3
    assert report["tree_mirror_groups"] == [["fire", "water"]]
    assert ["earth", "fire", "water"] in report["crystal_collision_groups"]


def test_distinct_repository_names_do_not_satisfy_discriminator_gate():
    row = registry()
    for node in row["nodes"]:
        assert node["admission"] == "HOLD_IDENTITY_DISCRIMINATOR_REQUIRED"
        assert node["repository"].startswith("demeet2k/")
    assert len({node["repository"] for node in row["nodes"]}) == 4
    assert len({node["tree_sha"] for node in row["nodes"]}) == 3


def test_fire_and_water_are_exact_content_mirrors_at_pinned_heads():
    rows = {row["node_id"]: row for row in registry()["nodes"]}
    assert rows["fire"]["tree_sha"] == rows["water"]["tree_sha"]
    assert rows["fire"]["crystal_tree_sha"] == rows["water"]["crystal_tree_sha"]
    assert rows["fire"]["data_tree_sha"] == rows["water"]["data_tree_sha"]
    assert rows["fire"]["revision"] != rows["water"]["revision"]
    assert rows["fire"]["repository"] != rows["water"]["repository"]


def test_shared_mcp_config_cannot_be_used_as_unique_node_identity():
    row = registry()
    native = row["common_native_config"]
    assert native["blob_sha"] == "d37d130dbb1eb885e51b3d64b54b3f56283b1955"
    assert native["crystal_node_id"] == 498
    assert native["mcp_server_name"] == "athena-nervous-system"
    assert "shared_crystal_address" in row["required_discriminator_manifest"]["must_not_use_alone"]


def test_common_runtime_kernel_is_evidence_of_shared_code_not_element_role():
    kernel = registry()["common_runtime_kernel"]
    assert kernel == {
        "MCP/athena_mcp_server.py": "350f8ab682a3a5697b18d60515e008173438a41a",
        "MCP/element_servers": "6667c6fbedbda3b26653d73d3e28b4b0c39b3310",
        "MCP/generate_graph.py": "b867a5b79dfcf83ca1d786f113e078882a2e86a8",
        "MCP/requirements.txt": "3ce29a062030f12740da592d230647a69fd3749d",
    }


def test_legacy_synapse_relation_is_not_promoted_to_core_packet_profile():
    synapse = registry()["shared_nervous_system_contracts"]["synapse_schema"]
    assert synapse["semantic_kind"] == "LEGACY_RELATION_EDGE"
    assert synapse["fields"] == [
        "synapse_id", "src", "dst", "kind", "why_it_exists", "metro_line", "status", "witness"
    ]
    assert "packet_id" not in synapse["fields"]
    assert "oid" not in synapse["fields"]


def test_profile_admission_without_typed_discriminator_is_rejected():
    row = registry()
    bad = copy.deepcopy(row)
    bad["nodes"][0]["admission"] = "PROPOSED_ADAPTER"
    report = module.audit_identity(bad)
    assert not report["ok"]
    assert any(error["code"] == "ELEMENT_NOT_HELD" for error in report["errors"])


def test_missing_collision_class_is_rejected():
    bad = copy.deepcopy(registry())
    bad["collision_groups"] = [
        row for row in bad["collision_groups"] if row["kind"] != "EXACT_REPOSITORY_TREE_MIRROR"
    ]
    report = module.audit_identity(bad)
    assert not report["ok"]
    assert any(
        error["code"] == "MISSING_COLLISION_CLASS" and error["kind"] == "EXACT_REPOSITORY_TREE_MIRROR"
        for error in report["errors"]
    )
