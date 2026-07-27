# KC144 V15 fixed-tree cohort snapshots

This branch contains deterministic global evaluations of exact
`kc144-v15-pass-ledger` trees.

Each snapshot is a pure function of:

```text
(ledger_commit, ledger_tree, compiler_commit)
```

It groups repeated source observations by application digest before evaluating
duplicates, then marks every member of every duplicate set symmetrically. A
streaming first writer receives no priority.

The compiler also applies explicit synthetic-test exclusions. A technical
receipt, global uniqueness, or self-declared evidence root cannot establish
external identity or independence. With no admissible external adjudication
trust anchors, counting remains zero.

```text
TECHNICAL_PASS != INDEPENDENT_CANDIDATE
GLOBAL_UNIQUE != EXTERNALLY_VERIFIED_INDEPENDENT
FIVE_ROLE_VECTOR != GOVERNANCE_AUTHORITY
SNAPSHOT != PRODUCTION_TRUTH
```

## Topology

```text
cohort/v15/
  GENESIS.json
  CONTRACT.json
  ADJUDICATION_TRUST_ROOTS.json
  README.md
  schemas/
  snapshots/sha256/<first-two-hex>/<snapshot-digest>.snapshot.json
  sources/ledger-trees/<ledger-tree>/<compiler-commit>.json
```

Snapshot and source paths are immutable. The branch head is only a navigation
pointer to the append-only history.
