#!/usr/bin/env python3
"""
Real IC10 candidates, built only from what the corpus ACTUALLY DECLARES.

Rule applied throughout: a field the corpus does not declare is None (= UNKNOWN),
never a fabricated value. UNKNOWN != 0. An honest UNMAPPED cell beats a decorative one.

Sources are the persisted raw texts in /home/claude/corpus/.
"""
from ic10 import Candidate

# The constructor of every station body in this corpus is one assistant instance
# working with one user in one channel. Recorded, not assumed.
CONSTRUCTOR = "assistant-instance"
CHANNEL     = "kc144-construction-threads"


# --------------------------------------------------------------------------
# 1. GID020 / X-01-FL - RETURN MECHANICS
#    The corpus's own strongest promotion claim. From KC144 :: 6-, GID020/P07:
#      "IC10_VERDICT::PROMOTE"
#      "PROMOTED_CLAIM::GID020 IS THE CANONICAL CONSTRUCTIVE RETURN/DECODER/
#       RECONSTRUCTION FLOWER"
#      "NOT_PROMOTED::UNIVERSAL REVERSIBILITY OF DOMAIN TRANSFORMATIONS"
# --------------------------------------------------------------------------
GID020 = Candidate(
    candidate_id="KC144.V2::GID020::X-01-FL::RETURN_MECHANICS::P07",
    source_epoch="KC144.V1",
    station="GID020",
    r_plus={
        "carrier": "typed return object Omega_R (24 fields)",
        "type": "ReturnObligation",
        "return_class": "DECODER",
        "loss_manifest": ["null-space loss", "structural loss", "provenance loss"],
        "invariants": [
            {"name": "coordinate_and_role_do_not_migrate",
             "transport": "identity on the KC144 address map",
             "witness": "GID020/P00 coordinate lock, R02C08"},
            {"name": "return_class_ceiling",
             "transport": "DeclaredReturnClass <= WitnessedReturnClass",
             "witness": "GID020/P06 conjugate audit"},
        ],
    },
    r_hinge={
        "carrier": "pass sequence P00-P07",
        "type": "ProcessReturn",
        "return_class": "PARTIAL_INVERSE",
        "loss_manifest": ["version migrations deferred to GID021/GID022/GID140"],
        "replay_packet": None,          # corpus declares no executable replay packet
    },
    r_star={
        "carrier": "KC54 duplex audit record",
        "type": "ConjugateReturn",
        "return_class": "COMPENSATING_RETURN",
        "loss_manifest": ["non-GID020 recursive reseed work"],
        "open_bridges": ["universal reversibility of domain transformations"],
    },
    q_contract={
        "goal": "canonical constructive return / decoder / reconstruction flower",
        "raw_cid": None, "canon_profile": None,        # no hash policy admitted
        "dependencies": [
            {"id": "GID019 return contract", "status": "CLOSED"},
            {"id": "GID021 multivalued return", "status": "OPEN"},
            {"id": "GID022 recursive reseed",   "status": "OPEN"},
        ],
        "rollback_head": None,
    },
    corridor={
        "membership_test": "station harness scope: KC144 return mechanics",
        "claim_ceiling": ["NOT universal reversibility of domain transformations"],
    },
    witnesses=[
        {"kind": "STRUCTURAL", "evidence_class": "B",
         "ref": "GID020/P07 28 numbered sections + node card"},
        {"kind": "RETURN_WITNESS", "evidence_class": "B",
         "ref": "GID020/P07 four-pole closure 11/10/00/01"},
    ],
    defects=[
        {"id": "RESIDUE.GID020.01", "severity": "S1", "status": "ROUTED",
         "note": "version migrations -> GID021/GID022/GID140; NONBLOCKING_FOR_PROMOTION"},
    ],
    provenance=[
        {"title": "KC144 :: 6-", "locator": "1mgypuOKGbTMvdNnUtdn-b8kD45Y3PP_Z6yxivmJOE_I",
         "evidence_class": "A"},
    ],
    authority={"issued_by": "GID020/P07 self-declaration",
               "note": "declared before any I10 existed"},
    sigma_E="SUPPORTED", sigma_X="PASS", sigma_S="RESEARCH_ONLY", sigma_P="TESTED",
    delta_return={},                                   # never measured
    constructor_id=CONSTRUCTOR, verifier_id=CONSTRUCTOR,
    constructor_channel=CHANNEL, verifier_channel=CHANNEL,
    notes="The corpus declared IC10_VERDICT::PROMOTE here with no I10 in existence.",
)


