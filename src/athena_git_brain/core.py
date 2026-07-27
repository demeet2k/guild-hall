from __future__ import annotations

from collections import deque
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Iterable


ACTIVE = "active"
RETURN_CLASSES = {
    "exact",
    "equivalent",
    "partial",
    "compensated",
    "multivalued",
    "provenance_only",
    "impossible",
}
PROMOTION_GATES = (
    "I01_identity",
    "I02_type_normalization",
    "I03_source_provenance",
    "I04_carrier_preconditions",
    "I05_invariant_preservation",
    "I06_defect_boundary",
    "I07_return",
    "I08_replay",
    "I09_authority_policy",
    "I10_migration_successor",
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise ValueError(f"{path}:{line_no}: {exc}") from exc
    return rows


def load_registry(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    federation = load_json(root / "registry/federation.json")
    edges = load_jsonl(root / "registry/edges.jsonl")
    return federation, edges


def _required(value: dict[str, Any], names: Iterable[str], prefix: str) -> list[str]:
    return [f"{prefix}: missing {name}" for name in names if name not in value]


def validate_registry(root: Path) -> dict[str, Any]:
    federation, edges = load_registry(root)
    errors: list[str] = []
    warnings: list[str] = []

    resources = federation.get("resources", [])
    resource_keys: set[tuple[str, str]] = set()
    for index, resource in enumerate(resources):
        prefix = f"resource[{index}]"
        errors.extend(_required(resource, ("rid", "vid", "kind", "kernel"), prefix))
        key = (resource.get("rid"), resource.get("vid"))
        if key in resource_keys:
            errors.append(f"{prefix}: duplicate resource version {key}")
        resource_keys.add(key)
        if not str(resource.get("rid", "")).startswith("athena."):
            errors.append(f"{prefix}: rid must start with athena.")

    edge_ids: set[str] = set()
    edge_by_id: dict[str, dict[str, Any]] = {}
    required_edge = (
        "eid",
        "source",
        "target",
        "type",
        "operator",
        "domain",
        "codomain",
        "preconditions",
        "carrier",
        "preserved",
        "changed",
        "lost",
        "defects",
        "witnesses",
        "authority",
        "return",
        "status",
        "version",
    )
    for index, edge in enumerate(edges):
        prefix = f"edge[{index}]"
        errors.extend(_required(edge, required_edge, prefix))
        eid = edge.get("eid")
        if eid in edge_ids:
            errors.append(f"{prefix}: duplicate edge id {eid}")
        edge_ids.add(eid)
        edge_by_id[eid] = edge

        source = edge.get("source", {})
        target = edge.get("target", {})
        for label, endpoint in (("source", source), ("target", target)):
            key = (endpoint.get("rid"), endpoint.get("vid"))
            if key not in resource_keys:
                errors.append(f"{prefix}: unknown {label} resource version {key}")

        if edge.get("status") == ACTIVE:
            if not edge.get("carrier"):
                errors.append(f"{prefix}: active edge has no carrier")
            if not edge.get("witnesses"):
                errors.append(f"{prefix}: active edge has no witnesses")
            return_value = edge.get("return", {})
            if return_value.get("class") not in RETURN_CLASSES:
                errors.append(f"{prefix}: invalid return class")
            if return_value.get("class") != "impossible" and not return_value.get(
                "edge_id"
            ):
                errors.append(f"{prefix}: returnable edge has no return edge id")
        elif edge.get("status") == "discovery":
            warnings.append(f"{prefix}: discovery edge is non-traversable")

    for eid, edge in edge_by_id.items():
        return_value = edge.get("return", {})
        reverse_id = return_value.get("edge_id")
        if not reverse_id:
            continue
        reverse = edge_by_id.get(reverse_id)
        if reverse is None:
            errors.append(f"{eid}: unknown return edge {reverse_id}")
            continue
        if reverse.get("source") != edge.get("target") or reverse.get(
            "target"
        ) != edge.get("source"):
            errors.append(f"{eid}: return edge {reverse_id} does not reverse endpoints")

    return {
        "status": "PASS" if not errors else "FAIL",
        "federation": federation.get("federation_id"),
        "release": federation.get("release"),
        "resource_versions": len(resource_keys),
        "edges": len(edges),
        "errors": errors,
        "warnings": warnings,
        "graph_digest": f"sha256:{digest({'resources': sorted(resource_keys), 'edges': edges})}",
    }


def compile_route(
    root: Path,
    source_rid: str,
    target_rid: str,
    *,
    query_id: str = "query.reference",
    require_return: bool = True,
) -> dict[str, Any]:
    federation, edges = load_registry(root)
    resource_rids = {item["rid"] for item in federation.get("resources", [])}
    if source_rid not in resource_rids or target_rid not in resource_rids:
        return {
            "verdict": "INVALID_ADDRESS",
            "source": source_rid,
            "target": target_rid,
            "defects": ["source or target RID is not present in frozen federation"],
        }

    edge_by_id = {edge["eid"]: edge for edge in edges}
    adjacency: dict[str, list[dict[str, Any]]] = {}
    for edge in edges:
        if edge.get("status") != ACTIVE:
            continue
        if not edge.get("carrier") or not edge.get("witnesses"):
            continue
        return_value = edge.get("return", {})
        if require_return:
            if return_value.get("class") == "impossible":
                continue
            if return_value.get("edge_id") not in edge_by_id:
                continue
        adjacency.setdefault(edge["source"]["rid"], []).append(edge)

    queue = deque([(source_rid, [])])
    seen = {source_rid}
    path: list[dict[str, Any]] | None = None
    while queue:
        node, candidate = queue.popleft()
        if node == target_rid:
            path = candidate
            break
        for edge in sorted(adjacency.get(node, []), key=lambda item: item["eid"]):
            neighbour = edge["target"]["rid"]
            if neighbour in seen:
                continue
            seen.add(neighbour)
            queue.append((neighbour, [*candidate, edge]))

    if path is None:
        return {
            "verdict": "UNMAPPED",
            "source": source_rid,
            "target": target_rid,
            "defects": ["no active type/witness/return-admissible path"],
        }

    return_plan = [edge["return"]["edge_id"] for edge in reversed(path)]
    preserved = sorted({item for edge in path for item in edge["preserved"]})
    lost = sorted({item for edge in path for item in edge["lost"]})
    defects = sorted({item for edge in path for item in edge["defects"]})
    witnesses = sorted({item for edge in path for item in edge["witnesses"]})
    body = {
        "query_id": query_id,
        "frozen_federation": federation["release"],
        "source": source_rid,
        "target": target_rid,
        "hops": [edge["eid"] for edge in path],
        "preserved": preserved,
        "lost": lost,
        "defects": defects,
        "witnesses": witnesses,
        "return_plan": return_plan,
        "branches": [],
        "replay": {
            "command": f"python -m athena_git_brain route {source_rid} {target_rid}",
            "graph_digest": validate_registry(root)["graph_digest"],
        },
        "verdict": "FOUND" if not lost else "PARTIAL",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"route_id": f"route:sha256:{digest(body)}", **body}


def promotion_ready(gates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    missing = [gate for gate in PROMOTION_GATES if gate not in gates]
    failed = [
        gate
        for gate in PROMOTION_GATES
        if gates.get(gate, {}).get("verdict") == "FAIL"
    ]
    held = [
        gate
        for gate in PROMOTION_GATES
        if gates.get(gate, {}).get("verdict") == "HOLD"
    ]
    unwitnessed = [
        gate
        for gate in PROMOTION_GATES
        if gates.get(gate, {}).get("verdict") == "PASS"
        and not gates.get(gate, {}).get("witnesses")
    ]
    ready = not missing and not failed and not held and not unwitnessed
    return {
        "ready": ready,
        "verdict": "PROMOTE" if ready else "HOLD",
        "missing": missing,
        "failed": failed,
        "held": held,
        "unwitnessed": unwitnessed,
        "law": "all ten gates must PASS with witnesses",
    }

