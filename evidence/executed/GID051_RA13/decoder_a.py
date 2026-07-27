#!/usr/bin/env python3
import hashlib
import json
import pathlib
import sys

TOP_KEYS = [
    "schema", "seedID", "version", "parent", "identity", "query",
    "carrier", "routes", "branchTestAddress", "approximation", "defects",
    "provenance", "witnesses", "unresolved", "promotion", "return",
]
ROUTES = [
    "F03<->F08", "F07<->F08", "F08<->F09",
    "F08<->F17", "F08->F18", "F08->F31",
]


def require(condition, code):
    if not condition:
        raise ValueError(code)


def projection(seed):
    q1 = seed["approximation"]["Q01"]
    q2 = seed["approximation"]["Q02"]
    values = [
        seed["schema"], seed["version"], seed["identity"]["gid"],
        seed["identity"]["grid"], seed["identity"]["station"],
        seed["carrier"]["tuple"], seed["carrier"]["jet"],
        *seed["routes"], seed["branchTestAddress"]["Q01"],
        q1["model"], str(q1["order"]), q1["remainder"], q1["errorBound"],
        q1["neighborhood"], q1["singularDirections"],
        q1["globalizationBurden"], q1["integratedModel"],
        str(q1["integratedOrder"]), q1["integratedRemainder"],
        q1["integratedErrorBound"], q1["integratedNeighborhood"],
        q2["object"], q2["ordinaryJet"], q2["testSpace"], q2["order"],
        q2["remainder"], q2["errorBound"], q2["neighborhood"],
        q2["singularDirections"], q2["globalizationBurden"],
        seed["promotion"]["IC10"], seed["promotion"]["QSHRINK"],
        seed["return"]["rollbackTarget"], seed["return"]["nextSeed"],
    ]
    encoded = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def main():
    path = pathlib.Path(sys.argv[1])
    expected = sys.argv[2] if len(sys.argv) > 2 else None
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected and digest != expected:
        print(f"DECODER_A::DIGEST_MISMATCH EXPECTED::{expected} OBSERVED::{digest}")
        return 2
    require(raw.endswith(b"\n"), "FINAL_LF_MISSING")
    require(raw.count(b"\n") == 1, "PAYLOAD_NOT_SINGLE_LINE")
    seed = json.loads(raw)
    require(list(seed.keys()) == TOP_KEYS, "TOP_LEVEL_ORDER_OR_FIELD_MISMATCH")
    require(seed["schema"] == "KC144.STATION_REENTRY.F08.V1", "SCHEMA_MISMATCH")
    require(seed["version"] == "KC144.V1", "VERSION_MISMATCH")
    require(seed["identity"]["gid"] == "051", "GID_MISMATCH")
    require(seed["identity"]["grid"] == "R05C03", "GRID_MISMATCH")
    require(seed["identity"]["station"] == "F08", "STATION_MISMATCH")
    require(seed["routes"] == ROUTES, "ROUTE_MISMATCH")
    require(seed["carrier"]["tuple"] == "A8=(P8,iota8,Lambda8,partial8,N8)", "CARRIER_MISMATCH")
    require(seed["approximation"]["Q01"]["order"] == 2, "Q01_ORDER_MISMATCH")
    require(seed["approximation"]["Q01"]["remainder"] == "R3(h)", "Q01_REMAINDER_MISMATCH")
    require(seed["approximation"]["Q01"]["neighborhood"] == "|h|<=r<1 ON PLUS LIFT", "Q01_NEIGHBORHOOD_MISMATCH")
    require(seed["approximation"]["Q02"]["ordinaryJet"] == "UNDEFINED", "Q02_JET_MISMATCH")
    require(seed["approximation"]["Q02"]["testSpace"] == "REQUIRED", "Q02_TEST_SPACE_MISMATCH")
    require(seed["promotion"]["IC10"] == "HOLD", "IC10_AUTHORITY_MISMATCH")
    require(seed["promotion"]["QSHRINK"] == "HOLD", "QSHRINK_AUTHORITY_MISMATCH")
    print(f"DECODER_A::PASS SHA256::{digest} PROJECTION::{projection(seed)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, ValueError, json.JSONDecodeError) as exc:
        print(f"DECODER_A::BLOCK::{exc}")
        raise SystemExit(1)