# --------------------------------------------------------------------------
# 2. GID044 / F01 - DIAGONAL LATIN SQUARE ADDRESS CARRIER
#    The one candidate carrying a finite, exhaustively checkable claim:
#      "#D_{4,top=1234} = 2"  over 24^3 = 13,824 ordered row triples.
#    Re-executed independently in verify_f01.py -> a MEASURED witness.
# --------------------------------------------------------------------------
GID044 = Candidate(
    candidate_id="KC144.V2::GID044::F01::DLS_ADDRESS_CARRIER::P07",
    source_epoch="KC144.V1",
    station="GID044",
    r_plus={
        "carrier": "diagonal Latin squares of order 4^m, seeds D^A and D^B",
        "type": "AddressCarrier",
        "return_class": "EXACT_INVERSE",
        "loss_manifest": ["symbol-only decoding is SET_VALUED; the typed locator "
                          "a = <m,r,c,s,p,chi,rho> is required for exact return"],
        "invariants": [
            {"name": "lift_preserves_latin_and_diagonal_property",
             "transport": "L^chi_{4^{m+1}}(4r+a,4c+b) = 4(L^chi_{4^m}(r,c)-1)+D^chi_{ab}",
             "witness": "exhaustive check, m=1,2 (verify_f01.py)"},
            {"name": "seed_count_top_row_1234_is_exactly_2",
             "transport": "enumeration over 24^3 ordered row triples",
             "witness": "verify_f01.py, independently re-executed"},
        ],
    },
    r_hinge={
        "carrier": "recursive digit expansion",
        "type": "ProcessReturn",
        "return_class": "EXACT_INVERSE",
        "loss_manifest": [],
        "replay_packet": {
            "inputs": "D^A, D^B, depth m",
            "addresses": "GID044/R04C08",
            "atlas_version": "KC144.V2",
            "operations": "block lift + digit expansion",
            "route_order": "P00..P07",
            "policies": "no A/B merge without a typed isomorphism",
            "seeds": "top row 1234 normalization",
            "decoder": "DecRow(r,s)=c ; DecColumn(c,s)=r",
            "expected_result": "#D_{4,top=1234}=2 ; L_{4^m} Latin and diagonal for all m>=1",
            "executed": True,
            "boot_class": "B4",   # independent re-derivation from the declared rule,
                                  # not a retrieval of the stored answer
        },
    },
    r_star={
        "carrier": "presentation counting",
        "type": "ConjugateReturn",
        "return_class": "SET_VALUED_RETURN",
        "loss_manifest": ["192 is a PRESENTATION count, not a count of "
                          "non-isomorphic DLS structures"],
        "open_bridges": [],
    },
    q_contract={
        "goal": "deterministic recursive address carrier for KC144",
        "raw_cid": "seed matrices given literally in KC144 :: 9-",
        "canon_profile": "top-row-1234 normalization",
        "dependencies": [
            {"id": "GID041 address handoff", "status": "CLOSED"},
        ],
        "rollback_head": "GID044/P06",
    },
    corridor={
        "membership_test": "finite: orders 4^m, m in {1,2,3}; verified m in {1,2}",
        "claim_ceiling": [
            "NOT a claim about DLS structures of order != 4^m",
            "NOT 192 non-isomorphic structures - 192 is a presentation count",
            "symbol alone is NOT a unique cell address",
        ],
    },
    witnesses=[
        {"kind": "MEASURED", "evidence_class": "MEASURED",
         "ref": "verify_f01.py exhaustive enumeration, this session"},
        {"kind": "RETURN_WITNESS", "evidence_class": "MEASURED",
         "ref": "round-trip Enc/Dec over all cells, m=1,2"},
        {"kind": "STRUCTURAL", "evidence_class": "A",
         "ref": "KC144 :: 9- GID044/P00-P07"},
    ],
    defects=[
        # Self-audit, entered against the interest of this candidate.
        # The enumerator was written by the same party that submits the candidate.
        # Its OUTPUT does not depend on that party's assessment (counting qualifies
        # under the harness law), and it is re-runnable by anyone. But "mechanically
        # re-derivable by a third party" is weaker than "was re-derived by a third
        # party". That gap is a residual, not nothing.
        {"id": "RESIDUE.GID044.VERIFIER", "severity": "S2", "status": "OPEN",
         "note": "verifier code authored by the constructing party; independence is "
                 "of the re-derivability kind, not the executed-by-a-third-party kind. "
                 "Falsifiable by re-running verify_f01.py under any other implementation."},
    ],
    provenance=[
        {"title": "KC144 :: 9-", "locator": "1_SxGGqIQYeQyoYfaToPTnb9U5-7wcJ6wVcG-toY3dkg",
         "evidence_class": "A"},
        {"title": "144 posts - crystal", "locator": "1Ct84ETWyBLa9uBXkmsJBBrLSQ6nzVIz_NSBDlph_kA4",
         "evidence_class": "A"},
    ],
    authority={"issued_by": "GID044/P07 closure", "stewardship": "RESEARCH_ONLY"},
    sigma_E="EXACT", sigma_X="PASS", sigma_S="ALLOW_LIMITED", sigma_P="TESTED",
    delta_return={"id": 0, "source": 0, "authority": 0,
                  "sem": 0, "route": 0, "branch": 0, "time": 0},
    constructor_id=CONSTRUCTOR, verifier_id="external-execution-this-session",
    constructor_channel=CHANNEL, verifier_channel="python-runtime",
    notes="The only corpus claim that is finite, stated exactly, and re-executable.",
)


