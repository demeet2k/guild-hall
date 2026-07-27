# KC144 V15 cryptographic-PASS ledger

This branch is an append-only observation log for applications that pass the
immutable V15 cryptographic verifier. It is rooted at the exact completed
crystal commit `1b653e39d7c09ba8b93a800860244242cd98d397` and tree
`d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b`.

A ledger receipt means only:

```text
CRYPTOGRAPHIC_PREFLIGHT_PASS_NONCOUNTING
COHORT_EFFECT::NONE_PENDING_FIXED_TREE_SNAPSHOT
IDENTITY_INDEPENDENCE_EXTERNALLY_PROVEN::FALSE
GOVERNANCE_AUTHORITY_GRANTED::FALSE
PRODUCTION_TRUTH_EFFECT::NONE
```

It does not establish identity, independence, fitness, uniqueness across the
whole cohort, selection, delivery, enrollment, authority, certification, M12
closure, or production truth.

## Content-addressed topology

```text
ledger/v15/
  GENESIS.json
  CONTRACT.json
  README.md
  schemas/
  objects/sha256/<first-two-hex>/<application-digest>.application.json
  receipts/sha256/<first-two-hex>/<receipt-digest>.receipt.json
  sources/github-issues/<zero-padded-issue-number>.json
```

The application digest is SHA-256 over UTF-8 canonical JSON:
`sort_keys=true`, separators `,` and `:`, and `ensure_ascii=false`. Stored
application bytes are that canonical form followed by one LF; the LF is not
part of the application digest.

Each accepted GitHub issue is permanently bound to its first accepted
application/body pair. Re-running the same snapshot is idempotent. A different
body or application at an already-bound issue path is a conflict and is held.
The same application may be observed at more than one source; that preserves
evidence but does not create multiple candidates.

No mutable aggregate is authoritative. Global duplicate and independence
evaluation occurs only over a fixed ledger tree in a later cohort snapshot.
