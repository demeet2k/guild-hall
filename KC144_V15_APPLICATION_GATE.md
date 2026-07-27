# KC144 V15 — External Application Gate

```text
LOOKUP_KEY::KC144.V15::EXTERNAL_APPLICATION_GATE
ROLE::PUBLICATION_AND_APPLICATION_INGRESS_OVERLAY
BASE_BRANCH::kc144-completed-crystal-v15
BASE_COMMIT::1b653e39d7c09ba8b93a800860244242cd98d397
BASE_TREE::d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b
PUBLICATION_STATE::FIVE_ROLE_CALLS_EXTERNALLY_PUBLISHED
APPLICATION_STATE::AWAITING_VALID_EXTERNAL_APPLICATIONS
GOVERNANCE_AUTHORITY_GRANTED::FALSE
TRUTH_EFFECT::NONE
```

The complete V15 crystal is immutable on the public branch
[`kc144-completed-crystal-v15`](https://github.com/demeet2k/guild-hall/tree/kc144-completed-crystal-v15).
This default-branch document is an additive transport overlay: it exposes the
five exact role-bound application payloads, records stable public locators, and
opens a structured ingress route. It does not rewrite the frozen runtime state.

## Apply

[Open the KC144 V15 signed-application form](https://github.com/demeet2k/guild-hall/issues/new?template=kc144-v15-application.yml)

Submit one public, double-signed
`KC144.BatchBoundCandidateApplication.V15` object. Generate and retain all
private keys externally. Never place a private key, password, recovery phrase,
access token, or other secret in a GitHub issue.

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
issue locators above. The publication overlay establishes a digest-preserving
bijection:

```text
phi_pub: P -> L
|P| = |L| = 5
role(phi_pub(p)) = role(p)
digest(phi_pub(p)) = digest(p)
```

This closes only the **external call-publication** sub-barrier. It does not
alter the historical frozen manifest, whose `READY_UNPUBLISHED` values describe
the state at V15 compilation time.

The live barrier is now:

```text
FIVE_VALID_INDEPENDENT_BATCH_BOUND_APPLICATIONS_REQUIRED
```

A submitted issue is not automatically a valid application. Only an object
that passes schema, inner V14 signature, outer V15 signature, batch, manifest,
role-call, validity-window, uniqueness, independence, and conflict checks may
enter the append-only receipt ledger. Rejected or duplicate objects remain
preserved and non-counting.

## Truth boundary

External publication proves public addressability of the five exact calls. It
does not prove delivery to a particular person, candidate identity,
independence, fitness, selection, packet assignment, governance activation,
M12 closure, certification, or any production truth claim.

```text
NEXT::KC144.V15::INGEST-VERIFY-AND-LEDGER-REAL-BATCH-BOUND-APPLICATIONS
RETURN::KC144.V15::PUBLIC_MIRROR
PARENT::KC144.V15::PUBLISH-FIVE-BATCH-BOUND-CALL-PAYLOADS-AND-INGEST-REAL-APPLICATIONS
```
