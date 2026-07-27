from __future__ import annotations

from collections import Counter
from itertools import combinations, product

from .model import Edge, Seat

K4 = ("11", "10", "00", "01")
L4 = ("SQ", "FL", "CL", "FR")
L3 = ("PLUS", "HINGE", "STAR")
O7 = ("ADMIT", "EXPAND", "NAVIGATE", "TRANSFORM", "TEST", "COMPRESS", "RETURN")
T3 = (-1, 0, 1)

BAND_COUNTS = {
    "H6": 6,
    "X16": 16,
    "BR21": 21,
    "F37": 37,
    "IC10": 10,
    "KC15": 15,
    "KC27": 27,
    "SSN12": 12,
}

H6_ROLES = (
    "Address–Identity Registry",
    "Domain Projection–Seating and Alias Registry",
    "Typed Route–Transformation Registry",
    "Invariant–Bridge–Defect Registry",
    "Source–Evidence–Version Registry",
    "Activation–Replay–Reseed Hub",
)

X_ROLES = {
    ("11", "SQ"): "exact object identity",
    ("11", "FL"): "construction / constructor",
    ("11", "CL"): "uncertainty / candidate fiber",
    ("11", "FR"): "recursive body",
    ("10", "SQ"): "operator declaration",
    ("10", "FL"): "execution",
    ("10", "CL"): "branch carrier",
    ("10", "FR"): "recursive composition",
    ("00", "SQ"): "zero taxonomy",
    ("00", "FL"): "invariant enforcement",
    ("00", "CL"): "defect / obstruction cloud",
    ("00", "FR"): "multiscale invariance",
    ("01", "SQ"): "return contract",
    ("01", "FL"): "return mechanics",
    ("01", "CL"): "multivalued return",
    ("01", "FR"): "recursive reseed / cold boot",
}

F_NAMED = {
    1: "diagonal Latin-square address carrier",
    2: "compactified complex / Hilbert",
    3: "rigged distributions and instruments",
    4: "orbit–character",
    5: "affine motion",
    6: "binary-octahedral quaternion lift",
    7: "branch cover / analytic continuation",
    8: "jets / local-asymptotic",
    9: "bulk–boundary totalized channel",
    10: "observable algebra",
    11: "commutant / sector",
    14: "commutant–Laplacian",
    15: "gain graph",
    17: "sheaf / holonomy",
    18: "cohomology / gluing / obstruction",
    22: "early warning",
    23: "compression / carry",
    24: "renormalization",
    26: "hysteresis / path-dependence",
    28: "question language",
    29: "corridor",
    31: "certificates",
    33: "replay / Merkle",
    35: "carrier unification frontier",
    37: "compiler / publication atlas",
}
F_ROUTED_ONLY = frozenset({13, 16, 27, 30, 32})

IC10_ROLES = (
    "identity / provenance",
    "syntax / normalization",
    "type / unit / carrier",
    "scope / regime / corridor",
    "invariant preservation",
    "evidence sufficiency",
    "dependency closure",
    "bridge / glue / return",
    "replay completeness",
    "promotion / canonical emission / reseed",
)

SSN_ROLES = (
    "node-state ledger",
    "edge-state ledger",
    "parallel wave engine",
    "in-between region ledger",
    "hybrid-density map",
    "thought-pattern matrix",
    "J-space commitment boundary",
    "healing and gap ledger",
    "path-signature registry",
    "projective-synapse map",
    "route-coverage audit",
    "solid-state certificate",
)


def gid_to_grid(gid: int) -> str:
    if not 1 <= gid <= 144:
        raise ValueError(f"gid outside KC144: {gid}")
    return f"R{(gid - 1) // 12 + 1:02d}C{(gid - 1) % 12 + 1:02d}"


def grid_to_gid(row: int, column: int) -> int:
    if not (1 <= row <= 12 and 1 <= column <= 12):
        raise ValueError(f"grid outside 12x12: {(row, column)}")
    return 12 * (row - 1) + column


def _seat(
    gid: int,
    band: str,
    station: str,
    role: str,
    status: str,
    **coordinates: object,
) -> Seat:
    return Seat(gid, gid_to_grid(gid), band, station, role, status, dict(coordinates))


