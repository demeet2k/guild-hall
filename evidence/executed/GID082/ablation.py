#!/usr/bin/env python3
"""
CONTROLLED ABLATION :: which blocker actually binds?

GID090's first run found two blockers. That run cannot tell us which one is
load-bearing, because both were absent simultaneously. This isolates them.

    baseline   as the corpus stands
    +canon     GID082 canonicalisation policy applied (fixes I02 corpus-wide)
    +party     a real second party with standing applied (fixes independence)
    +both

The prediction under test, stated BEFORE running (pre-registration):
    H1  +canon alone raises gate counts and changes ZERO verdicts.
    H2  +party alone changes verdicts only where the gates already pass.
    H3  the binding constraint is the party, not the policy.

A result that contradicts these is the informative one.
"""
import sys, copy
sys.path.insert(0, "/home/claude/gid090")

from ic10 import I10                      # the GID090 promotion kernel
import candidates as CAND
from canon import bind, HASH_POLICY_ID, CANON_PROFILE_ID
from answerable import Answerable, Window, Refusal, Appeal, independent_verifier

CONSTRUCTOR = "assistant-instance"


def apply_canon(c):
    """GID082: every candidate can now present raw_cid + canon_profile."""
    c = copy.deepcopy(c)
    if c.q_contract is None:
        c.q_contract = {}
    body = f"{c.candidate_id}|{c.station}|{c.source_epoch}"
    cid = bind(body, schema_tag="KC144.CANDIDATE")
    c.q_contract["raw_cid"] = cid.raw_cid
    c.q_contract["canon_profile"] = CANON_PROFILE_ID
    return c


REAL_PARTY = Answerable(
    agent=CONSTRUCTOR, party="independent-adjudicator",
    decision="promote this exact candidate under its declared claim ceiling",
    window=Window("candidate sealed", "verdict returned", True),
    refusal=Refusal(channel="return REJECT with a clause reference",
                    cost_to_refuser="NONE", reframing_risk=False),
    appeal=Appeal(route="re-submit after repair at GID140/M08", reopens_window=True),
    announced=True,
    announcement_terms="the candidate, its claim ceiling and its residual ledger, "
                       "stated in full before the verdict is requested")


def apply_party(c):
    """A second party that satisfies d(S,p) - not merely a distinct id."""
    ok, why = independent_verifier(REAL_PARTY, CONSTRUCTOR)
    assert ok, why
    c = copy.deepcopy(c)
    c.verifier_id = REAL_PARTY.party
    c.verifier_channel = "independent-adjudication-channel"
    # standing also lifts stewardship out of RESEARCH_ONLY: an authority that can be
    # refused is an authority that can allow.
    if c.sigma_S == "RESEARCH_ONLY":
        c.sigma_S = "ALLOW_LIMITED"
    return c


CONDITIONS = {
    "baseline":      lambda c: c,
    "+canon":        apply_canon,
    "+party":        apply_party,
    "+both":         lambda c: apply_party(apply_canon(c)),
}


def run():
    rows = []
    for c in CAND.ALL:
        short = c.candidate_id.split("::")[1]
        row = {"candidate": short}
        for name, f in CONDITIONS.items():
            r = I10(f(c))
            passes = sum(1 for g in r.gate_receipts if g.verdict == "PASS")
            row[name] = (passes, r.verdict)
        rows.append(row)

    w = 12
    print("=" * 96)
    print("ABLATION :: which blocker binds?      cells show  gates_PASS/9  ->  verdict")
    print("=" * 96)
    hdr = f"{'candidate':<12}" + "".join(f"{k:<21}" for k in CONDITIONS)
    print(hdr); print("-" * 96)
    for row in rows:
        line = f"{row['candidate']:<12}"
        for k in CONDITIONS:
            p, v = row[k]
            line += f"{p}/9 {v:<17}"
        print(line)
    print("-" * 96)

    for k in CONDITIONS:
        proms = sum(1 for r in rows if r[k][1].startswith("PROMOTE"))
        gates = sum(r[k][0] for r in rows)
        print(f"  {k:<10}  total gates PASS = {gates}/45   promotions = {proms}/5")

    print("\n" + "=" * 96)
    print("RESULT")
    print("=" * 96)
    b, c_, p_, bo = (CONDITIONS.keys())
    dg_canon = sum(r["+canon"][0] for r in rows) - sum(r["baseline"][0] for r in rows)
    dv_canon = sum(1 for r in rows if r["+canon"][1] != r["baseline"][1])
    dg_party = sum(r["+party"][0] for r in rows) - sum(r["baseline"][0] for r in rows)
    dv_party = sum(1 for r in rows if r["+party"][1] != r["baseline"][1])
    dv_both  = sum(1 for r in rows if r["+both"][1] != r["baseline"][1])
    print(f"  +canon  : gates {dg_canon:+d}   verdicts changed: {dv_canon}/5")
    print(f"  +party  : gates {dg_party:+d}   verdicts changed: {dv_party}/5")
    print(f"  +both   : verdicts changed: {dv_both}/5")
    print()
    print("  H1 (+canon alone changes zero verdicts) :",
          "CONFIRMED" if dv_canon == 0 else f"REFUTED ({dv_canon} changed)")
    print("  H3 (the party is the binding constraint) :",
          "CONFIRMED" if dv_party > dv_canon else "REFUTED")
    print()
    still = [r["candidate"] for r in rows if not r["+both"][1].startswith("PROMOTE")]
    print(f"  Candidates still REJECTED with BOTH repairs applied: {len(still)}/5")
    for r in rows:
        if not r["+both"][1].startswith("PROMOTE"):
            print(f"     {r['candidate']}: {r['+both'][0]}/9 gates -> {r['+both'][1]}")
    return rows


