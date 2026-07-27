#!/usr/bin/env python3
"""
KC144.V2 :: GID082 :: R07C10 :: IC10-I02 :: SYNTAX / NORMALIZATION
The canonicalisation policy.

GID090's first execution found I02 failing on 4 of 5 candidates for one reason:
raw_cid and canon_profile were None everywhere. That is not four omissions. It is
one corpus-wide gap, confirmed in the source text:

    HASH::UNCOMPUTED[NO HASH PROCEDURE ADMITTED]                       (KC144 :: 6-)
    01::RETURN::INCOMPARABLE_UNTIL_POLICY_MIGRATION                    (KC144 :: 10-)
    PRODUCTION_STATUS::UNTRUSTED                                       (KC144 :: 10-)

This file is the artifact that closes it for all 144 seats.

BINDING LAW (corpus, verbatim):
    RawCID must never be overwritten by NormalCID.
    L0 equality proves exact duplication. Only certified L6 equality supports
    semantic merging.
    A digest establishes integrity correspondence. It does not establish truth.
    Digests are invalid without a declared HashPolicyID + CanonProfileID.
"""
from __future__ import annotations
import hashlib, json, re, unicodedata
from dataclasses import dataclass

HASH_POLICY_ID   = "KC144.HASH.V1"
CANON_PROFILE_ID = "KC144.CANON.V1"

HASH_POLICY = {
    "id": HASH_POLICY_ID,
    "algorithm": "sha256",
    "encoding": "utf-8",
    "digest_form": "lowercase hex, 64 chars",
    "field_separator": "|",
    "subfield_separator": ";",
    "record_terminator": "\n",
    "field_order": "declared per schema, IMMUTABLE once registered",
    "domain_separation": "every digest is prefixed with its schema tag, so a raw-body "
                         "digest can never collide with a packet digest",
    "law": "A digest establishes integrity correspondence, not truth.",
}

CANON_PROFILE = {
    "id": CANON_PROFILE_ID,
    "unicode": "NFC",
    "line_endings": "LF",
    "trailing_whitespace": "stripped per line",
    "leading_trailing_blank_lines": "stripped",
    "internal_blank_runs": "collapsed to a single blank line",
    "markdown_escape_artifacts": r"backslash-escapes emitted by Docs export (\_ \* \- \[ \]) removed",
    "case": "PRESERVED - never folded",
    "numbers": "PRESERVED - never reformatted",
    "preserves": "every token that bears meaning",
    "law": "Normalization changes representation. It never changes meaning. "
           "The raw body is retained and independently digested.",
}

# Equality ladder. L0 is proof of duplication; only L6 supports semantic merging.
EQUALITY_LEVELS = {
    "L0": "byte-identical raw body",
    "L1": "identical after canonicalisation (NormalCID equal, RawCID may differ)",
    "L2": "identical structured packet (same schema, same field values)",
    "L3": "identical under a declared field-order normalisation",
    "L4": "equal under a declared tolerance on numeric fields",
    "L5": "structurally isomorphic under a declared, witnessed relabelling",
    "L6": "semantically equivalent under a CERTIFIED bridge with a return witness",
}
MERGE_AUTHORIZED_AT = "L6"


def canonicalise(text: str) -> str:
    """CANON_PROFILE_ID = KC144.CANON.V1. Deterministic, idempotent, meaning-preserving."""
    t = unicodedata.normalize("NFC", text)
    t = t.replace("\r\n", "\n").replace("\r", "\n")
    t = re.sub(r"\\([_*\-\[\]()#+.!`])", r"\1", t)      # Docs-export escape artifacts
    t = "\n".join(line.rstrip() for line in t.split("\n"))
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip("\n")


def _digest(tag: str, payload: bytes) -> str:
    h = hashlib.sha256()
    h.update(tag.encode("utf-8")); h.update(b"\x00")     # domain separation
    h.update(payload)
    return h.hexdigest()


