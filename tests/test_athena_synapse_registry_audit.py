import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("registry_audit", ROOT / "tools" / "athena_synapse_registry_audit.py")
audit = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(audit)


def registry():
    return json.loads((ROOT / "registry" / "ATHENA_SYNAPSE_NODES_V1.json").read_text())


def test_current_registry_passes_without_promoting_manifestless_elements():
    result = audit.audit_registry(registry())
    assert result["ok"]
    assert result["status_counts"]["MANIFEST_REQUIRED"] == 4
    assert result["status_counts"]["PROPOSED_ADAPTER"] == 2
    assert result["status_counts"]["CANONICAL_ABI"] == 1


def test_duplicate_node_id_fails():
    value = registry()
    value["nodes"][1]["node_id"] = value["nodes"][0]["node_id"]
    result = audit.audit_registry(value)
    assert not result["ok"]
    assert any(e["code"] == "DUPLICATE_NODE_ID" for e in result["errors"])


def test_duplicate_repository_fails():
    value = registry()
    value["nodes"][1]["repository"] = value["nodes"][0]["repository"]
    result = audit.audit_registry(value)
    assert any(e["code"] == "DUPLICATE_REPOSITORY" for e in result["errors"])


def test_profile_collision_fails():
    value = registry()
    value["nodes"][1]["synapse_profiles"] = [value["nodes"][0]["synapse_profiles"][0]]
    result = audit.audit_registry(value)
    assert any(e["code"] == "PROFILE_COLLISION" for e in result["errors"])


def test_manifest_required_node_cannot_claim_profile():
    value = registry()
    water = next(n for n in value["nodes"] if n["node_id"] == "water")
    water["synapse_profiles"] = ["WATER_MAGIC_V1"]
    result = audit.audit_registry(value)
    assert any(e["code"] == "UNADMITTED_PROFILE_CLAIM" for e in result["errors"])


def test_proposed_adapter_needs_evidence_and_profile():
    value = registry()
    core = next(n for n in value["nodes"] if n["node_id"] == "athena-core")
    core["synapse_profiles"] = []
    core["evidence_refs"] = []
    result = audit.audit_registry(value)
    codes = {e["code"] for e in result["errors"]}
    assert {"PROPOSED_ADAPTER_NEEDS_PROFILE", "PROPOSED_ADAPTER_NEEDS_EVIDENCE"} <= codes


def test_active_adapter_requires_manifest_and_evidence():
    value = registry()
    core = next(n for n in value["nodes"] if n["node_id"] == "athena-core")
    core["admission_status"] = "ACTIVE_ADAPTER"
    core["manifest_ref"] = None
    core["evidence_refs"] = []
    result = audit.audit_registry(value)
    codes = {e["code"] for e in result["errors"]}
    assert {"ACTIVE_ADAPTER_NEEDS_MANIFEST", "ACTIVE_ADAPTER_NEEDS_EVIDENCE"} <= codes


def test_exactly_one_canonical_abi_is_required():
    value = registry()
    hall = next(n for n in value["nodes"] if n["node_id"] == "guild-hall")
    hall["admission_status"] = "HOLD"
    result = audit.audit_registry(value)
    assert any(e["code"] == "CANONICAL_ABI_CARDINALITY" for e in result["errors"])