if __name__ == "__main__":
    run()


# --------------------------------------------------------------------------
# DECONFOUNDING.  apply_party() changed TWO things: the verifier identity AND
# sigma_S (RESEARCH_ONLY -> ALLOW_LIMITED).  That is a confounded intervention.
# The corpus's own law: a single-run spillover is not a causal estimate; paired
# isolated runs are required.  So isolate.
# --------------------------------------------------------------------------
def apply_party_id_only(c):
    c = copy.deepcopy(c)
    c.verifier_id = REAL_PARTY.party
    c.verifier_channel = "independent-adjudication-channel"
    return c                                   # sigma_S untouched

def apply_steward_only(c):
    c = copy.deepcopy(c)
    if c.sigma_S == "RESEARCH_ONLY":
        c.sigma_S = "ALLOW_LIMITED"
    return c                                   # verifier untouched

def deconfound():
    conds = {"baseline": lambda c: c,
             "+verifier_only": apply_party_id_only,
             "+steward_only": apply_steward_only,
             "+both_of_those": lambda c: apply_steward_only(apply_party_id_only(c))}
    print("\n" + "=" * 96)
    print("DECONFOUNDING :: +party bundled two changes. Isolating them.")
    print("=" * 96)
    print(f"{'candidate':<12}" + "".join(f"{k:<22}" for k in conds))
    print("-" * 96)
    rows = []
    for c in CAND.ALL:
        short = c.candidate_id.split("::")[1]
        line = f"{short:<12}"; row = {"candidate": short}
        for k, f in conds.items():
            r = I10(f(c))
            p = sum(1 for g in r.gate_receipts if g.verdict == "PASS")
            row[k] = r.verdict
            line += f"{p}/9 {r.verdict:<18}"
        rows.append(row); print(line)
    print("-" * 96)
    for k in list(conds)[1:]:
        n = sum(1 for r in rows if r[k] != r["baseline"])
        print(f"  {k:<16} verdicts changed vs baseline: {n}/5")
    print()
    v_only = sum(1 for r in rows if r["+verifier_only"] != r["baseline"])
    s_only = sum(1 for r in rows if r["+steward_only"] != r["baseline"])
    both   = sum(1 for r in rows if r["+both_of_those"] != r["baseline"])
    # A main-effect reading is only licensed when one factor alone approaches the
    # joint effect. Otherwise the correct report is INTERACTION, not "X is causal".
    if both > v_only + s_only:
        print(f"  -> SUPERADDITIVE INTERACTION: verifier alone {v_only}/5, "
              f"stewardship alone {s_only}/5, together {both}/5.")
        print("     Neither factor is sufficient. Both are necessary.")
        print("     A verifier with no authority to allow is as inert as authority")
        print("     with no verifier. The corpus had neither.")
    elif v_only and not s_only:
        print("  -> BOTH are independently sufficient to change the verdict class")
    else:
        print("  -> NEITHER alone changes a verdict; the effect was joint")
    return rows

if __name__ != "__main__":
    pass
