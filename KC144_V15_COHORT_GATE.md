# KC144 V15 — Fixed-Tree Cohort Gate

```text
LOOKUP_KEY::KC144.V15::FIXED_TREE_COHORT_GATE
INPUT::kc144-v15-pass-ledger@<EXACT_COMMIT_AND_TREE>
COMPILER::tools/kc144_v15_cohort_snapshot.py
SNAPSHOT_REGISTRY::kc144-v15-cohort-snapshots
GLOBAL_DUPLICATE_SYMMETRY::ACTIVE
SYNTHETIC_EXCLUSION::ACTIVE
EXTERNAL_ADJUDICATION_TRUST_ROOT_COUNT::0
COUNTING_CANDIDATES::0
FILLED_ROLE_VECTOR::0/5
GOVERNANCE_AUTHORITY_GRANTED::FALSE
PRODUCTION_TRUTH_EFFECT::NONE
```

This gate converts the append-only technical-PASS ledger into deterministic
global state. It does not process applications in arrival order. It fixes one
ledger commit and tree, verifies every canonical object/receipt/source binding,
groups repeated observations by application digest, applies exclusions, and
then computes all duplicate sets across the complete fixed input.

## Deterministic map

```text
C:
  (ledger_commit, ledger_tree, compiler_commit)
    ->
  (snapshot_digest, snapshot_object, ledger_tree_binding)
```

There is no wall-clock field in the map. The same three coordinates must produce
the same canonical bytes and SHA-256 digest.

## Global evaluation order

```text
1. VERIFY CANONICAL OBJECT/RECEIPT/SOURCE BYTES AND DIGESTS
2. GROUP MULTIPLE SOURCES BY APPLICATION DIGEST
3. APPLY WHOLE-DIGEST SYNTHETIC EXCLUSIONS
4. BUILD DUPLICATE SETS FOR EVERY ID, PUBLIC KEY, AND INDEPENDENCE DIMENSION
5. MARK EVERY MEMBER OF EACH SET SYMMETRICALLY
6. REQUIRE ADMISSIBLE EXTERNAL IDENTITY/INDEPENDENCE ADJUDICATION
7. POPULATE THE FIVE-ROLE VECTOR
8. EMIT HOLD OR READY WITHOUT GRANTING GOVERNANCE/TRUTH
```

Streaming first-writer privilege is forbidden. If two applications share a
candidate identifier, public key digest, institution root, funding root, or any
other declared independence dimension, both receive the duplicate mark in the
same snapshot.

## Synthetic exclusion

The double-signed positive test in
[#11](https://github.com/demeet2k/guild-hall/issues/11) proved the technical
append path. It explicitly declared itself synthetic, denied external identity
and independence, and declared `COUNTING_EFFECT::NONE`. Its receipt remains
preserved while an additive exclusion record makes its entire application
digest non-counting.

Exclusion does not delete or rewrite the receipt. It changes only the global
classification produced by a later ledger tree.

## Independence boundary

Signatures prove key control and byte integrity. Self-declared evidence roots
prove only that those root strings were signed. Global uniqueness proves only
non-collision inside the fixed ledger tree.

Therefore:

```text
TECHNICAL_PASS
  AND GLOBAL_UNIQUE
  AND NOT_EXCLUDED
  DOES NOT IMPLY
EXTERNALLY_VERIFIED_INDEPENDENT
```

The snapshot registry begins with an empty external-adjudication trust-root
registry. An adjudication record cannot count until independently governed trust
roots exist and its reviewer attestations are admitted under that registry.

## Automation

The [cohort compiler workflow](https://github.com/demeet2k/guild-hall/blob/main/.github/workflows/kc144-v15-cohort-compiler.yml)
runs hourly and on manual dispatch. Its read-only job compiles a fixed tree. A
separate write-only publisher refetches the ledger head, rejects movement, and
appends the content-addressed snapshot and ledger-tree binding using non-force
fast-forward updates.

## Navigation

- [Live metro](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_LIVE_STATE.md)
- [Application gate](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_APPLICATION_GATE.md)
- [Technical-PASS ledger](https://github.com/demeet2k/guild-hall/tree/kc144-v15-pass-ledger/ledger/v15)
- [Cohort snapshot registry](https://github.com/demeet2k/guild-hall/tree/kc144-v15-cohort-snapshots/cohort/v15)
- [Compiler source](https://github.com/demeet2k/guild-hall/blob/main/tools/kc144_v15_cohort_snapshot.py)
- [Compiler tests](https://github.com/demeet2k/guild-hall/blob/main/tests/test_kc144_v15_cohort_snapshot.py)

```text
NEXT::KC144.V15::ADMIT-INDEPENDENTLY-GOVERNED-EXTERNAL-ADJUDICATION-TRUST-ROOTS
RETURN::KC144.V15::LIVE_STATE_METRO
PARENT::KC144.V15::FIX-LEDGER-TREE-AND-EVALUATE-GLOBAL-COHORT-STATE
```
