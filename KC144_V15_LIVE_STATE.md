# KC144 V15 — Live State Metro

```text
LOOKUP_KEY::KC144.V15::LIVE_STATE_METRO
BASE_BRANCH::kc144-completed-crystal-v15
BASE_COMMIT::1b653e39d7c09ba8b93a800860244242cd98d397
BASE_TREE::d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b
PUBLIC_ROLE_CALLS::5/5
CRYPTOGRAPHIC_PASS_LEDGER::kc144-v15-pass-ledger
COHORT_SNAPSHOT_REGISTRY::kc144-v15-cohort-snapshots
PARALLEL_ROUTE_REGISTRY::kc144-parallel-navigation-v1
PARALLEL_ROUTE_WIDTH::5
PARALLEL_ROUTE_SNAPSHOT::sha256:c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d
GLOBAL_DUPLICATE_SYMMETRY::ACTIVE
EXTERNAL_ADJUDICATION_TRUST_ROOT_COUNT::0
TECHNICAL_APPLICATIONS::1
EXCLUDED_SYNTHETIC_APPLICATIONS::1
COUNTING_CANDIDATES::0
FILLED_ROLE_VECTOR::0/5
COUNTING_COHORT::NOT_YET_CONSTITUTED
IDENTITY_INDEPENDENCE_EXTERNALLY_PROVEN::FALSE
GOVERNANCE_AUTHORITY_GRANTED::FALSE
PRODUCTION_TRUTH_EFFECT::NONE
```

This is the live navigation surface for the external V15 boundary. Its state is
query-driven: GitHub issues carry transport observations, the dedicated ledger
branch carries content-addressed cryptographic-PASS receipts, and no manually
maintained counter is authoritative.

## One-screen route

```text
PUBLIC_MIRROR
  -> APPLICATION_GATE
  -> SIGNED_GITHUB_ISSUE
  -> IMMUTABLE_CRYPTOGRAPHIC_VERIFIER
  -> CONTENT_ADDRESSED_RECEIPT
  -> APPEND_ONLY_PASS_LEDGER
  -> FIXED_TREE_COHORT_SNAPSHOT
  -> GLOBAL_DUPLICATE_SYMMETRY
  -> EXTERNAL_IDENTITY_AND_INDEPENDENCE_ADJUDICATION
  -> FIVE_ROLE_VECTOR
  -> DELIVERY_BARRIER
```

The route is active through fixed-tree snapshot compilation and global duplicate
symmetry. A receipt stops at `CRYPTOGRAPHIC_PREFLIGHT_PASS_NONCOUNTING`.
No issue, label, bot comment, receipt, uniqueness result, or self-declared root
crosses the external-adjudication boundary.

## Live views

