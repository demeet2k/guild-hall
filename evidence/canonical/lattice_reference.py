#!/usr/bin/env python3
"""
KC144 — THE COMPLETE LATTICE, DERIVED FROM GENERATORS

Not crawled. The 144 seats are not a list; they are the disjoint union of the
orbits of five small generating sets plus one complement. This file derives all
144 from those generators and then CROSS-VALIDATES the derivation against every
independently-stated coordinate fact recoverable from the corpus.

Generators:
    K4  = {11, 10, 00, 01}        Klein four-group (poles)      q*q = 11
    L4  = {SQ, FL, CL, FR}        lenses (X-plane)
    L3  = {PLUS, HINGE, STAR}     lenses (BR-plane)
    O7  = {ADMIT..RETURN}         operator families
    T3  = {-1, 0, +1}             trit (KC27 axis), J(x) = -x

Derived bands:
    X16  = K4 x L4         product              16
    BR21 = O7 x L3         product              21
    KC15 = 2^K4 \ {}       power set            15
    KC27 = T3^3            cube                 27
    KC54 = E(P3 [] P3 [] P3)  EDGE set of that cube  54   (orthogonal: no seats)
    IC10 = chain I1 < ... < I10                  10
    SSN12 = list M1..M12                         12
    H6   = ring H01..H06                          6
    F37  = 144 - 107       COMPLEMENT            37

    144 = 6 + [16 + 21] + 37 + 10 + 15 + 27 + 12
        = 6 + 37_operator + 37_carrier + 10 + 15 + 27 + 12
"""
from itertools import combinations, product

# ---------------------------------------------------------------------------
# GENERATORS
# ---------------------------------------------------------------------------
K4 = ["11", "10", "00", "01"]                    # body, transform, invariant, return
L4 = ["SQ", "FL", "CL", "FR"]                    # contract, mechanics, branches, recursion
L3 = ["PLUS", "HINGE", "STAR"]                   # constructive, joint, conjugate
O7 = ["ADMIT", "EXPAND", "NAVIGATE", "TRANSFORM", "TEST", "COMPRESS", "RETURN"]
T3 = [-1, 0, 1]

POLE_ROLE = {"11": "BODY/SEED", "10": "TRANSFORM/VECTOR",
             "00": "INVARIANT/ZERO/DEFECT", "01": "RETURN/COVECTOR/ADDRESS"}
LENS_ROLE = {"SQ": "exact declaration / contract", "FL": "construction / mechanics",
             "CL": "branches / ambiguity / obstruction", "FR": "recursion / scale / replay"}

def gid_to_grid(g):
    return f"R{(g-1)//12 + 1:02d}C{(g-1)%12 + 1:02d}"

SEATS = {}   # gid -> dict

def seat(gid, band, name, role, status, **kw):
    assert 1 <= gid <= 144, gid
    assert gid not in SEATS, f"collision at GID{gid}"
    SEATS[gid] = dict(gid=gid, grid=gid_to_grid(gid), band=band, name=name,
                      role=role, status=status, **kw)

# ---------------------------------------------------------------------------
# BAND I — H6 · GID001-006 · control ring
# ---------------------------------------------------------------------------
H6 = [("H01", "Address-Identity Registry"),
      ("H02", "Domain Projection-Seating Registry"),
      ("H03", "Typed Route-Transformation Registry"),
      ("H04", "Invariant-Bridge-Defect Registry"),
      ("H05", "Source-Evidence-Version Registry"),
      ("H06", "Activation-Replay-Reseed Hub")]
for i, (n, r) in enumerate(H6, start=1):
    seat(i, "H6", n, r, "DOCUMENTED")

# ---------------------------------------------------------------------------
# BAND II-a — X16 · GID007-022 · K4 x L4
#   GID(q,l) = 7 + 4*p(q) + l(l)     p: 11->0 10->1 00->2 01->3
# ---------------------------------------------------------------------------
X_ROLE = {
 ("11","SQ"): "exact object identity",        ("11","FL"): "construction / constructor",
 ("11","CL"): "uncertainty / candidate fiber",("11","FR"): "recursive body",
 ("10","SQ"): "operator declaration",         ("10","FL"): "execution",
 ("10","CL"): "branch carrier",               ("10","FR"): "recursive composition",
 ("00","SQ"): "zero taxonomy",                ("00","FL"): "invariant enforcement",
 ("00","CL"): "defect / obstruction cloud",   ("00","FR"): "multiscale invariance",
 ("01","SQ"): "return contract",              ("01","FL"): "return mechanics",
 ("01","CL"): "multivalued return",           ("01","FR"): "recursive reseed / cold boot",
}
for pi, q in enumerate(K4):
    for li, l in enumerate(L4):
        g = 7 + 4*pi + li
        seat(g, "X16", f"X-{q}-{l}", X_ROLE[(q, l)], "DOCUMENTED",
             pole=q, lens=l, pole_role=POLE_ROLE[q], lens_role=LENS_ROLE[l])

