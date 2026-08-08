from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence, Tuple

from tools.observable_liminal_harness import LiminalCoordinate, TransitRecord, validate_route

SCHEMA = "ObservableLiminalEdgeReceipt.V1"


class EdgeReceiptError(ValueError):
    pass


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EdgeReceiptError(f"{field}: required non-empty string")
    return value


@dataclass(frozen=True)
class EdgeProvenance:
    surface: str
    transport: str
    native_locator: str
    native_version: str
    return_locator: str

    def validate(self) -> None:
        for field in (
            "surface", "transport", "native_locator", "native_version", "return_locator"
        ):
            _nonempty(getattr(self, field), f"provenance.{field}")

    def as_mapping(self) -> dict[str, str]:
        self.validate()
        return {
            "surface": self.surface,
            "transport": self.transport,
            "native_locator": self.native_locator,
            "native_version": self.native_version,
            "return_locator": self.return_locator,
        }


@dataclass(frozen=True)
class ReplayableEdge:
    transit: TransitRecord
    provenance: EdgeProvenance

    def validate(self) -> None:
        self.transit.validate()
        self.provenance.validate()

    def as_mapping(self) -> dict[str, Any]:
        self.validate()
        return {
            "before": self.transit.before.as_mapping(),
            "after": self.transit.after.as_mapping(),
            "action": self.transit.action,
            "evidence": self.transit.evidence,
            "witness": self.transit.witness,
            "provenance": self.provenance.as_mapping(),
        }


def _canonical_bytes(value: Mapping[str, Any]) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def _payload_digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def make_route_receipt(
    edges: Sequence[ReplayableEdge],
    *,
    registry_id: str,
    registry_version: str,
    carrier_id: str,
) -> dict[str, Any]:
    """Create a content-authenticated, cold-replayable observed-route receipt."""

    registry_id = _nonempty(registry_id, "registry_id")
    registry_version = _nonempty(registry_version, "registry_version")
    carrier_id = _nonempty(carrier_id, "carrier_id")
    if not edges:
        raise EdgeReceiptError("edges: at least one observed edge is required")

    for edge in edges:
        edge.validate()
    validate_route([edge.transit for edge in edges])

    payload = {
        "schema": SCHEMA,
        "registry": {"id": registry_id, "version": registry_version},
        "carrier_id": carrier_id,
        "edges": [edge.as_mapping() for edge in edges],
    }
    return {**payload, "payload_sha256": _payload_digest(payload)}


def load_route_receipt(
    value: Mapping[str, Any],
    *,
    expected_registry_id: str | None = None,
    expected_registry_version: str | None = None,
    expected_carrier_id: str | None = None,
) -> Tuple[ReplayableEdge, ...]:
    """Authenticate, bind registry/carrier identity, reconstruct, and validate a route."""

    if value.get("schema") != SCHEMA:
        raise EdgeReceiptError("schema: invalid")
    registry = value.get("registry")
    if not isinstance(registry, Mapping):
        raise EdgeReceiptError("registry: required object")
    registry_id = _nonempty(registry.get("id"), "registry.id")
    registry_version = _nonempty(registry.get("version"), "registry.version")
    carrier_id = _nonempty(value.get("carrier_id"), "carrier_id")

    if expected_registry_id is not None and registry_id != expected_registry_id:
        raise EdgeReceiptError("registry.id: mismatch")
    if expected_registry_version is not None and registry_version != expected_registry_version:
        raise EdgeReceiptError("registry.version: mismatch")
    if expected_carrier_id is not None and carrier_id != expected_carrier_id:
        raise EdgeReceiptError("carrier_id: mismatch")

    expected_digest = _nonempty(value.get("payload_sha256"), "payload_sha256")
    payload = {
        "schema": value["schema"],
        "registry": dict(registry),
        "carrier_id": carrier_id,
        "edges": value.get("edges"),
    }
    observed_digest = _payload_digest(payload)
    if observed_digest != expected_digest:
        raise EdgeReceiptError("payload_sha256: mismatch")

    raw_edges = value.get("edges")
    if not isinstance(raw_edges, list) or not raw_edges:
        raise EdgeReceiptError("edges: required non-empty array")

    rebuilt = []
    for i, raw in enumerate(raw_edges):
        if not isinstance(raw, Mapping):
            raise EdgeReceiptError(f"edges[{i}]: required object")
        provenance = raw.get("provenance")
        if not isinstance(provenance, Mapping):
            raise EdgeReceiptError(f"edges[{i}].provenance: required object")
        edge = ReplayableEdge(
            transit=TransitRecord(
                LiminalCoordinate.from_mapping(raw["before"]),
                LiminalCoordinate.from_mapping(raw["after"]),
                _nonempty(raw.get("action"), f"edges[{i}].action"),
                _nonempty(raw.get("evidence"), f"edges[{i}].evidence"),
                _nonempty(raw.get("witness"), f"edges[{i}].witness"),
            ),
            provenance=EdgeProvenance(
                surface=_nonempty(provenance.get("surface"), f"edges[{i}].provenance.surface"),
                transport=_nonempty(provenance.get("transport"), f"edges[{i}].provenance.transport"),
                native_locator=_nonempty(provenance.get("native_locator"), f"edges[{i}].provenance.native_locator"),
                native_version=_nonempty(provenance.get("native_version"), f"edges[{i}].provenance.native_version"),
                return_locator=_nonempty(provenance.get("return_locator"), f"edges[{i}].provenance.return_locator"),
            ),
        )
        edge.validate()
        rebuilt.append(edge)

    validate_route([edge.transit for edge in rebuilt])
    return tuple(rebuilt)
