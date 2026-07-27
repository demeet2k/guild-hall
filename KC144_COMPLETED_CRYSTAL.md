# KC144 Completed Crystal V15 — Public Metro Entry

```text
LOOKUP_KEY::KC144.V15::PUBLIC_MIRROR
ROLE::DEFAULT-BRANCH_NAVIGATION_GATE
PRIMARY::demeet2k/guild-hall@kc144-completed-crystal-v15
INTENDED_ORIGIN::AthenachkaCollective/KC144_COMPLETED_CRYSTAL
STATUS::PUBLIC_MIRROR_ACTIVE
APPLICATION_GATE::FIVE_ROLE_CALLS_EXTERNALLY_PUBLISHED
VERIFIER::STRICT_FAIL_CLOSED_ACTIVE
PASS_LEDGER::CONTENT_ADDRESSED_APPEND_ONLY_ACTIVE
COHORT_COMPILER::FIXED_TREE_GLOBAL_SYMMETRY_ACTIVE
COHORT_SNAPSHOT_REGISTRY::kc144-v15-cohort-snapshots
COUNTING_COHORT::NOT_YET_CONSTITUTED
PROMOTION_STATUS::WAITING_FOR_TARGET_WRITE_AUTHORITY
```

This entry exposes the complete KC144 V15 crystal from the public default branch
without merging it into or replacing `guild-hall/main`.

## Canonical identity

- Public branch: [`kc144-completed-crystal-v15`](https://github.com/demeet2k/guild-hall/tree/kc144-completed-crystal-v15)
- Public commit: [`1b653e39d7c09ba8b93a800860244242cd98d397`](https://github.com/demeet2k/guild-hall/commit/1b653e39d7c09ba8b93a800860244242cd98d397)
- Local publication commit: `48db9d009cd08b188cbfb0262ad84bb40ae59091`
- Exact root-tree SHA: `d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b`
- Published paths: `1,160`
- Unique Git blobs: `533`
- Verification matrix: `21/21 PASS`
- Version: `15.0.0`

The fetched public branch tree and the verified local tree have the same Git SHA
and a zero-file diff. Git object identity, not a descriptive claim, is the
publication equality witness.

## Navigation

- [Live state metro](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_LIVE_STATE.md)
- [Machine metro](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_MACHINE_METRO.json)
- [External application gate](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_APPLICATION_GATE.md)
- [Submit a signed V15 application](https://github.com/demeet2k/guild-hall/issues/new?template=kc144-v15-application.yml)
- [Append-only cryptographic-PASS ledger](https://github.com/demeet2k/guild-hall/tree/kc144-v15-pass-ledger/ledger/v15)
- [Fixed-tree cohort gate](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_COHORT_GATE.md)
- [Cohort snapshot registry](https://github.com/demeet2k/guild-hall/tree/kc144-v15-cohort-snapshots/cohort/v15)
- [Framework entrance / README](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/README.md)
- [Completed framework](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/COMPLETED_FRAMEWORK.md)
- [Systematic framework V3](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/SYSTEMATIC_FRAMEWORK_V3.md)
- [Mycelium framework V4](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/MYCELIUM_FRAMEWORK_V4.md)
- [Global state framework V5](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/GLOBAL_STATE_FRAMEWORK_V5.md)
- [M12 repair framework V6](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/M12_REPAIR_FRAMEWORK_V6.txt)
- [Source runtime](https://github.com/demeet2k/guild-hall/tree/kc144-completed-crystal-v15/src)
- [Canonical registries](https://github.com/demeet2k/guild-hall/tree/kc144-completed-crystal-v15/registry)
- [Schemas](https://github.com/demeet2k/guild-hall/tree/kc144-completed-crystal-v15/schemas)
- [Tests](https://github.com/demeet2k/guild-hall/tree/kc144-completed-crystal-v15/tests)
- [Evidence](https://github.com/demeet2k/guild-hall/tree/kc144-completed-crystal-v15/evidence)
- [Checksum manifest](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/CHECKSUMS.sha256)

## Status boundary

Publication means that the V15 source tree and all five role-bound application
calls are publicly addressable and cryptographically reproducible. The live
overlay can now parse, verify, content-address, and ledger exact issue
snapshots, then compile deterministic global cohort state from one fixed ledger
tree.

It does **not** assert that a valid independent candidate exists, participant
delivery, governance activation, independent witness completion, or M12
certification. Even a technical PASS remains non-counting until a fixed ledger
tree is globally checked for duplicate symmetry, identity, independence, and
conflicts.

Current live barrier:

```text
FIVE_REAL_EXTERNALLY_VERIFIED_INDEPENDENT_APPLICATIONS_REQUIRED
```

Current fixed-tree cohort state:

- [snapshot `sha256:b7835f3b…a446`](https://github.com/demeet2k/guild-hall/blob/kc144-v15-cohort-snapshots/cohort/v15/snapshots/sha256/b7/b7835f3b8ba011e5c0b2c160bbe8cf299d7741896cdfc0903c09e9ad22b2a446.snapshot.json)
- one technical application; one synthetic exclusion
- zero counting candidates; zero of five roles filled
- governance authority `false`; production truth effect `NONE`

Canonical continuation:

```text
KC144.V15::ADMIT-INDEPENDENTLY-GOVERNED-EXTERNAL-ADJUDICATION-TRUST-ROOTS
```

## Promotion route

When write authority becomes available for
`AthenachkaCollective/KC144_COMPLETED_CRYSTAL`, promote the exact tree
`d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b` without rebuilding,
reserializing, or changing evidence standing.