- [All V15 application issues](https://github.com/demeet2k/guild-hall/issues?q=is%3Aissue+%22%5BKC144+V15+APPLICATION%5D%22+in%3Atitle)
- [Cryptographic preflight PASS observations](https://github.com/demeet2k/guild-hall/issues?q=is%3Aissue+label%3A%22kc144%3Av15%3Apreflight-pass%22)
- [Content-addressed/ledgered observations](https://github.com/demeet2k/guild-hall/issues?q=is%3Aissue+label%3A%22kc144%3Av15%3Aledgered%22)
- [Fail-closed HOLD observations](https://github.com/demeet2k/guild-hall/issues?q=is%3Aissue+label%3A%22kc144%3Av15%3Ahold%22)
- [Append-only PASS ledger](https://github.com/demeet2k/guild-hall/tree/kc144-v15-pass-ledger/ledger/v15)
- [Fixed-tree cohort gate](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_COHORT_GATE.md)
- [Cohort snapshot registry](https://github.com/demeet2k/guild-hall/tree/kc144-v15-cohort-snapshots/cohort/v15)
- [Current fixed-tree snapshot](https://github.com/demeet2k/guild-hall/blob/kc144-v15-cohort-snapshots/cohort/v15/snapshots/sha256/b7/b7835f3b8ba011e5c0b2c160bbe8cf299d7741896cdfc0903c09e9ad22b2a446.snapshot.json)
- [Five-lane parallel route metro](https://github.com/demeet2k/guild-hall/blob/main/KC144_PARALLEL_ROUTE_METRO.md)
- [Current parallel route snapshot](https://github.com/demeet2k/guild-hall/blob/kc144-parallel-navigation-v1/registry/parallel-navigation/v1/snapshots/sha256/c8/c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d.json)
- [Open a signed application](https://github.com/demeet2k/guild-hall/issues/new?template=kc144-v15-application.yml)

## Executed verification matrix

```text
DUPLICATE_KEY_REJECTION::PASS
BOT_COMMENT_IDEMPOTENCE::PASS
STALE_CLOSED_SNAPSHOT_REJECTION::PASS
SIGNED_ROLE_SUBSTITUTION_REJECTION::PASS
POSITIVE_DOUBLE_SIGNATURE_PATH::PASS
CONTENT_ADDRESSED_APPEND::PASS
POSITIVE_LEDGER_IDEMPOTENCE::PASS
REPEATED_SOURCE_COLLAPSE::PASS
GLOBAL_DUPLICATE_SYMMETRY::PASS
DETERMINISTIC_SNAPSHOT_REPLAY::PASS
SYNTHETIC_COUNTING_EFFECT::NONE
ONE-WORKER/FIVE-WORKER-ROUTE-REPLAY::BYTE-IDENTICAL
FIVE-ROUTE-PAIRWISE-HOLONOMY::10/10-NONZERO
```

- [#9 duplicate-key HOLD](https://github.com/demeet2k/guild-hall/issues/9)
- [#10 stale/closed HOLD](https://github.com/demeet2k/guild-hall/issues/10)
- [#11 positive preflight, append, and idempotent rerun](https://github.com/demeet2k/guild-hall/issues/11)
- [#12 signed role-substitution HOLD](https://github.com/demeet2k/guild-hall/issues/12)

## Five immutable ingress coordinates

| Role | Public call | State before a real valid application |
|---|---|---|
| CUSTODIAN | [#3](https://github.com/demeet2k/guild-hall/issues/3) | `PUBLISHED_AWAITING_APPLICATION` |
| INDEPENDENT_REVIEWER | [#4](https://github.com/demeet2k/guild-hall/issues/4) | `PUBLISHED_AWAITING_APPLICATION` |
| REPLAY_WITNESS | [#5](https://github.com/demeet2k/guild-hall/issues/5) | `PUBLISHED_AWAITING_APPLICATION` |
| SOURCE_AUDITOR | [#6](https://github.com/demeet2k/guild-hall/issues/6) | `PUBLISHED_AWAITING_APPLICATION` |
| RETURN_AUDITOR | [#7](https://github.com/demeet2k/guild-hall/issues/7) | `PUBLISHED_AWAITING_APPLICATION` |

## State algebra

For a current issue snapshot `s`, immutable verifier `V`, application digest
`d`, and ledger tree `T`:

```text
PREFLIGHT(s) =
  CURRENT_SNAPSHOT(s)
  AND STRICT_PARSE(s)
  AND SINGLE_ROLE_BINDING(s)
  AND OBSERVED_INSIDE_BATCH(s.updated_at)
  AND V(s) = PASS

APPEND(T, d, s) =
  IDEMPOTENT                    if the exact source binding already exists
  T + {object, receipt, source} if all occupied paths agree byte-for-byte
  HOLD                          otherwise

COUNTING(d, fixed(T)) =
  FALSE until global duplicate symmetry, external identity,
  external independence, conflicts, and the five-role vector are adjudicated
```

The application object is addressed by the SHA-256 digest of its canonical JSON
bytes. The issue source is permanently bound to its first accepted body digest.
Concurrent writers use non-force fast-forward updates and retry from the latest
ledger head.

## Exclusion law

Synthetic tests, malformed objects, stale snapshots, replays, content-address
collisions, source-binding conflicts, duplicate identifiers, and
identity/independence claims without external adjudication are non-counting.
They remain observable without being promoted into truth.