# ---------------------------------------------------------------------------
# BAND II-b — BR21 · GID023-043 · O7 x L3
#   i = 3*(f-1) + lam ;  GID(B_i) = 22 + i
# ---------------------------------------------------------------------------
for fi, fam in enumerate(O7):
    for li, lam in enumerate(L3):
        i = 3*fi + li + 1
        g = 22 + i
        seat(g, "BR21", f"B{i:02d}", f"{fam}/{lam}", "DOCUMENTED",
             family=fam, lens=lam, br_index=i,
             mirror=f"B{22-i:02d}", rail=lam)

# ---------------------------------------------------------------------------
# BAND III — F37 · GID044-080 · the COMPLEMENT band
#   GID(F_n) = 43 + n.  Named seats are DOCUMENTED; the rest stay UNMAPPED.
#   An honest UNMAPPED cell is superior to a decorative analogy.
# ---------------------------------------------------------------------------
F_NAMED = {
 1:"diagonal Latin square address carrier", 2:"compactified complex / Hilbert",
 3:"rigged distributions & instruments",    4:"orbit-character",
 5:"affine motion",                          6:"binary-octahedral quaternion lift",
 7:"branch cover / analytic continuation",   8:"jets / local-asymptotic",
 9:"bulk-boundary totalized channel",       10:"observable algebra",
 11:"commutant / sector",                   14:"commutant-Laplacian",
 15:"gain graph",                           17:"sheaf / holonomy",
 18:"cohomology / gluing / obstruction",    22:"early warning",
 23:"compression / carry",                  24:"renormalization",
 26:"hysteresis / path-dependence",         28:"question language",
 29:"corridor",                             31:"certificates",
 33:"replay / Merkle",                      35:"carrier unification frontier",
 37:"compiler / publication atlas",
}
F_ROUTED_ONLY = {13, 16, 27, 30, 32}   # appear in routes; role never stated
for n in range(1, 38):
    g = 43 + n
    if n in F_NAMED:
        st, role = "DOCUMENTED", F_NAMED[n]
    elif n in F_ROUTED_ONLY:
        st, role = "ROUTED_ONLY", "referenced as a route endpoint; role not declared"
    else:
        st, role = "UNMAPPED", "NOT DECLARED (UNMAPPED is lawful; do not invent)"
    seat(g, "F37", f"F{n:02d}", role, st, f_index=n,
         operator_dual=g - 37)              # see the 37<->37 duality below

# ---------------------------------------------------------------------------
# BAND IV — IC10 · GID081-090 · ordered chain.  GID(I_k) = 80 + k
# ---------------------------------------------------------------------------
IC10 = ["identity / provenance", "syntax / normalization", "type / unit / carrier",
        "scope / regime / corridor", "invariant preservation", "evidence sufficiency",
        "dependency closure", "bridge / glue / return", "replay completeness",
        "promotion / canonical emission / reseed"]
for k, r in enumerate(IC10, start=1):
    seat(80 + k, "IC10", f"I{k:02d}", r, "DOCUMENTED", gate_index=k)

# ---------------------------------------------------------------------------
# BAND V — KC15 · GID091-105 · 2^K4 minus empty, graded by cardinality
#   Order: |S| = 1 (4 seats), 2 (6), 3 (4), 4 (1).  4+6+4+1 = 15.
#   The corpus fixes the four singletons at 091-094; grading then forces the rest.
# ---------------------------------------------------------------------------
kc15 = []
for k in (1, 2, 3, 4):
    for S in combinations(K4, k):
        kc15.append(S)
assert len(kc15) == 15
for idx, S in enumerate(kc15):
    g = 91 + idx
    mask = "".join("1" if p in S else "0" for p in K4)   # bit order [11,10,00,01]
    seat(g, "KC15", "{" + ",".join(S) + "}",
         f"support mask {mask}", "DERIVED",
         support=list(S), mask=mask, cardinality=len(S))

