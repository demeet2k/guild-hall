from __future__ import annotations

"""ATHENA Synapse ABI V1 conformance, frontier, and conservative GC helpers.

Dependency-free by design: every ATHENA repo can run the same checks without
importing another organ's runtime. Routing never upgrades into truth, and causal
order is never inferred from wall-clock timestamps.
"""

import argparse
import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any, Iterable, Mapping

SCHEMA = "ATHENA.SYNAPSE.ENVELOPE.V1"
EVENT_TYPES = {
    "OBSERVATION", "PROPOSAL", "CLAIM", "EFFECT", "RECEIPT", "WITNESS",
    "CONTRADICTION", "HOLD", "RETURN", "SUPERSESSION",
}
RECEIPT_STAGES = {
    "PRESENTED", "CONSUMED", "INCORPORATED", "DECISION_CHANGED", "PROPAGATED",
}
EPISTEMIC_CLASSES = {"OBS", "RET", "DER", "HYP", "SIM", "UNK", "CON"}


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def bridge_event_id(origin: Mapping[str, Any], projection: str = "athena-synapse-v1") -> str:
    """Stable bridge identity; wall time is deliberately excluded."""
    material = {
        "projection": projection,
        "node_id": origin.get("node_id"),
        "repository": origin.get("repository"),
        "native_system": origin.get("native_system"),
        "native_event_id": origin.get("native_event_id"),
        "source_revision": origin.get("source_revision"),
    }
    return "SYN-" + hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()[:32]


def dedupe_key(envelope: Mapping[str, Any]) -> str:
    return bridge_event_id(envelope.get("origin") or {})


