#!/usr/bin/env python3
"""
KC144.V2 :: GID090 :: R08C06 :: IC10-I10 :: PROMOTION / CANONICAL EMISSION / RESEED

The promotion kernel. Executable, not declarative.

Constitutional basis (recovered verbatim from KC144 "Hmm", GID081-089 build):

    Promotable(C) <=>  /\_{k=1..9} I_k(C) = PASS
                    /\ UnknownHardClauses(C) = {}
                    /\ OutOfScopeRequiredClauses(C) = {}
                    /\ HardDebt(C) = {}
                    /\ Independent(W_verify, C)
                    /\ sigma_S in {ALLOW, ALLOW_LIMITED}
                    /\ ReturnWitness(C) != {}

    Promotable(C) != Promoted(C).
    I10(C) -> Pi_C = <CandidateID, SourceEpoch, GateReceipts_1:9, Authority,
                      ClaimCeiling, ResidualLedger, RollbackHead, SuccessorPolicy,
                      PromotionDigest>
    I_k(C) = FAIL  ==>  C -> QUARANTINE (+) REPAIR_ROUTE      [the Trellis operation]
    QSHRINK is FORBIDDEN_BEFORE_GID090 and operates only on a promoted C+.

Harness law (binding): every check here reduces to counting, enumeration, presence,
or comparison. No gate is phrased 'assess', 'consider', or 'review'.
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Any
import hashlib, json

# ---------------------------------------------------------------------------
# 0 - TYPED VOCABULARIES.  None of these collapse into one another.
# ---------------------------------------------------------------------------

VERDICT = ("PASS", "FAIL", "UNKNOWN", "OUT_OF_SCOPE")   # four constitutionally distinct
TEST_INVALID = "TEST_INVALID"                            # verifier-state, outside the four
NOT_EVALUATED = "NOT_EVALUATED"                          # gate ordering, not a result

SIGMA_E = ("EXACT", "SUPPORTED", "PARTIAL", "UNSUPPORTED")            # evidence maturity
SIGMA_X = ("PASS", "FAIL", "UNKNOWN", "OUT_OF_SCOPE")                 # execution result
SIGMA_S = ("ALLOW", "ALLOW_LIMITED", "RESEARCH_ONLY", "PAUSE", "REFUSE")  # stewardship
SIGMA_P = ("DRAFT", "CANDIDATE", "TESTED", "PROMOTABLE", "PROMOTED", "DEPRECATED")

RETURN_CLASSES = (
    "EXACT_INVERSE", "PARTIAL_INVERSE", "ADJOINT", "PSEUDOINVERSE", "DECODER",
    "COMPENSATING_RETURN", "SET_VALUED_RETURN", "BRANCH_PRESERVING_ANTECEDENT_SET",
    "IMPOSSIBLE_RETURN",
)

# delta_return components.  delta_hard MUST be zero for promotion.
DELTA_COMPONENTS = ("id", "sem", "route", "source", "branch", "authority", "time")
DELTA_HARD = ("id", "source", "authority")

GATE_TABLE = {
    "I01": (81, "R07C09", "identity / provenance",
            "Is the object exactly identified and sourced?"),
    "I02": (82, "R07C10", "syntax / normalization",
            "Is its form canonical and its raw identity preserved?"),
    "I03": (83, "R07C11", "type / unit / carrier",
            "Is every object typed with carrier and units?"),
    "I04": (84, "R07C12", "scope / regime / corridor",
            "Is the validity corridor declared and testable?"),
    "I05": (85, "R08C01", "invariant preservation",
            "Is each invariant preserved under a declared transport?"),
    "I06": (86, "R08C02", "evidence sufficiency",
            "Is the evidence class sufficient and lawful?"),
    "I07": (87, "R08C03", "dependency closure",
            "Are all dependencies resolved and unrevoked?"),
    "I08": (88, "R08C04", "bridge / defect / return",
            "Are transport loss and return behaviour declared?"),
    "I09": (89, "R08C05", "replay completeness",
            "Can an independent process reproduce the result?"),
    "I10": (90, "R08C06", "promotion / canonical emission / reseed",
            "May this exact candidate become an authoritative successor?"),
}

# Failure routes.  A failed gate never deletes; it routes.
REPAIR_ROUTES = {
    "I01": "GID001/H01 identity registry",
    "I02": "GID074/F31 certificate + GID082 renormalization",
    "I03": "GID083 type admission; GID061/F18 carrier defect",
    "I04": "GID084 corridor; GID072/F29 corridor carrier",
    "I05": "GID085; repair candidates GID038/GID039/GID040",
    "I06": "GID005/H05 source-evidence registry; GID086",
    "I07": "GID087 dependency snapshot; REVOKE + retest",
    "I08": "GID088; failed glue -> GID061; ambiguous return -> GID021",
    "I09": "GID089 first-divergence checkpoint; GID140/M08 healing ledger",
    "I10": "GID090 quarantine shelf; GID140/M08; rollback head",
}


# ---------------------------------------------------------------------------
# 1 - CANDIDATE.  C = <R+, R|x|, R*, Q, Gamma, W, D, P, A>
# ---------------------------------------------------------------------------

@dataclass
class Clause:
    """A single mechanical check. `hard` clauses block; soft ones only annotate."""
    name: str
    verdict: str
    hard: bool
    evidence: str

@dataclass
class GateReceipt:
    gate: str
    gid: int
    grid: str
    role: str
    verdict: str
    clauses: list[Clause] = field(default_factory=list)
    repair_route: str | None = None

    def failed(self):    return [c for c in self.clauses if c.hard and c.verdict == "FAIL"]
    def unknown(self):   return [c for c in self.clauses if c.hard and c.verdict == "UNKNOWN"]
    def oos(self):       return [c for c in self.clauses if c.hard and c.verdict == "OUT_OF_SCOPE"]


@dataclass
class Candidate:
    """
    The IC10 candidate.  Fields are DECLARED state, not inferred.  Absence is a
    typed absence: None means NOT DECLARED, which is never silently read as zero.
    """
    candidate_id: str
    source_epoch: str
    station: str                      # the GID this candidate returns from

    # --- the three returns.  successful object != restartable process != auditable return
    r_plus: dict | None = None        # R+  GID041 certified constructive successor
    r_hinge: dict | None = None       # R|x| GID042 replayable process return
    r_star: dict | None = None        # R*  GID043 conjugate/auditable return

    q_contract: dict | None = None    # Q   query contract (goal frozen at admission)
    corridor: dict | None = None      # Gamma validity corridor
    witnesses: list[dict] = field(default_factory=list)      # W
    defects: list[dict] = field(default_factory=list)        # D  defect/debt ledger
    provenance: list[dict] = field(default_factory=list)     # P
    authority: dict | None = None     # A  stewardship / claim ceiling

    # --- declared status vector (the candidate's own claim about itself; verified below)
    sigma_E: str = "UNSUPPORTED"
    sigma_X: str = "UNKNOWN"
    sigma_S: str = "RESEARCH_ONLY"
    sigma_P: str = "DRAFT"

    # --- reconstruction error vector.  None per component = NOT MEASURED (not zero).
    delta_return: dict[str, float | None] = field(default_factory=dict)

    # --- verifier identity, for the independence test
    constructor_id: str = ""
    verifier_id: str = ""
    verifier_channel: str = ""
    constructor_channel: str = ""

    notes: str = ""


# ---------------------------------------------------------------------------
# 2 - MECHANICAL PRIMITIVES.  Counting, presence, enumeration, comparison only.
# ---------------------------------------------------------------------------

def present(x) -> bool:
    """Declared and non-empty.  None is NOT DECLARED; [] and {} are EMPTY."""
    return x is not None and x != {} and x != []

def declared_or_unknown(x, name, hard=True, ok_msg="", bad_msg="") -> Clause:
    if x is None:
        return Clause(name, "UNKNOWN", hard, f"{name}: NOT DECLARED (UNKNOWN != 0)")
    if not present(x):
        return Clause(name, "FAIL", hard, bad_msg or f"{name}: declared but empty")
    return Clause(name, "PASS", hard, ok_msg or f"{name}: declared")

def enum_in(value, allowed, name, hard=True) -> Clause:
    if value is None:
        return Clause(name, "UNKNOWN", hard, f"{name}: NOT DECLARED")
    if value not in allowed:
        return Clause(name, "FAIL", hard, f"{name}={value!r} not in {allowed}")
    return Clause(name, "PASS", hard, f"{name}={value}")

def count_at_least(seq, n, name, hard=True) -> Clause:
    if seq is None:
        return Clause(name, "UNKNOWN", hard, f"{name}: NOT DECLARED")
    k = len(seq)
    v = "PASS" if k >= n else "FAIL"
    return Clause(name, v, hard, f"{name}: count={k}, required>={n}")

def gate_verdict(clauses: list[Clause]) -> str:
    """A gate is PASS only if every hard clause is PASS.  FAIL dominates UNKNOWN
    dominates OUT_OF_SCOPE.  Soft clauses never change the verdict."""
    hard = [c for c in clauses if c.hard]
    if any(c.verdict == "FAIL" for c in hard):          return "FAIL"
    if any(c.verdict == "UNKNOWN" for c in hard):       return "UNKNOWN"
    if any(c.verdict == "OUT_OF_SCOPE" for c in hard):  return "OUT_OF_SCOPE"
    return "PASS"


# ---------------------------------------------------------------------------
# 3 - GATES I01 .. I09
# ---------------------------------------------------------------------------

def _mk(gate, clauses) -> GateReceipt:
    gid, grid, role, _q = GATE_TABLE[gate]
    v = gate_verdict(clauses)
    return GateReceipt(gate, gid, grid, role, v, clauses,
                       REPAIR_ROUTES[gate] if v != "PASS" else None)

def I01(C: Candidate) -> GateReceipt:
    """identity / provenance"""
    cs = [
        declared_or_unknown(C.candidate_id, "candidate_id"),
        declared_or_unknown(C.source_epoch, "source_epoch"),
        declared_or_unknown(C.station, "station_address"),
        count_at_least(C.provenance, 1, "provenance_anchors"),
    ]
    # Every provenance anchor must carry an exact locator, not just a title.
    if C.provenance:
        unpinned = [p.get("title", "?") for p in C.provenance if not p.get("locator")]
        cs.append(Clause("provenance_locators_pinned",
                         "PASS" if not unpinned else "FAIL", True,
                         f"unpinned anchors={unpinned}" if unpinned
                         else f"all {len(C.provenance)} anchors carry exact locators"))
        # An echo of the system's own prior output is not independent evidence.
        echoes = [p.get("title", "?") for p in C.provenance
                  if p.get("evidence_class") == "E"]
        cs.append(Clause("echo_not_counted_as_witness", "PASS", False,
                         f"echo-class anchors excluded from evidence: {echoes}"
                         if echoes else "no echo-class anchors"))
    return _mk("I01", cs)

def I02(C: Candidate) -> GateReceipt:
    """syntax / normalization.  RawCID must never be overwritten by NormalCID."""
    cs = [declared_or_unknown(C.q_contract, "canonical_form_declared")]
    if C.q_contract:
        cs.append(Clause("raw_identity_preserved",
                         "PASS" if C.q_contract.get("raw_cid") else "UNKNOWN", True,
                         f"raw_cid={C.q_contract.get('raw_cid')}"))
        cs.append(Clause("normalization_profile_declared",
                         "PASS" if C.q_contract.get("canon_profile") else "UNKNOWN", True,
                         f"canon_profile={C.q_contract.get('canon_profile')}"))
    return _mk("I02", cs)

def I03(C: Candidate) -> GateReceipt:
    """type / unit / carrier.  A domain name alone is not a type."""
    cs = []
    for label, R in (("R+", C.r_plus), ("R|x|", C.r_hinge), ("R*", C.r_star)):
        if R is None:
            cs.append(Clause(f"{label}_typed", "UNKNOWN", True, f"{label}: NOT DECLARED"))
            continue
        missing = [k for k in ("carrier", "type") if not R.get(k)]
        cs.append(Clause(f"{label}_typed", "PASS" if not missing else "FAIL", True,
                         f"{label}: missing {missing}" if missing
                         else f"{label}: carrier={R['carrier']} type={R['type']}"))
    return _mk("I03", cs)

def I04(C: Candidate) -> GateReceipt:
    """scope / regime / corridor.  A verdict is valid only for the corridor tested."""
    cs = [declared_or_unknown(C.corridor, "corridor_declared")]
    if C.corridor:
        cs.append(Clause("corridor_membership_testable",
                         "PASS" if C.corridor.get("membership_test") else "FAIL", True,
                         f"membership_test={C.corridor.get('membership_test')}"))
        cs.append(Clause("claim_ceiling_declared",
                         "PASS" if C.corridor.get("claim_ceiling") else "UNKNOWN", True,
                         f"claim_ceiling={C.corridor.get('claim_ceiling')}"))
    return _mk("I04", cs)

def I05(C: Candidate) -> GateReceipt:
    """invariant preservation under a DECLARED transport, not by name-matching."""
    inv = (C.r_plus or {}).get("invariants")
    cs = [declared_or_unknown(inv, "invariants_declared")]
    if inv:
        untransported = [i.get("name", "?") for i in inv if not i.get("transport")]
        cs.append(Clause("each_invariant_has_declared_transport",
                         "PASS" if not untransported else "FAIL", True,
                         f"invariants lacking transport={untransported}" if untransported
                         else f"all {len(inv)} invariants carry a declared transport"))
        unwitnessed = [i.get("name", "?") for i in inv if not i.get("witness")]
        cs.append(Clause("each_invariant_witnessed",
                         "PASS" if not unwitnessed else "FAIL", True,
                         f"unwitnessed={unwitnessed}" if unwitnessed
                         else "all invariants witnessed"))
    return _mk("I05", cs)

def I06(C: Candidate) -> GateReceipt:
    """evidence sufficiency.  Structural coherence is never evidence."""
    cs = [
        enum_in(C.sigma_E, SIGMA_E, "sigma_E_declared"),
        count_at_least(C.witnesses, 1, "witnesses"),
    ]
    if C.witnesses:
        classes = [w.get("evidence_class") for w in C.witnesses]
        cs.append(Clause("every_witness_has_evidence_class",
                         "PASS" if all(classes) else "FAIL", True,
                         f"classes={classes}"))
        # A structural pass is not an empirical witness.
        empirical = [w for w in C.witnesses if w.get("evidence_class") in ("MEASURED", "A")]
        cs.append(Clause("empirical_witness_present",
                         "PASS" if empirical else "UNKNOWN", False,
                         f"empirical/retrieved witnesses={len(empirical)} "
                         f"(structural-only evidence cannot promote an empirical claim)"))
        if C.sigma_E == "EXACT" and not empirical:
            cs.append(Clause("sigma_E_EXACT_requires_measured_witness", "FAIL", True,
                             "sigma_E=EXACT declared with zero MEASURED witnesses"))
    return _mk("I06", cs)

def I07(C: Candidate) -> GateReceipt:
    """dependency closure.  An open bridge is replayed as open, never silently filled."""
    deps = (C.q_contract or {}).get("dependencies")
    cs = [declared_or_unknown(deps, "dependencies_declared")]
    if deps:
        open_deps = [d.get("id", "?") for d in deps if d.get("status") != "CLOSED"]
        cs.append(Clause("all_dependencies_closed",
                         "PASS" if not open_deps else "FAIL", True,
                         f"open dependencies={open_deps}" if open_deps
                         else f"all {len(deps)} dependencies CLOSED"))
        revoked = [d.get("id", "?") for d in deps if d.get("revoked")]
        cs.append(Clause("no_revoked_dependencies",
                         "PASS" if not revoked else "FAIL", True, f"revoked={revoked}"))
    return _mk("I07", cs)

def I08(C: Candidate) -> GateReceipt:
    """bridge / defect / return.  No forward path completes until return is typed."""
    cs = []
    for label, R in (("R+", C.r_plus), ("R|x|", C.r_hinge), ("R*", C.r_star)):
        rc = (R or {}).get("return_class")
        cs.append(enum_in(rc, RETURN_CLASSES, f"{label}_return_class"))
    # Loss must be declared, and IMPOSSIBLE_RETURN is a lawful declared result.
    losses = [(R or {}).get("loss_manifest") for R in (C.r_plus, C.r_hinge, C.r_star)]
    cs.append(Clause("loss_manifest_declared_on_all_three_returns",
                     "PASS" if all(l is not None for l in losses) else "UNKNOWN", True,
                     f"loss manifests declared={[l is not None for l in losses]}"))
    # Open bridges are lawful but must be enumerated, not absent.
    ob = (C.r_star or {}).get("open_bridges")
    cs.append(Clause("open_bridges_enumerated",
                     "PASS" if ob is not None else "UNKNOWN", True,
                     f"open_bridges={ob}"))
    return _mk("I08", cs)

def I09(C: Candidate) -> GateReceipt:
    """replay completeness.  'Can an INDEPENDENT process reproduce the result?'"""
    rp = (C.r_hinge or {}).get("replay_packet")
    cs = [declared_or_unknown(rp, "replay_packet_declared")]
    if rp:
        required = ["inputs", "addresses", "atlas_version", "operations", "route_order",
                    "policies", "seeds", "decoder", "expected_result"]
        missing = [k for k in required if k not in rp]
        cs.append(Clause("replay_packet_complete",
                         "PASS" if not missing else "FAIL", True,
                         f"missing fields={missing}" if missing
                         else f"all {len(required)} replay fields present"))
        cs.append(Clause("replay_executed",
                         "PASS" if rp.get("executed") else "UNKNOWN", True,
                         f"executed={rp.get('executed')}"))
        bc = rp.get("boot_class")
        cs.append(Clause("boot_class_independent",
                         "PASS" if bc in ("B3", "B4", "B5", "B6") else
                         ("FAIL" if bc in ("B0", "B1", "B2") else "UNKNOWN"), True,
                         f"boot_class={bc} (only B3+ is an independent cold boot)"))
    # delta_hard must be measured AND zero.
    dh = [(k, C.delta_return.get(k)) for k in DELTA_HARD]
    unmeasured = [k for k, v in dh if v is None]
    nonzero = [(k, v) for k, v in dh if v is not None and v != 0]
    if unmeasured:
        cs.append(Clause("delta_hard_measured", "UNKNOWN", True,
                         f"unmeasured hard components={unmeasured} (UNKNOWN != 0)"))
    elif nonzero:
        cs.append(Clause("delta_hard_zero", "FAIL", True, f"nonzero hard delta={nonzero}"))
    else:
        cs.append(Clause("delta_hard_zero", "PASS", True,
                         "delta_id + delta_source + delta_authority = 0"))
    return _mk("I09", cs)

GATES_1_9 = [I01, I02, I03, I04, I05, I06, I07, I08, I09]


# ---------------------------------------------------------------------------
# 4 - I10.  The promotion authority.  GID090.
# ---------------------------------------------------------------------------

@dataclass
class PromotionReceipt:
    """Pi_C - emitted ONLY on promotion."""
    candidate_id: str
    source_epoch: str
    gate_receipts_1_9: list[dict]
    authority: dict
    claim_ceiling: list[str]
    residual_ledger: list[dict]
    rollback_head: str
    successor_policy: str
    promotion_digest: str

@dataclass
class Quarantine:
    """The Trellis operation: refuse promotion without destroying the material."""
    candidate_id: str
    blocking_clauses: list[dict]
    repair_routes: list[str]
    preserved: bool = True
    note: str = ("QUARANTINE (+) REPAIR_ROUTE. The candidate is preserved in full, "
                 "remains addressable, and may be re-submitted after repair. "
                 "Nothing is deleted.")

@dataclass
class I10Result:
    candidate_id: str
    gate_receipts: list[GateReceipt]
    sigma: tuple[str, str, str, str]
    promotable: bool
    promotable_clauses: list[Clause]
    verdict: str                         # PROMOTE | PROMOTE_WITH_CARRY | HOLD | REPAIR | REJECT
    receipt: PromotionReceipt | None
    quarantine: Quarantine | None
    qshrink_authorized: bool


def _canonical_digest(obj) -> str:
    return hashlib.sha256(
        json.dumps(obj, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def independent(C: Candidate) -> Clause:
    """
    Independent(W_verify, C).

    Mechanical: the verifier must not be the constructor, and must not share the
    constructor's channel.  This is the clause the corpus states in prose:
    a system 'cannot certify the COMPLETION of a loop it both generated and judged.'
    """
    if not C.verifier_id or not C.constructor_id:
        return Clause("verifier_independence", "UNKNOWN", True,
                      f"constructor={C.constructor_id!r} verifier={C.verifier_id!r} "
                      "- one or both NOT DECLARED")
    same_agent   = C.verifier_id == C.constructor_id
    same_channel = (C.verifier_channel or None) == (C.constructor_channel or None)
    if same_agent:
        return Clause("verifier_independence", "FAIL", True,
                      f"verifier_id == constructor_id == {C.verifier_id!r}: "
                      "the loop was generated and judged by one party")
    if same_channel:
        return Clause("verifier_independence", "FAIL", True,
                      f"distinct ids but shared channel {C.verifier_channel!r}")
    return Clause("verifier_independence", "PASS", True,
                  f"constructor={C.constructor_id} / verifier={C.verifier_id} "
                  f"on distinct channels")


def I10(C: Candidate) -> I10Result:
    # ---- gate ordering: I_{k+1} admissible only if I_1..I_k produced lawful packets
    receipts: list[GateReceipt] = []
    halted = False
    for g in GATES_1_9:
        if halted:
            gate = g.__name__
            gid, grid, role, _ = GATE_TABLE[gate]
            receipts.append(GateReceipt(gate, gid, grid, role, NOT_EVALUATED, [],
                                        "blocked by an earlier gate"))
            continue
        r = g(C)
        receipts.append(r)
        if r.verdict == "FAIL":
            halted = True   # ordering law; the candidate is not erased, only halted

    # ---- the promotable conjunction, clause by clause
    pc: list[Clause] = []
    passed_1_9 = [r for r in receipts if r.verdict == "PASS"]
    pc.append(Clause("all_nine_gates_PASS",
                     "PASS" if len(passed_1_9) == 9 else "FAIL", True,
                     f"{len(passed_1_9)}/9 gates PASS "
                     f"({[r.gate for r in receipts if r.verdict != 'PASS']} not PASS)"))

    unknown_hard = [f"{r.gate}.{c.name}" for r in receipts for c in r.unknown()]
    pc.append(Clause("UnknownHardClauses_empty",
                     "PASS" if not unknown_hard else "FAIL", True,
                     f"unknown hard clauses={unknown_hard}"))

    oos_hard = [f"{r.gate}.{c.name}" for r in receipts for c in r.oos()]
    pc.append(Clause("OutOfScopeRequiredClauses_empty",
                     "PASS" if not oos_hard else "FAIL", True,
                     f"out-of-scope required clauses={oos_hard}"))

    hard_debt = [d for d in C.defects
                 if d.get("severity") in ("S3", "S4") and d.get("status") != "REPAIRED"]
    pc.append(Clause("HardDebt_empty",
                     "PASS" if not hard_debt else "FAIL", True,
                     f"unrepaired S3/S4 defects={[d.get('id') for d in hard_debt]}"))

    pc.append(independent(C))

    pc.append(Clause("stewardship_allows",
                     "PASS" if C.sigma_S in ("ALLOW", "ALLOW_LIMITED") else "FAIL", True,
                     f"sigma_S={C.sigma_S}"))

    rw = [w for w in C.witnesses if w.get("kind") == "RETURN_WITNESS"]
    pc.append(Clause("ReturnWitness_nonempty",
                     "PASS" if rw else "FAIL", True,
                     f"return witnesses={len(rw)}"))

    promotable = all(c.verdict == "PASS" for c in pc if c.hard)

    # ---- sigma(C) is a VECTOR.  It is never compressed to a single token.
    sigma = (C.sigma_E, C.sigma_X, C.sigma_S,
             "PROMOTABLE" if promotable else C.sigma_P)

    # ---- verdict.  Promotable(C) != Promoted(C): promotion is an authority event.
    blocking = [c for c in pc if c.hard and c.verdict != "PASS"]
    if promotable:
        soft_residue = [d for d in C.defects if d.get("status") != "REPAIRED"]
        verdict = "PROMOTE_WITH_CARRY" if soft_residue else "PROMOTE"
    elif any(c.verdict == "FAIL" and c.name in
             ("verifier_independence", "stewardship_allows") for c in blocking):
        verdict = "REJECT"        # constitutional block, not a repairable defect
    elif unknown_hard:
        verdict = "HOLD"          # missing measurement, not proven failure
    else:
        verdict = "REPAIR"

    receipt = qz = None
    if verdict.startswith("PROMOTE"):
        body = {"candidate_id": C.candidate_id, "source_epoch": C.source_epoch,
                "gates": [asdict(r) for r in receipts], "sigma": sigma}
        receipt = PromotionReceipt(
            candidate_id=C.candidate_id, source_epoch=C.source_epoch,
            gate_receipts_1_9=[asdict(r) for r in receipts],
            authority=C.authority or {},
            claim_ceiling=(C.corridor or {}).get("claim_ceiling", []),
            residual_ledger=[d for d in C.defects if d.get("status") != "REPAIRED"],
            rollback_head=(C.q_contract or {}).get("rollback_head", "UNDECLARED"),
            successor_policy="APPEND_ONLY; supersession requires an explicit receipt",
            promotion_digest=_canonical_digest(body))
    else:
        qz = Quarantine(
            candidate_id=C.candidate_id,
            blocking_clauses=[asdict(c) for c in blocking],
            repair_routes=sorted({r.repair_route for r in receipts if r.repair_route}))

    return I10Result(C.candidate_id, receipts, sigma, promotable, pc, verdict,
                     receipt, qz, qshrink_authorized=verdict.startswith("PROMOTE"))


def qshrink(result: I10Result):
    """QSHRINK is FORBIDDEN_BEFORE_GID090 and operates only on a promoted C+."""
    if not result.qshrink_authorized:
        return {"status": "REFUSED",
                "reason": f"QSHRINK_FORBIDDEN: verdict={result.verdict}, "
                          "no promotion receipt exists",
                "law": "Compress(x) does not imply Promote(x); the converse ordering is binding"}
    return {"status": "AUTHORIZED",
            "packet": "(m, kappa, D, epsilon, S, R)",
            "acceptance": "lawful iff D(m,kappa) ~=_epsilon C+"}


# ---------------------------------------------------------------------------
# 5 - REPORT
# ---------------------------------------------------------------------------

def report(r: I10Result) -> str:
    L = []
    L.append(f"CANDIDATE :: {r.candidate_id}")
    L.append("-" * 78)
    for g in r.gate_receipts:
        mark = {"PASS": "PASS", "FAIL": "FAIL", "UNKNOWN": "UNKN",
                "OUT_OF_SCOPE": "OOS ", NOT_EVALUATED: "----"}[g.verdict]
        L.append(f"  [{mark}] {g.gate} GID{g.gid:03d} {g.grid}  {g.role}")
        for c in g.clauses:
            if c.verdict != "PASS":
                L.append(f"           - {c.name}: {c.verdict} :: {c.evidence}")
    L.append("-" * 78)
    L.append("  PROMOTABLE CONJUNCTION")
    for c in r.promotable_clauses:
        L.append(f"    [{c.verdict:4s}] {c.name}: {c.evidence}")
    L.append("-" * 78)
    L.append(f"  sigma(C) = <{r.sigma[0]}, {r.sigma[1]}, {r.sigma[2]}, {r.sigma[3]}>")
    L.append(f"  VERDICT  = {r.verdict}")
    if r.receipt:
        L.append(f"  Pi_C digest = {r.receipt.promotion_digest[:32]}...")
        L.append(f"  claim ceiling = {r.receipt.claim_ceiling}")
    if r.quarantine:
        L.append(f"  QUARANTINE :: {len(r.quarantine.blocking_clauses)} blocking clause(s); "
                 f"candidate preserved={r.quarantine.preserved}")
        for rr in r.quarantine.repair_routes:
            L.append(f"    repair -> {rr}")
    q = qshrink(r)
    L.append(f"  QSHRINK  = {q['status']}" + (f" :: {q.get('reason','')}"
                                              if q["status"] == "REFUSED" else ""))
    return "\n".join(L)