def generate_seats() -> tuple[Seat, ...]:
    """Generate the whole atlas as disjoint orbits, never as 144 hand-entered rows."""
    seats: list[Seat] = []

    for index, role in enumerate(H6_ROLES, start=1):
        seats.append(_seat(index, "H6", f"H{index:02d}", role, "DOCUMENTED", index=index))

    for pole_index, pole in enumerate(K4):
        for lens_index, lens in enumerate(L4):
            gid = 7 + 4 * pole_index + lens_index
            seats.append(
                _seat(
                    gid,
                    "X16",
                    f"X-{pole}-{lens}",
                    X_ROLES[(pole, lens)],
                    "DOCUMENTED",
                    pole=pole,
                    lens=lens,
                )
            )

    for family_index, family in enumerate(O7):
        for lens_index, lens in enumerate(L3):
            index = 3 * family_index + lens_index + 1
            seats.append(
                _seat(
                    22 + index,
                    "BR21",
                    f"B{index:02d}",
                    f"{family}/{lens}",
                    "DOCUMENTED",
                    family=family,
                    lens=lens,
                    index=index,
                    mirror_index=22 - index,
                )
            )

    for index in range(1, 38):
        if index in F_NAMED:
            role = F_NAMED[index]
            status = "DOCUMENTED"
        elif index in F_ROUTED_ONLY:
            role = "route endpoint; source role not declared"
            status = "ROUTED_ONLY"
        else:
            role = "UNMAPPED — address generated; source role not declared"
            status = "UNMAPPED"
        seats.append(
            _seat(
                43 + index,
                "F37",
                f"F{index:02d}",
                role,
                status,
                index=index,
                coactivation_candidate_gid=index + 6,
            )
        )

    for index, role in enumerate(IC10_ROLES, start=1):
        seats.append(
            _seat(80 + index, "IC10", f"I{index:02d}", role, "DOCUMENTED", index=index)
        )

    support_sets = [
        support
        for cardinality in (1, 2, 3, 4)
        for support in combinations(K4, cardinality)
    ]
    for offset, support in enumerate(support_sets):
        mask = "".join("1" if pole in support else "0" for pole in K4)
        seats.append(
            _seat(
                91 + offset,
                "KC15",
                "{" + ",".join(support) + "}",
                f"support mask {mask}",
                "DERIVED",
                support=list(support),
                mask=mask,
                cardinality=len(support),
            )
        )

    for z, y, x in product(T3, repeat=3):
        index = 9 * (z + 1) + 3 * (y + 1) + (x + 1)
        seats.append(
            _seat(
                106 + index,
                "KC27",
                f"P{index:02d}",
                f"({x},{y},{z})",
                "DERIVED",
                coord=[x, y, z],
                index=index,
                mirror_gid=106 + 26 - index,
                ring=abs(x) + abs(y) + abs(z),
            )
        )

    for index, role in enumerate(SSN_ROLES, start=1):
        status = "DOCUMENTED" if index in (2, 3, 5, 6, 8, 9, 11, 12) else "DERIVED"
        seats.append(_seat(132 + index, "SSN12", f"M{index:02d}", role, status, index=index))

    seats.sort(key=lambda seat: seat.gid)
    if len(seats) != 144 or len({seat.gid for seat in seats}) != 144:
        raise AssertionError("KC144 generation is not bijective")
    return tuple(seats)


def _edge(a: int, b: int, edge_class: str, semantics: str) -> Edge:
    return Edge(min(a, b), max(a, b), edge_class, semantics)


def _cycle(gids: list[int], edge_class: str, semantics: str) -> set[Edge]:
    return {
        _edge(gids[i], gids[(i + 1) % len(gids)], edge_class, semantics)
        for i in range(len(gids))
    }


def _path(gids: list[int], edge_class: str, semantics: str) -> set[Edge]:
    return {
        _edge(left, right, edge_class, semantics)
        for left, right in zip(gids, gids[1:])
    }


def generate_edges(x16_reading: str = "both") -> tuple[Edge, ...]:
    """Generate typed intra-band edges.

    X16 has two lawful edge classes over the same vertices. They are deliberately
    not merged merely because their endpoints overlap.
    """
    if x16_reading not in {"both", "schedule", "algebra"}:
        raise ValueError("x16_reading must be both, schedule, or algebra")
    edges: set[Edge] = set()
    edges |= _cycle(list(range(1, 7)), "H6_RING", "control-cycle")

    if x16_reading in {"both", "schedule"}:
        for pole_index in range(4):
            edges |= _cycle(
                [7 + 4 * pole_index + lens for lens in range(4)],
                "X16_SCHEDULE",
                "C4 lens schedule",
            )
        for lens_index in range(4):
            edges |= _cycle(
                [7 + 4 * pole + lens_index for pole in range(4)],
                "X16_SCHEDULE",
                "C4 pole schedule",
            )

    if x16_reading in {"both", "algebra"}:
        for lens_index in range(4):
            vertices = [7 + 4 * pole + lens_index for pole in range(4)]
            edges |= {
                _edge(a, b, "X16_ALGEBRA", "K4 pole relation")
                for a, b in combinations(vertices, 2)
            }
        for pole_index in range(4):
            edges |= _cycle(
                [7 + 4 * pole_index + lens for lens in range(4)],
                "X16_ALGEBRA",
                "C4 lens relation",
            )

    for family_index in range(7):
        vertices = [23 + 3 * family_index + lens for lens in range(3)]
        edges |= {
            _edge(a, b, "BR21_LENS", "K3 lens relation")
            for a, b in combinations(vertices, 2)
        }
    for lens_index in range(3):
        edges |= _path(
            [23 + 3 * family + lens_index for family in range(7)],
            "BR21_OPERATOR",
            "P7 operator rail",
        )

    edges |= _path(list(range(44, 81)), "F37_RAIL", "P37 carrier address rail")
    edges |= _path(list(range(81, 91)), "IC10_CHAIN", "ordered promotion gates")

    seats = generate_seats()
    support_by_gid = {
        seat.gid: frozenset(seat.coordinates["support"])
        for seat in seats
        if seat.band == "KC15"
    }
    for source, support in support_by_gid.items():
        for target, other in support_by_gid.items():
            if len(other) == len(support) + 1 and support < other:
                edges.add(_edge(source, target, "KC15_HASSE", "nonempty B4 Hasse cover"))

    cube = {
        tuple(seat.coordinates["coord"]): seat.gid
        for seat in seats
        if seat.band == "KC27"
    }
    for coord, source in cube.items():
        for axis in range(3):
            target_coord = list(coord)
            target_coord[axis] += 1
            target_tuple = tuple(target_coord)
            if target_tuple in cube:
                edges.add(
                    _edge(source, cube[target_tuple], "KC54_EDGE", "KC27 cube rail")
                )

    edges |= _path(list(range(133, 145)), "SSN12_CHAIN", "observatory sequence")
    return tuple(sorted(edges))


def edge_census(x16_reading: str = "both") -> dict[str, int]:
    return dict(Counter(edge.edge_class for edge in generate_edges(x16_reading)))
