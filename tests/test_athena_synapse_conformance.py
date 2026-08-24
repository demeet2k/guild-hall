import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("synapse", ROOT / "tools" / "athena_synapse_conformance.py")
synapse = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(synapse)


def envelope(native_event_id="pkt-1", **overrides):
    origin = {
        "node_id": "athena-mcp",
        "repository": "demeet2k/athena-mcp-server",
        "native_system": "liminal-beacon-v1",
        "native_event_id": native_event_id,
        "source_revision": "abc123",
        "native_ref": f"athena://liminal/packet/{native_event_id}",
    }
    row = {
        "schema": synapse.SCHEMA,
        "event_id": synapse.bridge_event_id(origin),
        "event_type": "OBSERVATION",
        "subject": "work:bridge",
        "origin": origin,
        "semantics": {"epistemic_class": "OBS", "authority_class": "COORDINATION", "truth_ceiling": "ROUTING_STATE", "native_kind": "DELTA"},
        "routing": {"return_routes": [origin["native_ref"]], "recipients": [], "route_keys": ["work:bridge"], "visibility": "COLONY"},
        "causality": {"parent_ids": [], "reply_to": None, "correction_of": None, "retraction_of": None, "supersedes": []},
        "clock": {"wall_time": "2026-08-24T08:00:00Z", "bridge_observed_at": "2026-08-24T08:00:01Z", "origin_sequence": 4},
        "payload": {"summary": "bridge delta", "payload_ref": origin["native_ref"], "body": {"x": 1}, "body_digest": synapse.digest({"x": 1}), "evidence": [], "residuals": []},
        "receipt": None,
    }
    row.update(overrides)
    return row


def test_valid_envelope_and_stable_id_ignores_wall_time():
    one = envelope()
    two = copy.deepcopy(one)
    two["clock"]["wall_time"] = "2030-01-01T00:00:00Z"
    assert synapse.validate_envelope(one) == []
    assert one["event_id"] == two["event_id"]


def test_bad_bridge_id_and_body_digest_are_rejected():
    row = envelope()
    row["event_id"] = "SYN-wrong"
    row["payload"]["body_digest"] = "sha256:wrong"
    errors = synapse.validate_envelope(row)
    assert any("deterministic bridge identity" in e for e in errors)
    assert any("body_digest" in e for e in errors)


def test_contradiction_requires_target():
    row = envelope(event_type="CONTRADICTION")
    assert "CONTRADICTION requires correction_of or a causal parent" in synapse.validate_envelope(row)


def test_receipt_preserves_stage_distinction():
    row = envelope(event_type="RECEIPT", receipt={"stage": "PRESENTED", "recipient": "athena-core"})
    assert synapse.validate_envelope(row) == []
    row["receipt"]["stage"] = "MAGICALLY_UNDERSTOOD"
    assert "receipt.stage is invalid" in synapse.validate_envelope(row)


def test_vector_frontier_does_not_make_global_clock():
    rows = [envelope("a"), envelope("b")]
    rows[1]["origin"] = dict(rows[1]["origin"], node_id="guild-hall", repository="demeet2k/guild-hall", native_system="conformance", source_revision="def456")
    rows[1]["event_id"] = synapse.bridge_event_id(rows[1]["origin"])
    rows[1]["clock"]["origin_sequence"] = 999
    f = synapse.frontier(rows)
    assert set(f["origins"]) == {"athena-mcp", "guild-hall"}
    assert "global_sequence" not in f


def test_causal_sort_uses_edges_not_wall_time():
    parent = envelope("parent")
    child = envelope("child")
    child["causality"]["parent_ids"] = [parent["event_id"]]
    child["clock"]["wall_time"] = "2000-01-01T00:00:00Z"
    order = synapse.causal_order([child, parent])
    assert order["ok"]
    assert order["ordered_event_ids"] == [parent["event_id"], child["event_id"]]


def test_gc_duplicate_vs_collision():
    one = envelope("dup")
    duplicate = copy.deepcopy(one)
    report = synapse.gc_report([one, duplicate])
    assert report["status"] == "OK"
    assert report["exact_duplicate_candidates"] == [one["event_id"]]
    collision = copy.deepcopy(one)
    collision["payload"]["summary"] = "mutated under same native identity"
    report = synapse.gc_report([one, collision])
    assert report["status"] == "HOLD"
    assert report["collision_holds"][0]["reason"] == "SAME_BRIDGE_ID_DIFFERENT_BODY"


def test_fixture_conforms():
    fixture = json.loads((ROOT / "fixtures" / "athena_synapse_vectors_v1.json").read_text())
    assert synapse.conformance_report(fixture["envelopes"])["ok"]
