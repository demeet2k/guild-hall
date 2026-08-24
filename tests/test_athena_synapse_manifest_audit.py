import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("manifest_audit", ROOT / "tools" / "athena_synapse_manifest_audit.py")
audit = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(audit)


def manifest(standing="DECLARED_NO_ADAPTER"):
    return {
        "schema": "ATHENA.SYNAPSE.NODE.MANIFEST.V1",
        "node_id": "water",
        "repository": "demeet2k/athena-cloud-water",
        "default_branch": "master",
        "role": "observation",
        "standing": standing,
        "observed_revision": "a7fcf26683c08f090cf94b14a8aa861db599c679",
        "native_surfaces": [
            {
                "surface_id": "water-resource",
                "kind": "MCP_RESOURCE",
                "reference": "athena://cloud-water",
                "mutation_class": "READ_ONLY",
                "evidence_ref": "blob:MCP/element_servers/cloud_server.py@f0b6bc1f9cfce2a9797ce07c18bb79d0afa386ca",
                "notes": "observed decorator and resource body"
            },
            {
                "surface_id": "water-tool-module",
                "kind": "MCP_TOOL_MODULE",
                "reference": "MCP/element_servers/cloud_server.py",
                "mutation_class": "MIXED",
                "evidence_ref": "blob:MCP/element_servers/cloud_server.py@f0b6bc1f9cfce2a9797ce07c18bb79d0afa386ca",
                "notes": "tool module inspection only"
            }
        ],
        "synapse_profiles": [],
        "import_profiles": [],
        "return_routes": ["athena://cloud-water"],
        "authority_class": "SELF_DECLARED_NATIVE_SURFACE",
        "truth_ceiling": "REPOSITORY_CODE_SURFACE_ONLY",
        "evidence_refs": ["blob:MCP/element_servers/cloud_server.py@f0b6bc1f9cfce2a9797ce07c18bb79d0afa386ca"],
        "residuals": ["RUNTIME_START_UNOBSERVED", "SYNAPSE_ADAPTER_NOT_IMPLEMENTED"]
    }


def test_declared_no_adapter_manifest_passes_without_profile_inflation():
    result = audit.audit_manifest(manifest())
    assert result["ok"]
    assert result["surface_count"] == 2


def test_no_adapter_cannot_claim_export_or_import_profile():
    value = manifest()
    value["synapse_profiles"] = ["WATER_V1"]
    assert any(e["code"] == "NO_ADAPTER_CANNOT_CLAIM_PROFILE" for e in audit.audit_manifest(value)["errors"])
    value = manifest()
    value["import_profiles"] = ["FEDERATION_EVENT_V1"]
    assert any(e["code"] == "NO_ADAPTER_CANNOT_CLAIM_PROFILE" for e in audit.audit_manifest(value)["errors"])


def test_observed_revision_is_required_and_hash_shaped():
    value = manifest()
    value["observed_revision"] = "master"
    assert any(e["code"] == "BAD_OBSERVED_REVISION" for e in audit.audit_manifest(value)["errors"])


def test_surface_evidence_must_be_manifest_evidence():
    value = manifest()
    value["native_surfaces"][0]["evidence_ref"] = "blob:unbound"
    assert any(e["code"] == "SURFACE_EVIDENCE_NOT_IN_MANIFEST_EVIDENCE" for e in audit.audit_manifest(value)["errors"])


def test_surface_ids_are_unique():
    value = manifest()
    value["native_surfaces"][1]["surface_id"] = value["native_surfaces"][0]["surface_id"]
    assert any(e["code"] == "DUPLICATE_SURFACE_ID" for e in audit.audit_manifest(value)["errors"])


def test_adapter_standing_requires_profile():
    value = manifest("PROPOSED_ADAPTER")
    assert any(e["code"] == "ADAPTER_STANDING_REQUIRES_PROFILE" for e in audit.audit_manifest(value)["errors"])


def test_active_adapter_requires_execution_evidence():
    value = manifest("ACTIVE_ADAPTER")
    value["synapse_profiles"] = ["WATER_V1"]
    assert any(e["code"] == "ACTIVE_ADAPTER_REQUIRES_EXECUTION_EVIDENCE" for e in audit.audit_manifest(value)["errors"])
    value["evidence_refs"].append("test:water-adapter-suite")
    assert audit.audit_manifest(value)["ok"]


def test_runtime_and_adapter_residuals_are_visible_warnings_when_missing():
    value = manifest()
    value["residuals"] = []
    result = audit.audit_manifest(value)
    codes = {w["code"] for w in result["warnings"]}
    assert "NO_ADAPTER_WITHOUT_EXPLICIT_ADAPTER_RESIDUAL" in codes
    assert "RUNTIME_STANDING_NOT_EXPLICIT" in codes
