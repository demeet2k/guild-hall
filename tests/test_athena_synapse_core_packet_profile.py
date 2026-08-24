from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("synapse", ROOT / "tools" / "athena_synapse_conformance.py")
synapse = importlib.util.module_from_spec(spec)
assert spec.loader
spec.loader.exec_module(synapse)

VECTOR = ROOT / "fixtures" / "athena_core_synapse_packet_envelope_v1.json"


def vector():
    return json.loads(VECTOR.read_text(encoding="utf-8"))


def test_core_packet_envelope_conforms_to_canonical_abi():
    row = vector()
    envelope = row["envelope"]
    assert synapse.validate_envelope(envelope) == []
    assert envelope["event_id"] == row["expected"]["event_id"]
    assert synapse.digest(envelope) == row["expected"]["envelope_digest"]
    assert envelope["payload"]["body_digest"] == row["expected"]["body_digest"]
    assert envelope["frontier"]["native_digest"] == row["expected"]["packet_digest"]


def test_core_packet_projection_is_lossless_with_explicit_reconstruction_token():
    envelope = vector()["envelope"]
    projection = envelope["projection"]
    assert projection["profile"] == "FEDERATION_SYNAPSE_PACKET_V1"
    assert projection["loss_class"] == "LOSSLESS"
    assert projection["lost"] == []
    assert projection["return_token"] == envelope["frontier"]["native_ref"]
    assert projection["return_token"].endswith(envelope["frontier"]["native_digest"])


def test_core_packet_appears_as_independent_vector_frontier_origin_not_global_clock():
    row = vector()
    envelope = row["envelope"]
    frontier = synapse.frontier([envelope])
    origin = frontier["origins"][row["expected"]["frontier_node_id"]]
    assert origin["repository"] == row["expected"]["frontier_repository"]
    assert origin["source_revisions"] == [row["expected"]["source_revision"]]
    assert origin["event_ids"] == [row["expected"]["event_id"]]
    assert origin["max_origin_sequence"] is None
    assert "global_sequence" not in frontier


def test_core_parent_events_remain_external_causal_refs_when_not_in_view():
    row = vector()
    envelope = row["envelope"]
    order = synapse.causal_order([envelope])
    assert order["ok"]
    assert order["ordered_event_ids"] == [row["expected"]["event_id"]]
    assert sorted(order["external_refs"][row["expected"]["event_id"]]) == sorted(row["expected"]["external_causal_refs"])
    assert order["cycle_event_ids"] == []


def test_exact_replay_is_duplicate_candidate_not_collision():
    envelope = vector()["envelope"]
    report = synapse.gc_report([envelope, copy.deepcopy(envelope)])
    assert report["status"] == "OK"
    assert report["collision_holds"] == []
    assert report["exact_duplicate_candidates"] == [envelope["event_id"]]


def test_reobservation_same_bridge_id_with_changed_body_is_collision_hold():
    envelope = vector()["envelope"]
    reobserved = copy.deepcopy(envelope)
    reobserved["clock"]["bridge_observed_at"] = "2099-01-01T00:00:00Z"
    assert synapse.validate_envelope(reobserved) == []
    assert reobserved["event_id"] == envelope["event_id"]
    assert synapse.digest(reobserved) != synapse.digest(envelope)
    report = synapse.gc_report([envelope, reobserved])
    assert report["status"] == "HOLD"
    assert report["collision_holds"] == [{
        "dedupe_key": envelope["event_id"],
        "event_ids": [envelope["event_id"], envelope["event_id"]],
        "reason": "SAME_BRIDGE_ID_DIFFERENT_BODY",
    }]


def test_core_payload_tamper_is_rejected_by_shared_body_digest_firewall():
    envelope = copy.deepcopy(vector()["envelope"])
    envelope["payload"]["body"]["packet"]["oid"] = "OID-forged"
    errors = synapse.validate_envelope(envelope)
    assert any("body_digest" in error for error in errors)