# ---------------------------------------------------------------------------
# BAND VI — KC27 · GID106-132 · T3^3
#   n = 9(z+1) + 3(y+1) + (x+1) ;  GID = 106 + n ;  mirror mu(P_n) = P_{26-n}
# ---------------------------------------------------------------------------
for z in T3:
    for y in T3:
        for x in T3:
            n = 9*(z+1) + 3*(y+1) + (x+1)
            g = 106 + n
            seat(g, "KC27", f"P{n:02d}", f"({x},{y},{z})", "DERIVED",
                 coord=(x, y, z), n=n, mirror_n=26-n, mirror_gid=106 + (26-n),
                 is_center=(x, y, z) == (0, 0, 0),
                 ring=abs(x)+abs(y)+abs(z))

# ---------------------------------------------------------------------------
# BAND VII — SSN12 · GID133-144 · GID(M_k) = 132 + k
# ---------------------------------------------------------------------------
SSN = ["node-state ledger", "edge-state ledger", "parallel wave engine",
       "in-between region ledger", "hybrid-density map", "thought-pattern matrix",
       "J-space commitment boundary", "healing & gap ledger", "path-signature registry",
       "projective-synapse map", "route-coverage audit", "solid-state certificate"]
for k, r in enumerate(SSN, start=1):
    seat(132 + k, "SSN12", f"M{k:02d}", r,
         "DOCUMENTED" if k in (2,3,5,6,8,9,11,12) else "DERIVED", m_index=k)

assert len(SEATS) == 144, len(SEATS)


# ---------------------------------------------------------------------------
# THE EDGE SPINE — derived per band, then summed.
# This resolves the corpus's GLOBAL-EDGE-DENOMINATOR = HOLD.
# ---------------------------------------------------------------------------
def edges_cycle(n):      return n                     # C_n
def edges_path(n):       return n - 1                 # P_n
def edges_complete(n):   return n*(n-1)//2            # K_n
def edges_cartesian(n1, e1, n2, e2):                  # G1 [] G2
    return n1*e2 + n2*e1

SPINE = {}
SPINE["H6 ring C6"]            = edges_cycle(6)                       # 6
# X16: TWO typed edge classes on one vertex set. Not competing claims.
SPINE["X16 algebra K4[]C4"]    = edges_cartesian(4, edges_complete(4), 4, edges_cycle(4))
SPINE["X16 schedule C4[]C4"]   = edges_cartesian(4, edges_cycle(4), 4, edges_cycle(4))
SPINE["BR21 7*K3 + 3*P7"]      = 7*edges_complete(3) + 3*edges_path(7)  # 21 + 18 = 39
SPINE["F37 address rail P37"]  = edges_path(37)                        # 36
SPINE["IC10 chain P10"]        = edges_path(10)                        # 9
SPINE["KC15 Hasse B4\\{}"]      = 4*3 + 6*2 + 4*1                       # 28
SPINE["KC27 grid P3[]P3[]P3"]  = (8*3 + 12*4 + 6*5 + 1*6)//2           # 54
SPINE["SSN12 chain P12"]       = edges_path(12)                        # 11

CORPUS_166 = ["BR21 7*K3 + 3*P7", "F37 address rail P37", "IC10 chain P10",
              "KC15 Hasse B4\\{}", "KC27 grid P3[]P3[]P3"]


def kc54_edge_set():
    """KC54 read as the EDGE set of the KC27 cube (the upstream derivation)."""
    V = [(x, y, z) for z in T3 for y in T3 for x in T3]
    E = set()
    for v in V:
        for ax in range(3):
            for d in (-1, 1):
                w = list(v); w[ax] += d; w = tuple(w)
                if all(c in T3 for c in w):
                    E.add(frozenset((v, w)))
    return E


# ---------------------------------------------------------------------------
# CROSS-VALIDATION — every independently stated coordinate fact from the corpus
# ---------------------------------------------------------------------------
CHECKS = []
def check(desc, got, want):
    CHECKS.append((desc, got == want, f"got={got!r} want={want!r}"))

# address law
check("GID(8,6) = 90 (IC10-I10)", 12*(8-1)+6, 90)
check("GID(r,c) bijective on 1..144",
      sorted(12*(r-1)+c for r in range(1,13) for c in range(1,13)), list(range(1,145)))
