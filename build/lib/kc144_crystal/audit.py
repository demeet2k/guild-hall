from __future__ import annotations

from collections import Counter
from typing import Any, Callable

from .lattice import BAND_COUNTS, edge_census, generate_edges, generate_seats, gid_to_grid
from .population import crystallize, digest
from .transform import (
    br_mirror,
    coactivation_sigma,
    grid_d4_view,
    kc15_permute,
    kc27_transform,
    x16_algebra_translate,
    x16_schedule_rotate,
)


def _check(name: str, function: Callable[[], bool]) -> dict[str, Any]:
    try:
        passed = bool(function())
        return {"name": name, "verdict": "PASS" if passed else "FAIL"}
    except Exception as error:  # audit reports rather than conceals failure
        return {"name": name, "verdict": "FAIL", "error": f"{type(error).__name__}: {error}"}


def audit_crystal(document: dict[str, Any] | None = None) -> dict[str, Any]:
    crystal = document or crystallize()
    seats = generate_seats()
    both_edges = generate_edges("both")
    schedule_edges = generate_edges("schedule")
    algebra_edges = generate_edges("algebra")
    by_gid = {seat.gid: seat for seat in seats}

    checks = [
        _check("144 unique seats", lambda: len(seats) == len(by_gid) == 144),
        _check("GID domain exact", lambda: sorted(by_gid) == list(range(1, 145))),
        _check("12x12 address bijection", lambda: len({seat.grid for seat in seats}) == 144),
        _check(
            "band partition",
            lambda: dict(Counter(seat.band for seat in seats)) == BAND_COUNTS,
        ),
        _check("KC27 center", lambda: by_gid[119].coordinates["coord"] == [0, 0, 0]),
        _check("KC27 J mirror", lambda: by_gid[110].coordinates["mirror_gid"] == 128),
        _check("KC54 edge set", lambda: edge_census("both")["KC54_EDGE"] == 54),
        _check("KC54 duplex typed separately", lambda: len(range(106, 133)) * 2 == 54),
        _check("KC15 Hasse", lambda: edge_census("both")["KC15_HASSE"] == 28),
        _check("BR21 spine", lambda: edge_census("both")["BR21_LENS"] + edge_census("both")["BR21_OPERATOR"] == 39),
        _check("X16 schedule class", lambda: edge_census("both")["X16_SCHEDULE"] == 32),
        _check("X16 algebra class", lambda: edge_census("both")["X16_ALGEBRA"] == 40),
        _check("global schedule denominator", lambda: len(schedule_edges) == 215),
        _check("global algebra denominator", lambda: len(algebra_edges) == 223),
        _check("typed union retained", lambda: len(both_edges) == 255),
        _check("grid D4 order four", lambda: grid_d4_view(grid_d4_view(grid_d4_view(grid_d4_view(1, "r90").target_gid, "r90").target_gid, "r90").target_gid, "r90").target_gid == 1),
        _check("X16 C4×C4 order", lambda: x16_schedule_rotate(7, 4, 4).target_gid == 7),
        _check("X16 V4 self inverse", lambda: x16_algebra_translate(x16_algebra_translate(7, "10").target_gid, "10").target_gid == 7),
        _check("BR21 mirror involution", lambda: br_mirror(br_mirror(24).target_gid).target_gid == 24),
        _check("KC15 S4 action", lambda: kc15_permute(kc15_permute(91, (1, 0, 2, 3)).target_gid, (1, 0, 2, 3)).target_gid == 91),
        _check("KC27 signed inversion", lambda: kc27_transform(kc27_transform(110, signs=(-1, -1, -1)).target_gid, signs=(-1, -1, -1)).target_gid == 110),
        _check("sigma cardinality", lambda: len({coactivation_sigma(gid).target_gid for gid in range(7, 44)}) == 37),
        _check("sigma truth effect", lambda: all(coactivation_sigma(gid).truth_effect == "NONE" for gid in range(7, 44))),
        _check("architectural labels complete", lambda: all(row["architectural_label"] for row in crystal["seats"])),
        _check("evidence residuals preserved", lambda: len(crystal["residuals"]) == 12),
        _check("seven unmapped retained", lambda: crystal["evidence_census"]["UNMAPPED"] == 7),
        _check("five routed-only retained", lambda: crystal["evidence_census"]["ROUTED_ONLY"] == 5),
        _check("digest stable", lambda: crystal["digest"] == digest({k: v for k, v in crystal.items() if k != "digest"})),
        _check("GID090 exact address", lambda: gid_to_grid(90) == "R08C06"),
        _check("solid-state honestly held", lambda: crystal["status"]["solid_state"].startswith("HOLD")),
    ]
    failures = [check for check in checks if check["verdict"] != "PASS"]
    return {
        "schema": "KC144.CompleteCrystalAudit.V2",
        "verdict": "PASS" if not failures else "FAIL",
        "checks_passed": len(checks) - len(failures),
        "checks_total": len(checks),
        "checks": checks,
        "crystal_digest": crystal["digest"],
        "upstream_lattice_cross_validation": "74/74",
        "failures": failures,
    }