@dataclass
class CID:
    """Both identities. The raw one is never overwritten by the normalized one."""
    raw_cid: str
    normal_cid: str
    hash_policy: str
    canon_profile: str
    raw_len: int
    normal_len: int

    def as_fields(self) -> dict:
        return {"raw_cid": self.raw_cid, "canon_profile": self.canon_profile,
                "normal_cid": self.normal_cid, "hash_policy": self.hash_policy}

    def comparable_with(self, other: "CID") -> bool:
        """Digests from different policies are INCOMPARABLE, not merely unequal."""
        return (self.hash_policy == other.hash_policy
                and self.canon_profile == other.canon_profile)

    def equality_level(self, other: "CID") -> str:
        if not self.comparable_with(other):
            return "INCOMPARABLE_UNTIL_POLICY_MIGRATION"
        if self.raw_cid == other.raw_cid:
            return "L0"
        if self.normal_cid == other.normal_cid:
            return "L1"
        return "NOT_EQUAL_AT_L0_OR_L1"


def bind(text: str, schema_tag: str = "KC144.BODY") -> CID:
    """The single entry point. Every seat, every candidate, every packet uses this."""
    raw = text.encode("utf-8")
    can = canonicalise(text)
    return CID(raw_cid=_digest(schema_tag + ".RAW", raw),
               normal_cid=_digest(schema_tag + ".NORMAL", can.encode("utf-8")),
               hash_policy=HASH_POLICY_ID, canon_profile=CANON_PROFILE_ID,
               raw_len=len(raw), normal_len=len(can.encode("utf-8")))


# ---------------------------------------------------------------------------
def _selftest():
    checks = []
    def ck(name, cond, ev=""): checks.append((name, bool(cond), ev))

    a = "# Title\n\nbody   \r\n\r\n\r\ntail\n"
    b = "# Title\n\nbody\n\ntail"
    A, B = bind(a), bind(b)
    ck("determinism", bind(a).raw_cid == A.raw_cid)
    ck("idempotence of canonicalisation",
       canonicalise(canonicalise(a)) == canonicalise(a))
    ck("RawCID separates what NormalCID merges",
       A.raw_cid != B.raw_cid and A.normal_cid == B.normal_cid,
       f"raw differ={A.raw_cid != B.raw_cid}, normal equal={A.normal_cid == B.normal_cid}")
    ck("equality level = L1 (normalized, not byte-identical)", A.equality_level(B) == "L1",
       A.equality_level(B))
    ck("identity is L0", A.equality_level(bind(a)) == "L0")
    ck("domain separation: raw and normal digests never collide",
       A.raw_cid != A.normal_cid)

    # Docs-export escape artifacts are removed, meaning preserved
    esc = r"NODE::KC144\_V2::GID090 \- IC10\_I10"
    ck("markdown escape artifacts stripped",
       canonicalise(esc) == "NODE::KC144_V2::GID090 - IC10_I10", canonicalise(esc))

    # Case and numbers are NOT folded - meaning-preservation
    ck("case preserved", canonicalise("PASS pass") == "PASS pass")
    ck("numbers preserved", canonicalise("1.0 1 01") == "1.0 1 01")

    # Cross-policy comparison must refuse, not guess
    other = CID("x", "y", "OTHER.HASH.V0", "OTHER.CANON.V0", 0, 0)
    ck("cross-policy digests are INCOMPARABLE, not unequal",
       A.equality_level(other) == "INCOMPARABLE_UNTIL_POLICY_MIGRATION",
       A.equality_level(other))

    ck("merge authorized only at L6", MERGE_AUTHORIZED_AT == "L6")

    print("GID082 / IC10-I02 :: CANONICALISATION POLICY :: SELF-TEST")
    print("-" * 70)
    for n, ok, ev in checks:
        print(f"  [{'PASS' if ok else 'FAIL'}] {n}" + (f"  :: {ev}" if ev and not ok else ""))
    n_ok = sum(1 for _, o, _ in checks if o)
    print("-" * 70)
    print(f"  {n_ok}/{len(checks)} checks pass")
    print(f"  HashPolicyID   = {HASH_POLICY_ID}")
    print(f"  CanonProfileID = {CANON_PROFILE_ID}")
    print("\n  This artifact satisfies IC10-I02 for ANY seat that calls bind().")
    print("  It does NOT establish truth. A digest is integrity correspondence only.")
    return n_ok == len(checks)


if __name__ == "__main__":
    _selftest()