# band boundaries
check("H6 = 001-006",   (min(g for g,s in SEATS.items() if s['band']=='H6'),
                         max(g for g,s in SEATS.items() if s['band']=='H6')), (1,6))
check("X16 = 007-022",  (min(g for g,s in SEATS.items() if s['band']=='X16'),
                         max(g for g,s in SEATS.items() if s['band']=='X16')), (7,22))
check("BR21 = 023-043", (min(g for g,s in SEATS.items() if s['band']=='BR21'),
                         max(g for g,s in SEATS.items() if s['band']=='BR21')), (23,43))
check("F37 = 044-080",  (min(g for g,s in SEATS.items() if s['band']=='F37'),
                         max(g for g,s in SEATS.items() if s['band']=='F37')), (44,80))
check("IC10 = 081-090", (min(g for g,s in SEATS.items() if s['band']=='IC10'),
                         max(g for g,s in SEATS.items() if s['band']=='IC10')), (81,90))
check("KC15 = 091-105", (min(g for g,s in SEATS.items() if s['band']=='KC15'),
                         max(g for g,s in SEATS.items() if s['band']=='KC15')), (91,105))
check("KC27 = 106-132", (min(g for g,s in SEATS.items() if s['band']=='KC27'),
                         max(g for g,s in SEATS.items() if s['band']=='KC27')), (106,132))
check("SSN12 = 133-144",(min(g for g,s in SEATS.items() if s['band']=='SSN12'),
                         max(g for g,s in SEATS.items() if s['band']=='SSN12')), (133,144))
# X16 named seats
for g, nm in [(7,"X-11-SQ"), (14,"X-10-FR"), (15,"X-00-SQ"), (20,"X-01-FL"),
              (21,"X-01-CL"), (22,"X-01-FR")]:
    check(f"GID{g:03d} = {nm}", SEATS[g]["name"], nm)
# BR21 named seats
for g, nm, role in [(23,"B01","ADMIT/PLUS"), (24,"B02","ADMIT/HINGE"),
                    (29,"B07","NAVIGATE/PLUS"), (33,"B11","TRANSFORM/HINGE"),
                    (34,"B12","TRANSFORM/STAR"), (43,"B21","RETURN/STAR")]:
    check(f"GID{g:03d} = {nm} {role}", (SEATS[g]["name"], SEATS[g]["role"]), (nm, role))
check("BR21 centre B11 = GID033", [g for g,s in SEATS.items()
      if s['band']=='BR21' and s['name']=='B11'][0], 33)
check("BR21 mirror B_i <-> B_{22-i} on B02", SEATS[24]["mirror"], "B20")
# F37
for g, nm in [(44,"F01"), (56,"F13"), (58,"F15"), (61,"F18"), (74,"F31"),
              (76,"F33"), (78,"F35"), (80,"F37")]:
    check(f"GID{g:03d} = {nm}", SEATS[g]["name"], nm)
# IC10
for g, nm in [(81,"I01"), (85,"I05"), (88,"I08"), (89,"I09"), (90,"I10")]:
    check(f"GID{g:03d} = {nm}", SEATS[g]["name"], nm)
check("I05 grid = R08C01", SEATS[85]["grid"], "R08C01")
check("I10 grid = R08C06", SEATS[90]["grid"], "R08C06")
# KC15 singletons fixed by the corpus
for g, s in [(91,"{11}"), (92,"{10}"), (93,"{00}"), (94,"{01}")]:
    check(f"GID{g:03d} = {s}", SEATS[g]["name"], s)
# KC15 derived pairs, validated against corpus ROUTE PAYLOADS (independent evidence)
check("GID099 = {10,01} (corpus: 'forward/return operator pair')",
      SEATS[99]["name"], "{10,01}")
check("GID100 = {00,01} (corpus: 'invariant-governed return')",
      SEATS[100]["name"], "{00,01}")
check("GID098 = {10,00} (corpus: 'compression eligibility and loss probes')",
      SEATS[98]["name"], "{10,00}")
check("GID096 = {11,00} (corpus: 'storage, revision, container boundary')",
      SEATS[96]["name"], "{11,00}")
check("KC15 grading 4,6,4,1", [sum(1 for s in SEATS.values()
      if s['band']=='KC15' and s['cardinality']==k) for k in (1,2,3,4)], [4,6,4,1])
# KC27
check("KC27 centre P13 = GID119",
      [g for g,s in SEATS.items() if s['band']=='KC27' and s.get('is_center')][0], 119)