# --------------------------------------------------------------------------
# 3. GID043 / B21 - RETURN / STAR.  Reopened past its own P07 with P08-P10.
#    "ClosedSchema(GID043)=PASS but RuntimeCertified(GID043)=UNTESTED"
#    "IC10_PROMOTION::NOT_REQUESTED"
# --------------------------------------------------------------------------
GID043 = Candidate(
    candidate_id="KC144.V2::GID043::B21::RETURN_STAR::P10",
    source_epoch="KC144.V2",
    station="GID043",
    r_plus={"carrier": "R* bundle <v0,P,vn,P^-1,B,U,W,Delta,status>",
            "type": "ConjugateReturnBundle", "return_class": "SET_VALUED_RETURN",
            "loss_manifest": ["route-changing successors carry a new PathID"],
            "invariants": [{"name": "no_failed_path_is_deleted",
                            "transport": "FailedRouteRegistry inclusion",
                            "witness": "GID043/P07 registry"}]},
    r_hinge={"carrier": "event-sourced runtime S_t", "type": "ProcessReturn",
             "return_class": "REPLAY" if False else "PARTIAL_INVERSE",
             "loss_manifest": [],
             "replay_packet": {"inputs": "28-symbol event alphabet",
                               "addresses": "GID043/R04C07", "atlas_version": "KC144.V2",
                               "operations": "Apply(S_t,a_t)", "route_order": "P08 runtime",
                               "policies": "append-only", "seeds": None,
                               "decoder": None, "expected_result": None,
                               "executed": False, "boot_class": None}},
    r_star={"carrier": "obstruction record", "type": "ConjugateReturn",
            "return_class": "IMPOSSIBLE_RETURN",
            "loss_manifest": ["irreversibility certified where proven"],
            "open_bridges": ["RUNTIME_ROUTE_INSTANCE", "ACTUAL_STAR_RAIL_RUNTIME_INSTANCE"]},
    q_contract={"goal": "conjugate return terminus of the BR21 circuit",
                "raw_cid": None, "canon_profile": None,
                "dependencies": [{"id": "runtime edge receipts", "status": "OPEN"},
                                 {"id": "GID141/M09 path signature", "status": "OPEN"}],
                "rollback_head": None},
    corridor={"membership_test": "BR21 star rail, schema scope only",
              "claim_ceiling": ["schema closed; runtime UNCERTIFIED"]},
    witnesses=[{"kind": "STRUCTURAL", "evidence_class": "B", "ref": "GID043/P07 schema"},
               {"kind": "RETURN_WITNESS", "evidence_class": "B", "ref": "GID043/P09 holographic unit"}],
    defects=[{"id": "D.GID043.RUNTIME", "severity": "S3", "status": "OPEN",
              "note": "RuntimeCertified=UNTESTED; no bound runtime instance"}],
    provenance=[{"title": "KC144 :: 9-", "locator": "1_SxGGqIQYeQyoYfaToPTnb9U5-7wcJ6wVcG-toY3dkg",
                 "evidence_class": "A"}],
    authority={"issued_by": None},
    sigma_E="PARTIAL", sigma_X="UNKNOWN", sigma_S="RESEARCH_ONLY", sigma_P="CANDIDATE",
    delta_return={},
    constructor_id=CONSTRUCTOR, verifier_id=CONSTRUCTOR,
    constructor_channel=CHANNEL, verifier_channel=CHANNEL,
    notes="Station explicitly declined to request promotion. Included to confirm "
          "the kernel agrees with the corpus's own refusal.",
)


