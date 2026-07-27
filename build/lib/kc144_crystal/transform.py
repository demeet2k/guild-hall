from __future__ import annotations

from itertools import permutations, product

from .lattice import K4, L3, L4, O7, T3, generate_seats, gid_to_grid, grid_to_gid
from .model import TransformReceipt

_K4_BITS = {"11": (0, 0), "10": (1, 0), "00": (0, 1), "01": (1, 1)}
_BITS_K4 = {value: key for key, value in _K4_BITS.items()}


def _receipt(name: str, source: int, target: int, effect: str) -> TransformReceipt:
    return TransformReceipt(name, source, target, effect, "NONE")


def grid_d4_view(gid: int, operation: str) -> TransformReceipt:
    """Rotate/reflect the 12x12 address plane without changing source identity."""
    row, column = ((gid - 1) // 12 + 1, (gid - 1) % 12 + 1)
    operations = {
        "identity": (row, column),
        "r90": (column, 13 - row),
        "r180": (13 - row, 13 - column),
        "r270": (13 - column, row),
        "reflect_vertical": (row, 13 - column),
        "reflect_horizontal": (13 - row, column),
        "reflect_diagonal": (column, row),
        "reflect_antidiagonal": (13 - column, 13 - row),
    }
    if operation not in operations:
        raise ValueError(f"unknown D4 operation: {operation}")
    target = grid_to_gid(*operations[operation])
    return _receipt(f"GRID_D4::{operation}", gid, target, "ADDRESS_VIEW_ONLY")


def x16_schedule_rotate(gid: int, pole_turn: int = 0, lens_turn: int = 0) -> TransformReceipt:
    if not 7 <= gid <= 22:
        raise ValueError("X16 transform requires GID007..022")
    offset = gid - 7
    pole_index, lens_index = divmod(offset, 4)
    target = 7 + 4 * ((pole_index + pole_turn) % 4) + (lens_index + lens_turn) % 4
    return _receipt(
        f"X16_SCHEDULE::C4xC4::{pole_turn % 4},{lens_turn % 4}",
        gid,
        target,
        "BAND_AUTOMORPHISM",
    )


def x16_algebra_translate(
    gid: int, pole_element: str = "11", lens_turn: int = 0
) -> TransformReceipt:
    if not 7 <= gid <= 22 or pole_element not in K4:
        raise ValueError("X16 algebra transform requires an X16 gid and a K4 element")
    offset = gid - 7
    pole_index, lens_index = divmod(offset, 4)
    pole = K4[pole_index]
    left = _K4_BITS[pole]
    right = _K4_BITS[pole_element]
    translated = _BITS_K4[(left[0] ^ right[0], left[1] ^ right[1])]
    target = 7 + 4 * K4.index(translated) + (lens_index + lens_turn) % 4
    return _receipt(
        f"X16_ALGEBRA::V4xC4::{pole_element},{lens_turn % 4}",
        gid,
        target,
        "BAND_AUTOMORPHISM",
    )


def br_rotate(gid: int, operator_turn: int = 0, lens_turn: int = 0) -> TransformReceipt:
    if not 23 <= gid <= 43:
        raise ValueError("BR21 transform requires GID023..043")
    family_index, lens_index = divmod(gid - 23, 3)
    target = 23 + 3 * ((family_index + operator_turn) % 7) + (lens_index + lens_turn) % 3
    return _receipt(
        f"BR21::C7xC3::{operator_turn % 7},{lens_turn % 3}",
        gid,
        target,
        "BAND_AUTOMORPHISM",
    )


def br_mirror(gid: int) -> TransformReceipt:
    if not 23 <= gid <= 43:
        raise ValueError("BR21 mirror requires GID023..043")
    index = gid - 22
    return _receipt("BR21::MIRROR", gid, 22 + (22 - index), "BAND_INVOLUTION")


def f37_reflect(gid: int) -> TransformReceipt:
    if not 44 <= gid <= 80:
        raise ValueError("F37 reflection requires GID044..080")
    return _receipt("F37::P37_REFLECTION", gid, 124 - gid, "ADDRESS_RAIL_VIEW")


def coactivation_sigma(gid: int) -> TransformReceipt:
    """Map operator seats 007..043 to carrier addresses 044..080.

    Equal cardinality makes this a candidate coactivation bijection. It is not
    an evidence transport, identity equation, or promotion.
    """
    if not 7 <= gid <= 43:
        raise ValueError("sigma requires an X16 or BR21 operator gid")
    return _receipt("SIGMA_PLUS_37", gid, gid + 37, "COACTIVATION_CANDIDATE")


def kc15_permute(gid: int, permutation: tuple[int, int, int, int]) -> TransformReceipt:
    if not 91 <= gid <= 105 or sorted(permutation) != [0, 1, 2, 3]:
        raise ValueError("KC15 transform requires a KC15 gid and an S4 permutation")
    seat = generate_seats()[gid - 1]
    support = set(seat.coordinates["support"])
    mapping = {K4[index]: K4[permutation[index]] for index in range(4)}
    transformed = frozenset(mapping[pole] for pole in support)
    for candidate in generate_seats()[90:105]:
        if frozenset(candidate.coordinates["support"]) == transformed:
            return _receipt(
                f"KC15::S4::{''.join(map(str, permutation))}",
                gid,
                candidate.gid,
                "SUPPORT_AUTOMORPHISM",
            )
    raise AssertionError("S4 action left the nonempty Boolean lattice")


def kc27_transform(
    gid: int,
    axis_permutation: tuple[int, int, int] = (0, 1, 2),
    signs: tuple[int, int, int] = (1, 1, 1),
) -> TransformReceipt:
    if not 106 <= gid <= 132:
        raise ValueError("KC27 transform requires GID106..132")
    if sorted(axis_permutation) != [0, 1, 2] or any(sign not in (-1, 1) for sign in signs):
        raise ValueError("KC27 transform requires an axis permutation and ±1 signs")
    coord = tuple(generate_seats()[gid - 1].coordinates["coord"])
    transformed = tuple(signs[i] * coord[axis_permutation[i]] for i in range(3))
    x, y, z = transformed
    target = 106 + 9 * (z + 1) + 3 * (y + 1) + (x + 1)
    return _receipt(
        f"KC27::B3::{axis_permutation},{signs}",
        gid,
        target,
        "CUBE_AUTOMORPHISM",
    )


def transformation_catalog() -> dict[str, object]:
    return {
        "law": "transformations generate addresses, relations, and coactivations; truth_effect is always NONE",
        "groups": {
            "address_plane": {"group": "D4", "order": 8, "identity": "source GID retained"},
            "X16_schedule": {"group": "C4×C4", "order": 16},
            "X16_algebra": {"action": "V4×C4", "order": 16},
            "BR21_rotations": {"group": "C7×C3", "order": 21},
            "BR21_mirror": {"group": "C2", "order": 2},
            "F37_rail": {"group": "C2", "order": 2},
            "KC15": {"group": "S4", "order": len(tuple(permutations(range(4))))},
            "KC27": {
                "group": "B3 signed permutations",
                "order": len(tuple(permutations(range(3)))) * len(tuple(product((-1, 1), repeat=3))),
            },
        },
        "typed_nonidentities": {
            "SIGMA_PLUS_37": "37↔37 candidate coactivation; not evidence transport",
            "KC54_edges": "54 cube rails E(P3□P3□P3)",
            "KC54_duplex": "54 node shadows KC27+⊕KC27*",
        },
    }
