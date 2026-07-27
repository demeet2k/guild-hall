# KC144 V15 — External Application Gate

```text
LOOKUP_KEY::KC144.V15::EXTERNAL_APPLICATION_GATE
ROLE::PUBLICATION_VERIFICATION_AND_LEDGER_INGRESS_OVERLAY
BASE_BRANCH::kc144-completed-crystal-v15
BASE_COMMIT::1b653e39d7c09ba8b93a800860244242cd98d397
BASE_TREE::d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b
PUBLICATION_STATE::FIVE_ROLE_CALLS_EXTERNALLY_PUBLISHED
VERIFICATION_STATE::STRICT_FAIL_CLOSED_TWO_JOB_PIPELINE
LEDGER_STATE::CONTENT_ADDRESSED_APPEND_ONLY_ACTIVE
APPLICATION_STATE::AWAITING_VALID_EXTERNAL_APPLICATIONS
COUNTING_COHORT::NOT_YET_CONSTITUTED
GOVERNANCE_AUTHORITY_GRANTED::FALSE
TRUTH_EFFECT::NONE
```

The complete V15 crystal is immutable on
[`kc144-completed-crystal-v15`](https://github.com/demeet2k/guild-hall/tree/kc144-completed-crystal-v15).
This default-branch gate is an additive transport overlay. It exposes the five
exact role-bound payloads, accepts public signed objects, verifies current issue
snapshots against the frozen runtime, and appends content-addressed technical
receipts. It does not rewrite the crystal.

Use the [live state metro](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_LIVE_STATE.md)
to navigate the whole active route.

## Apply

[Open the KC144 V15 signed-application form](https://github.com/demeet2k/guild-hall/issues/new?template=kc144-v15-application.yml)

Submit one public, double-signed
`KC144.BatchBoundCandidateApplication.V15` object for exactly one role. Generate
and retain every private key externally. Never place a private key, password,
recovery phrase, access token, or other secret in a GitHub issue.

## Autonomous verification and append

The [KC144 V15 application verifier](https://github.com/demeet2k/guild-hall/blob/main/.github/workflows/kc144-v15-application-verifier.yml)
runs when an application issue is opened or edited.

1. A read-only job checks out exact commit
   `1b653e39d7c09ba8b93a800860244242cd98d397`.
2. It rejects oversized bodies, missing or duplicate sections, duplicate JSON
   keys, non-finite numbers, extra/missing schema keys, oversized identifiers,
   malformed roots, unchecked declarations, and missing evidence locators.
3. It requires one exact ingress role:
   the form role, payload digest, eligible-role vector, target call identifier,
   and target call digest must all match the same immutable role payload.
4. It uses `github.issue.updated_at` as the external observation time and
   requires the observation and signed submission to be inside the batch
   window, with the submission no more than 24 hours old when observed.
5. It runs the frozen double-signature, batch, manifest, role-call, and time
   verifier.
6. A separate publisher job refetches the issue and rejects a changed, closed,
   or stale snapshot before any write.
7. A technical PASS is appended to
   [`kc144-v15-pass-ledger`](https://github.com/demeet2k/guild-hall/tree/kc144-v15-pass-ledger/ledger/v15)
   as canonical application, receipt, and permanent source binding.
8. One exact `github-actions[bot]` comment and bounded labels expose the result.

The publisher executes no applicant code and does not check out the repository.
Ledger ref updates are non-force fast-forwards with bounded retry. Repeating the
same accepted snapshot is idempotent; changing an already-bound issue/application
pair is held.

The only positive issue-level technical state is:

```text
CRYPTOGRAPHIC_PREFLIGHT_PASS_NONCOUNTING
```

It is not a valid independent cohort member. Identity and independence remain
false until externally adjudicated over one fixed ledger tree. Duplicate
applications and identifiers are evaluated symmetrically at that later global
snapshot; no streaming first writer can acquire counting priority.

The next stage is implemented at the
[fixed-tree cohort gate](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_COHORT_GATE.md).
It preserves technical receipts while grouping replayed sources, applying
synthetic exclusions, and marking every member of every duplicate set.

The closed [fail-closed self-test issue #8](https://github.com/demeet2k/guild-hall/issues/8)
contains a deliberately incomplete synthetic object and is non-counting.

## Adversarial integration evidence

The release was exercised through public issue events, not only local fixtures:

| Case | Public evidence | Observed result |
|---|---|---|
| Duplicate JSON key and repeated run | [Issue #9](https://github.com/demeet2k/guild-hall/issues/9), [workflow](https://github.com/demeet2k/guild-hall/actions/runs/30297551241) | `HOLD`; one exact bot comment after rerun |
| Issue closed between verification and publication | [Issue #10](https://github.com/demeet2k/guild-hall/issues/10), [workflow](https://github.com/demeet2k/guild-hall/actions/runs/30297743485) | `STALE_HOLD`; HOLD and stale labels |
| Valid double-signed synthetic object | [Issue #11](https://github.com/demeet2k/guild-hall/issues/11), [workflow](https://github.com/demeet2k/guild-hall/actions/runs/30297866329), [source binding](https://github.com/demeet2k/guild-hall/blob/kc144-v15-pass-ledger/ledger/v15/sources/github-issues/000000000011.json) | first run `APPENDED`; rerun `ALREADY_PRESENT_IDEMPOTENT`; explicitly non-counting |
| Valid signatures with form/signed-role substitution | [Issue #12](https://github.com/demeet2k/guild-hall/issues/12), [workflow](https://github.com/demeet2k/guild-hall/actions/runs/30297864793) | `HOLD` on `single_role_ingress_exact`; no ledger write |

All synthetic test issues are closed and have `COUNTING_EFFECT::NONE`.

## Publication receipts

| Role | Public call | Immutable payload | Payload digest |
|---|---|---|---|
| CUSTODIAN | [Issue #3](https://github.com/demeet2k/guild-hall/issues/3) | [JSON](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/registry/v15/application_publication_custodian_v15.json) | `sha256:3714c4cc058ec345b33d4cbdb38741d10ad9520937dab8396670135fc7b74a3b` |
| INDEPENDENT_REVIEWER | [Issue #4](https://github.com/demeet2k/guild-hall/issues/4) | [JSON](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/registry/v15/application_publication_independent_reviewer_v15.json) | `sha256:3c8292b222bd4475e36554dc7f64b0988ee529be061690dd63e6374f79625f10` |
| REPLAY_WITNESS | [Issue #5](https://github.com/demeet2k/guild-hall/issues/5) | [JSON](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/registry/v15/application_publication_replay_witness_v15.json) | `sha256:ac3ec296c8479514a5a51eeba546216f036288843d20ac92ff004e14d1bc60ee` |
| SOURCE_AUDITOR | [Issue #6](https://github.com/demeet2k/guild-hall/issues/6) | [JSON](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/registry/v15/application_publication_source_auditor_v15.json) | `sha256:502d009c9347dc357ad672077013a0adb3e64bfc2590fb5d3828358b80b53d20` |
| RETURN_AUDITOR | [Issue #7](https://github.com/demeet2k/guild-hall/issues/7) | [JSON](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/registry/v15/application_publication_return_auditor_v15.json) | `sha256:378340758cbd0ff5dd7f6498a5552d5c80fc7228e1caa8d870e28aab6096769b` |

All five payloads bind the same immutable transport coordinate:

```text
TRANSPORT_ID::KC144.CANDIDATE.APPLICATION.TRANSPORT.V15
BATCH_ID::V11-BATCH::c7e3ae7e8cfd126a75b41b4a
BATCH_ROOT::sha256:b9322c5950d562f7a3f437ed8c939d98506db4edf34446e8332318513bca46b5
CALL_MANIFEST_ROOT::sha256:fc82581375a195d09a58b7769eb33bba719c7f7e4b7ddd7b5276dcf1ce1d6219
TRANSPORT_CONTRACT_DIGEST::sha256:792599594c518288c15161f314721d0319f791f54cab652341f1aec7d1f2bde8
SIGNATURE_ALGORITHM::ED25519
OUTER_SIGNATURE_DOMAIN::KC144.V15.BATCH_BOUND_CANDIDATE_APPLICATION
```

## Verification route

- [Transport contract](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/registry/v15/application_transport_contract_v15.json)
- [Frozen publication manifest](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/registry/v15/application_publication_manifest_v15.json)
- [Application JSON Schema](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/schemas/kc144/batch-bound-candidate-application-v15.schema.json)
- [Executable verifier](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/src/kc144_crystal/application_v15.py)
- [Application transport tests](https://github.com/demeet2k/guild-hall/blob/kc144-completed-crystal-v15/tests/test_application_transport_v15.py)
- [Ledger contract](https://github.com/demeet2k/guild-hall/blob/kc144-v15-pass-ledger/ledger/v15/CONTRACT.json)
- [Fixed-tree cohort gate](https://github.com/demeet2k/guild-hall/blob/main/KC144_V15_COHORT_GATE.md)
- [Cohort snapshot registry](https://github.com/demeet2k/guild-hall/tree/kc144-v15-cohort-snapshots/cohort/v15)

Local verification command after placing a candidate object in
`batch-bound-candidate-application.json`:

```bash
PYTHONPATH=src python3 -m kc144_crystal candidate-application-verify \
  registry/v11/governance_challenge_batch_v11.json \
  batch-bound-candidate-application.json \
  --checked-at <ISO-8601-TIME>
```

## State transition law

Let `P` be the five immutable prepared payloads and `L` the five public GitHub
issue locators. Publication establishes:

```text
phi_pub: P -> L
|P| = |L| = 5
role(phi_pub(p)) = role(p)
digest(phi_pub(p)) = digest(p)
```

For an application issue `s`:

```text
technical_pass(s)
  = current_snapshot(s)
  AND strict_schema(s)
  AND exact_single_role_binding(s)
  AND time_valid(s.updated_at)
  AND immutable_runtime(s) = PASS

technical_pass(s) DOES NOT IMPLY independent_candidate(s)
```

The live barrier remains:

```text
FIVE_VALID_INDEPENDENT_BATCH_BOUND_APPLICATIONS_REQUIRED
```

## Truth boundary

External publication proves public addressability. A content-addressed receipt
proves that one observed issue snapshot passed the cryptographic preflight. It
does not prove candidate identity, external independence, fitness, selection,
delivery, packet assignment, governance activation, M12 closure, certification,
or production truth.

```text
NEXT::KC144.V15::ADMIT-INDEPENDENTLY-GOVERNED-EXTERNAL-ADJUDICATION-TRUST-ROOTS
RETURN::KC144.V15::LIVE_STATE_METRO
PARENT::KC144.V15::PUBLISH-VERIFY-LEDGER-WITHOUT-PREMATURE-COUNTING
```