# --------------------------------------------------------------------------
# 4. GID088 / IC10-I08 - BRIDGE / DEFECT / RETURN.
#    The corpus's own terminal state: "PROMOTION::BLOCKED  QSHRINK::WITHHELD"
#    "C_E::HOLD_OPEN_BRIDGE"  - the empirical fiber has no apparatus evidence.
# --------------------------------------------------------------------------
GID088 = Candidate(
    candidate_id="KC144.V1::GID088::IC10-I08::BRIDGE_GLUE_RETURN::P11",
    source_epoch="KC144.V1",
    station="GID088",
    r_plus={"carrier": "bridge certificate beta_ij", "type": "BridgeCertificate",
            "return_class": "PARTIAL_INVERSE",
            "loss_manifest": ["C_F lossy state reconstruction without carry prohibited"],
            "invariants": [{"name": "Rji_after_beta_ij_approx_identity",
                            "transport": "declared corridor",
                            "witness": "GID088/P11 C_F"}]},
    r_hinge={"carrier": "replay manifest", "type": "ProcessReturn",
             "return_class": "DECODER", "loss_manifest": ["first-divergence checkpoints"],
             "replay_packet": None},
    r_star={"carrier": "refutation packet", "type": "ConjugateReturn",
            "return_class": "SET_VALUED_RETURN",
            "loss_manifest": ["invalid scalar inverse refuted"],
            "open_bridges": ["C_E model->apparatus certificate ABSENT"]},
    q_contract={"goal": "bridge, defect and return governance",
                "raw_cid": None, "canon_profile": None,
                "dependencies": [{"id": "C_E empirical realization", "status": "OPEN"},
                                 {"id": "I09-I10", "status": "OPEN"}],
                "rollback_head": None},
    corridor={"membership_test": "declared corridor per bridge",
              "claim_ceiling": ["formal only; no empirical inflation"]},
    witnesses=[{"kind": "STRUCTURAL", "evidence_class": "A", "ref": "GID088/P11"},
               {"kind": "RETURN_WITNESS", "evidence_class": "A", "ref": "RS::GID088.P11"}],
    defects=[{"id": "C_E.OPEN_BRIDGE", "severity": "S4", "status": "OPEN",
              "note": "empirical fiber: NATIVE/EMPIRICAL execution count = 0"}],
    provenance=[{"title": "KC144 “Hmm”", "locator": "1BLkCatEi1gZM9PtrNOxvGzY7XXooUSfV4CtT_LaoO1g",
                 "evidence_class": "E"},   # the corpus itself flags this as a derivative mirror
                {"title": "144 posts - crystal", "locator": "1Ct84ETWyBLa9uBXkmsJBBrLSQ6nzVIz_NSBDlph_kA4",
                 "evidence_class": "A"}],
    authority={"issued_by": None},
    sigma_E="PARTIAL", sigma_X="PASS", sigma_S="RESEARCH_ONLY", sigma_P="TESTED",
    delta_return={},
    constructor_id=CONSTRUCTOR, verifier_id=CONSTRUCTOR,
    constructor_channel=CHANNEL, verifier_channel=CHANNEL,
    notes="Corpus terminal state was PROMOTION::BLOCKED. Kernel should agree.",
)


