from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .lattice import BAND_COUNTS, edge_census, generate_edges, generate_seats
from .transform import transformation_catalog


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest(value: Any) -> str:
    return "sha256:" + hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def default_atlas_path() -> Path:
    return Path(__file__).with_name("data") / "atlas_frozen.json"


def _load_atlas(path: Path) -> dict[int, dict[str, Any]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    rows = document["seats"] if isinstance(document, dict) else document
    by_gid = {int(row["gid"]): row for row in rows}
    if sorted(by_gid) != list(range(1, 145)):
        raise ValueError("frozen atlas is not a complete GID001..GID144 bijection")
    return by_gid


def crystallize(atlas_path: str | Path | None = None) -> dict[str, Any]:
    """Compile the whole crystal in one deterministic projection.

    Generation supplies structure. The frozen atlas supplies architectural
    labels. Evidence status remains controlled by the later lattice audit.
    """
    seats = generate_seats()
    atlas = _load_atlas(Path(atlas_path) if atlas_path else default_atlas_path())
    rows: list[dict[str, Any]] = []
    for seat in seats:
        architectural = atlas[seat.gid]
        basis = {
            "DOCUMENTED": "SOURCE_DOCUMENTED",
            "DERIVED": "GENERATOR_FORCED",
            "ROUTED_ONLY": "ROUTE_ENDPOINT_ONLY",
            "UNMAPPED": "ADDRESS_ONLY",
        }[seat.evidence_status]
        rows.append(
            {
                **seat.to_dict(),
                "architectural_label": architectural["title"],
                "architectural_status": architectural["status"],
                "aliases": architectural.get("aliases", []),
                "population_basis": basis,
                "promotion_effect": "NONE",
            }
        )

    all_edges = generate_edges("both")
    edge_rows = [edge.to_dict() for edge in all_edges]
    evidence_census = Counter(row["evidence_status"] for row in rows)
    residuals = [
        {
            "gid": row["gid"],
            "station": row["station"],
            "architectural_label": row["architectural_label"],
            "evidence_status": row["evidence_status"],
            "required_resolution": (
                "bind an exact source excerpt and witness"
                if row["evidence_status"] == "UNMAPPED"
                else "bind a role-defining source excerpt"
            ),
        }
        for row in rows
        if row["evidence_status"] in {"ROUTED_ONLY", "UNMAPPED"}
    ]

    document: dict[str, Any] = {
        "schema": "KC144.CompleteCrystal.V2",
        "namespace": "KC144.V2",
        "framework_revision": "KC144.COMPLETE.CRYSTAL.2026-07-26",
        "method": "DISJOINT_ORBIT_GENERATION_PLUS_EVIDENCE_OVERLAY",
        "equation": (
            "H6 ⊔ (K4×L4) ⊔ (O7×L3) ⊔ F37 ⊔ C10 ⊔ "
            "(2^K4\\{∅}) ⊔ T3^3 ⊔ S12"
        ),
        "status": {
            "framework": "EXECUTABLE_CRYSTAL_COMPLETE",
            "structural_population": "144/144",
            "address_bijection": "PASS",
            "source_content": "PARTIAL_WITH_TYPED_RESIDUALS",
            "external_federation": "REFERENCE_RECEIPTS_ONLY_NOT_DEPLOYED",
            "solid_state": "HOLD_PENDING_LIVE_COVERAGE_AND_INDEPENDENT_COLD_REPLAY",
        },
        "laws": [
            "generation does not promote truth",
            "rotation is a typed view or automorphism, never silent identity collapse",
            "architectural label and evidence status are independent fields",
            "KC54 edge-set and KC54 duplex are distinct typed objects",
            "X16 schedule and algebra edge classes share vertices but are not merged",
            "QSHRINK follows joint return plus IC10 promotion; it never precedes them",
            "unmapped source content remains a residual instead of being invented",
        ],
        "band_counts": BAND_COUNTS,
        "evidence_census": dict(evidence_census),
        "edge_census": edge_census("both"),
        "edge_denominators": {
            "schedule_reading": 215,
            "algebra_reading": 223,
            "both_typed_classes_stored": len(all_edges),
        },
        "transformations": transformation_catalog(),
        "seats": rows,
        "edges": edge_rows,
        "residuals": residuals,
    }
    document["digest"] = digest(document)
    return document


def write_crystal(output: str | Path, atlas_path: str | Path | None = None) -> dict[str, Any]:
    document = crystallize(atlas_path)
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return document