def _is_nonempty_str(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _string_list(value: Any) -> bool:
    return isinstance(value, list) and all(_is_nonempty_str(item) for item in value) and len(value) == len(set(value))


def validate_envelope(envelope: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    if envelope.get("schema") != SCHEMA:
        errors.append("schema must be ATHENA.SYNAPSE.ENVELOPE.V1")
    event_id = envelope.get("event_id")
    if not _is_nonempty_str(event_id):
        errors.append("event_id is required")
    event_type = envelope.get("event_type")
    if event_type not in EVENT_TYPES:
        errors.append("unsupported event_type")
    if not _is_nonempty_str(envelope.get("subject")):
        errors.append("subject is required")

    origin = envelope.get("origin")
    if not isinstance(origin, Mapping):
        errors.append("origin object is required")
        origin = {}
    for field in ("node_id", "repository", "native_system", "native_event_id", "source_revision"):
        if not _is_nonempty_str(origin.get(field)):
            errors.append(f"origin.{field} is required")
    required_origin = ("node_id", "repository", "native_system", "native_event_id", "source_revision")
    if _is_nonempty_str(event_id) and all(_is_nonempty_str(origin.get(k)) for k in required_origin):
        if event_id != bridge_event_id(origin):
            errors.append("event_id does not match deterministic bridge identity")

    semantics = envelope.get("semantics")
    if not isinstance(semantics, Mapping):
        errors.append("semantics object is required")
        semantics = {}
    if semantics.get("epistemic_class") not in EPISTEMIC_CLASSES:
        errors.append("semantics.epistemic_class must be OBS|RET|DER|HYP|SIM|UNK|CON")
    for field in ("authority_class", "truth_ceiling"):
        if not _is_nonempty_str(semantics.get(field)):
            errors.append(f"semantics.{field} is required")

    routing = envelope.get("routing")
    if not isinstance(routing, Mapping):
        errors.append("routing object is required")
        routing = {}
    routes = routing.get("return_routes")
    if not _string_list(routes) or not routes:
        errors.append("routing.return_routes requires at least one unique non-empty route")
    for field in ("recipients", "route_keys"):
        if field in routing and not _string_list(routing.get(field)):
            errors.append(f"routing.{field} must be a unique string array")

    causality = envelope.get("causality")
    if not isinstance(causality, Mapping):
        errors.append("causality object is required")
        causality = {}
    for field in ("parent_ids", "supersedes"):
        if not _string_list(causality.get(field, [])):
            errors.append(f"causality.{field} must be a unique string array")
    for field in ("reply_to", "correction_of", "retraction_of"):
        value = causality.get(field)
        if value is not None and not _is_nonempty_str(value):
            errors.append(f"causality.{field} must be null or non-empty string")
    if event_type == "CONTRADICTION" and not causality.get("correction_of") and not (causality.get("parent_ids") or []):
        errors.append("CONTRADICTION requires correction_of or a causal parent")
    if event_type == "SUPERSESSION" and not causality.get("retraction_of") and not (causality.get("supersedes") or []):
        errors.append("SUPERSESSION requires retraction_of or supersedes")

    receipt = envelope.get("receipt")
    if event_type == "RECEIPT":
        if not isinstance(receipt, Mapping):
            errors.append("RECEIPT event requires receipt object")
        elif receipt.get("stage") not in RECEIPT_STAGES:
            errors.append("receipt.stage is invalid")
    elif receipt is not None and isinstance(receipt, Mapping) and receipt.get("stage") not in RECEIPT_STAGES:
        errors.append("receipt.stage is invalid")

    clock = envelope.get("clock")
    if not isinstance(clock, Mapping):
        errors.append("clock object is required")
    else:
        if not _is_nonempty_str(clock.get("bridge_observed_at")):
            errors.append("clock.bridge_observed_at is required")
        seq = clock.get("origin_sequence")
        if seq is not None and (not isinstance(seq, int) or isinstance(seq, bool) or seq < 0):
            errors.append("clock.origin_sequence must be null or a non-negative integer")

    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        errors.append("payload object is required")
    else:
        body = payload.get("body")
        body_digest = payload.get("body_digest")
        if body is not None and body_digest != digest(body):
            errors.append("payload.body_digest does not match payload.body")
        elif body is None and body_digest is not None and not _is_nonempty_str(body_digest):
            errors.append("payload.body_digest must be null or non-empty string")
    return errors


def conformance_report(envelopes: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    results = []
    for index, envelope in enumerate(envelopes):
        errors = validate_envelope(envelope)
        results.append({"index": index, "event_id": envelope.get("event_id"), "ok": not errors, "errors": errors})
    return {"schema": SCHEMA, "ok": all(row["ok"] for row in results), "results": results}


def frontier(envelopes: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Vector frontier; independent origins are never collapsed into one clock."""
    per_origin: dict[str, dict[str, Any]] = {}
    for envelope in envelopes:
        if validate_envelope(envelope):
            continue
        origin = envelope["origin"]
        node_id = origin["node_id"]
        row = per_origin.setdefault(node_id, {
            "repository": origin["repository"], "source_revisions": set(),
            "event_ids": [], "max_origin_sequence": None,
        })
        row["source_revisions"].add(origin["source_revision"])
        row["event_ids"].append(envelope["event_id"])
        seq = (envelope.get("clock") or {}).get("origin_sequence")
        if seq is not None:
            row["max_origin_sequence"] = seq if row["max_origin_sequence"] is None else max(row["max_origin_sequence"], seq)
    frozen = {}
    for node_id, row in sorted(per_origin.items()):
        frozen[node_id] = {
            "repository": row["repository"],
            "source_revisions": sorted(row["source_revisions"]),
            "event_ids": sorted(set(row["event_ids"])),
            "max_origin_sequence": row["max_origin_sequence"],
        }
    result = {"schema": "ATHENA.SYNAPSE.FRONTIER.V1", "origins": frozen}
    result["frontier_digest"] = digest(result)
    return result


def causal_order(envelopes: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Topological order over explicit in-set causal edges, never timestamps."""
    rows = {str(e.get("event_id")): e for e in envelopes if _is_nonempty_str(e.get("event_id"))}
    deps: dict[str, set[str]] = {eid: set() for eid in rows}
    reverse: dict[str, set[str]] = defaultdict(set)
    external: dict[str, list[str]] = {}
    for eid, envelope in rows.items():
        causal = envelope.get("causality") or {}
        refs = list(causal.get("parent_ids") or []) + list(causal.get("supersedes") or [])
        refs += [causal.get(k) for k in ("reply_to", "correction_of", "retraction_of") if causal.get(k)]
        for ref in sorted(set(map(str, refs))):
            if ref in rows and ref != eid:
                deps[eid].add(ref)
                reverse[ref].add(eid)
            elif ref != eid:
                external.setdefault(eid, []).append(ref)
    queue = deque(sorted(eid for eid, required in deps.items() if not required))
    ordered: list[str] = []
    while queue:
        eid = queue.popleft()
        ordered.append(eid)
        for nxt in sorted(reverse.get(eid, ())):
            deps[nxt].discard(eid)
            if not deps[nxt]:
                queue.append(nxt)
    cycle = sorted(eid for eid, required in deps.items() if required)
    return {"ordered_event_ids": ordered, "external_refs": external, "cycle_event_ids": cycle, "ok": not cycle}


def gc_report(envelopes: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Conservative GC analysis only; never deletes evidence."""
    rows = list(envelopes)
    by_key: dict[str, list[tuple[str, str]]] = defaultdict(list)
    referenced: set[str] = set()
    explicitly_retired: set[str] = set()
    for envelope in rows:
        eid = str(envelope.get("event_id") or "")
        if not eid:
            continue
        by_key[dedupe_key(envelope)].append((eid, digest(envelope)))
        causal = envelope.get("causality") or {}
        for field in ("parent_ids", "supersedes"):
            referenced.update(map(str, causal.get(field) or []))
        for field in ("reply_to", "correction_of", "retraction_of"):
            if causal.get(field):
                referenced.add(str(causal[field]))
        explicitly_retired.update(map(str, causal.get("supersedes") or []))
        if causal.get("retraction_of"):
            explicitly_retired.add(str(causal["retraction_of"]))

    duplicate_candidates: list[str] = []
    collision_holds = []
    for key, members in sorted(by_key.items()):
        digests = {body for _, body in members}
        if len(members) > 1 and len(digests) == 1:
            duplicate_candidates.extend(eid for eid, _ in members[1:])
        elif len(members) > 1:
            collision_holds.append({"dedupe_key": key, "event_ids": [eid for eid, _ in members], "reason": "SAME_BRIDGE_ID_DIFFERENT_BODY"})
    return {
        "schema": "ATHENA.SYNAPSE.GC.REPORT.V1",
        "deletion_performed": False,
        "exact_duplicate_candidates": sorted(set(duplicate_candidates)),
        "explicitly_retired_candidates": sorted(explicitly_retired),
        "retain_required": sorted(referenced),
        "collision_holds": collision_holds,
        "status": "HOLD" if collision_holds else "OK",
    }


def _load(path: str) -> list[dict[str, Any]]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(value, dict) and isinstance(value.get("envelopes"), list):
        return value["envelopes"]
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    raise ValueError("input must be envelope object, array, or {envelopes:[...]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("validate", "frontier", "causal", "gc"))
    parser.add_argument("path")
    args = parser.parse_args(argv)
    rows = _load(args.path)
    result = (
        conformance_report(rows) if args.command == "validate" else
        frontier(rows) if args.command == "frontier" else
        causal_order(rows) if args.command == "causal" else gc_report(rows)
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("ok", result.get("status") != "HOLD") else 2


if __name__ == "__main__":
    raise SystemExit(main())