# --------------------------------------------------------------------------
# 5. GID024 / B02 - ADMIT / HINGE.  Fully closed P00-P07 with a structural
#    cold-boot replay score of 25/25 - explicitly flagged IN-THREAD, not an
#    independent cross-conversation measurement.
# --------------------------------------------------------------------------
GID024 = Candidate(
    candidate_id="KC144.V1::GID024::B02::ADMIT_HINGE::P07",
    source_epoch="KC144.V1",
    station="GID024",
    r_plus={"carrier": "joint admission receipt", "type": "AdmissionReceipt",
            "return_class": "EXACT_INVERSE",
            "loss_manifest": [],
            "invariants": [{"name": "verdict_set_closed_at_five",
                            "transport": "enumeration {ADMIT, ADMIT_WITH_BRANCHES, HOLD, REPAIR, REJECT}",
                            "witness": "GID024/P02"},
                           {"name": "never_manufactures_agreement",
                            "transport": "typed pullback A_join = intersection of e_k^-1",
                            "witness": "GID024/P03"}]},
    r_hinge={"carrier": "P00-P07 pass chain", "type": "ProcessReturn",
             "return_class": "PARTIAL_INVERSE", "loss_manifest": ["six correction patches at P06"],
             "replay_packet": {"inputs": "admission input", "addresses": "GID024/R02C12",
                               "atlas_version": "KC144.V1", "operations": "P00-P07",
                               "route_order": "hinge rail 024->027->...->042",
                               "policies": "source precedence lock", "seeds": "GID024/P00",
                               "decoder": "structural", "expected_result": "25/25 checklist",
                               "executed": True, "boot_class": "B0"}},
    r_star={"carrier": "conjugate audit", "type": "ConjugateReturn",
            "return_class": "COMPENSATING_RETURN",
            "loss_manifest": ["CARRY024.01-06"],
            "open_bridges": ["independent cross-conversation cold-boot performance"]},
    q_contract={"goal": "joint admissibility without manufactured agreement",
                "raw_cid": None, "canon_profile": None,
                "dependencies": [{"id": "GID023 B01", "status": "CLOSED"},
                                 {"id": "GID025 B03", "status": "CLOSED"}],
                "rollback_head": "GID024/P06"},
    corridor={"membership_test": "BR21 ADMIT family, hinge lens",
              "claim_ceiling": ["promoted as a formal operator contract only; "
                                "NOT proof that future verdicts will be correct"]},
    witnesses=[{"kind": "STRUCTURAL", "evidence_class": "A", "ref": "GID024/P07 25/25"},
               {"kind": "RETURN_WITNESS", "evidence_class": "A", "ref": "GID024/P07 compression seed"}],
    defects=[{"id": "CARRY024.06", "severity": "S2", "status": "OPEN",
              "note": "independent cross-conversation cold-boot performance remains empirical"}],
    provenance=[{"title": "KC144 :: 5-", "locator": "1L-G0Lzdovg_jwa_GilXs2CSZCfL8jAlfgaLccnj1n3I",
                 "evidence_class": "A"}],
    authority={"issued_by": "GID024/P07"},
    sigma_E="SUPPORTED", sigma_X="PASS", sigma_S="ALLOW_LIMITED", sigma_P="TESTED",
    delta_return={"id": 0, "source": 0, "authority": None},   # authority never measured
    constructor_id=CONSTRUCTOR, verifier_id=CONSTRUCTOR,
    constructor_channel=CHANNEL, verifier_channel=CHANNEL,
)


ALL = [GID020, GID044, GID043, GID088, GID024]