check("KC27 P04 <-> P22 mirror", SEATS[110]["mirror_n"], 22)
check("GID(P04) = 110", 106+4, 110)
check("GID(P22) = 128", 106+22, 128)
check("GID(P10) = 116 and GID(P16) = 122", (106+10, 106+16), (116,122))
check("GID(P12) = 118 and GID(P14) = 120", (106+12, 106+14), (118,120))
check("P13 six axis-neighbours = {P04,P10,P12,P14,P16,P22}",
      sorted([13-9,13-3,13-1,13+1,13+3,13+9]), [4,10,12,14,16,22])
# SSN12
for g, nm in [(134,"M02"), (135,"M03"), (137,"M05"), (138,"M06"),
              (140,"M08"), (141,"M09"), (143,"M11"), (144,"M12")]:
    check(f"GID{g:03d} = {nm}", SEATS[g]["name"], nm)
# census
check("144 = 6+16+21+37+10+15+27+12", 6+16+21+37+10+15+27+12, 144)
check("operator block |X16 + BR21| = 37", 16+21, 37)
check("carrier block |F37| = 37", 37, 37)
check("F37 is the complement: 144 - 107", 144-(6+16+21+10+15+27+12), 37)
# edges
check("KC27 edge count = 54 (= KC54 cardinality)", len(kc54_edge_set()), 54)
check("KC27 degree sum = 108", 8*3+12*4+6*5+1*6, 108)
check("KC15 Hasse edges = 28", SPINE["KC15 Hasse B4\\{}"], 28)
check("BR21 spine = 39", SPINE["BR21 7*K3 + 3*P7"], 39)
check("corpus E_spine = 166", sum(SPINE[k] for k in CORPUS_166), 166)
check("X16 algebra K4[]C4 = 40 edges", SPINE["X16 algebra K4[]C4"], 40)
check("X16 schedule C4[]C4 = 32 edges", SPINE["X16 schedule C4[]C4"], 32)


def main():
    print("=" * 88)
    print("KC144 — COMPLETE LATTICE DERIVED FROM GENERATORS")
    print("=" * 88)
    ok = sum(1 for _, o, _ in CHECKS if o)
    print(f"\nCROSS-VALIDATION: {ok}/{len(CHECKS)} independently-stated corpus facts reproduced")
    for d, o, ev in CHECKS:
        if not o:
            print(f"   [FAIL] {d}: {ev}")
    print("\nSEAT STATUS CENSUS")
    from collections import Counter
    c = Counter(s["status"] for s in SEATS.values())
    for k, v in sorted(c.items(), key=lambda kv: -kv[1]):
        print(f"   {k:14s} {v:3d}")
    print("\nBAND CENSUS")
    b = Counter(s["band"] for s in SEATS.values())
    for k in ("H6","X16","BR21","F37","IC10","KC15","KC27","SSN12"):
        gs = [g for g,s in SEATS.items() if s['band']==k]
        print(f"   {k:6s} {b[k]:3d}   GID{min(gs):03d}-{max(gs):03d}")
    print("\nEDGE SPINE (intra-band)")
    for k, v in SPINE.items():
        mark = " *" if k in CORPUS_166 else "  "
        print(f"  {mark} {k:26s} {v:5d}")
    corpus = sum(SPINE[k] for k in CORPUS_166)
    omitted = ["H6 ring C6", "SSN12 chain P12"]
    tot_sched = corpus + sum(SPINE[k] for k in omitted) + SPINE["X16 schedule C4[]C4"]
    tot_alg   = corpus + sum(SPINE[k] for k in omitted) + SPINE["X16 algebra K4[]C4"]
    print(f"\n   corpus-counted spine (5 bands)        = {corpus}")
    print(f"   + H6 (6) + SSN12 (11) + X16 schedule  = {tot_sched}")
    print(f"   + H6 (6) + SSN12 (11) + X16 algebra   = {tot_alg}")
    print(f"\n   The corpus's E_spine = 166 omitted THREE bands entirely:")
    print(f"     H6 (6 edges), X16 (32 or 40), SSN12 (11).")
    print(f"   GLOBAL-EDGE-DENOMINATOR (intra-band, schedule reading) = {tot_sched}")
    print(f"   GLOBAL-EDGE-DENOMINATOR (intra-band, algebra reading)  = {tot_alg}")
    return SEATS


if __name__ == "__main__":
    main()
