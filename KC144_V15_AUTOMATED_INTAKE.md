# KC144 V15 — Automated Public Intake

```text
LOOKUP_KEY::KC144.V15::AUTOMATED_PUBLIC_INTAKE
ENTRY::KC144.V1::GID006::H06
NEXUS::KC144.V1::GID003::H03
EVIDENCE_LEDGER::KC144.V1::GID005::H05
ROUTE_LEDGER::KC144.V1::GID141::M09
RETURN::KC144.V1::GID144::M12
PROMOTION_GATE::KC144.V1::GID090::I10
PROMOTION_STATE::HOLD
TRUTH_EFFECT::NONE
```

The public issue form is now an executable intake membrane. Every opened,
edited, reopened, or manually replayed KC144 V15 application issue is routed
through three synchronized lanes:

1. **Transport admission** — extract exactly one public JSON object, bind the
   selected role to its immutable payload digest, reject secret-bearing fields,
   and freeze an application hash.
2. **Cryptographic verification** — run the canonical V15 verifier from exact
   commit `1b653e39d7c09ba8b93a800860244242cd98d397`, checking the immutable
   challenge batch, call manifest, target roles, timing, inner V14 signature,
   and outer V15 signature.
3. **Receipt and return** — emit a deterministic receipt comment, preserve the
   replay capsule as a workflow artifact, and return to
   `KC144.V1::GID144::M12`.

The workflow is replay-safe: identical application bytes and verifier results
produce the same receipt digest, and an identical receipt is not commented
twice. An edited application produces a new digest and therefore a new
append-only receipt without erasing the earlier observation.

## State separation

```text
ISSUE_SUBMITTED
  -> TRANSPORT_PARSED
  -> {PASS | HOLD}
  -> EXTERNAL_IDENTITY_AND_INDEPENDENCE_REVIEW_PENDING
  -> COHORT_SOLVER_PENDING
  -> PACKET_ASSIGNMENT_PENDING
  -> GOVERNANCE_HOLD
```

A transport `PASS` proves only that the public object is well formed, bound to
the exact V15 batch and calls, and controlled by the key that validates both
declared signatures. It does not prove the human or institutional identity
behind that key, independence, fitness, selection, delivery, authority,
certification, or truth.

## Immutable anchors

```text
BASE_COMMIT::1b653e39d7c09ba8b93a800860244242cd98d397
BASE_TREE::d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b
BATCH_ID::V11-BATCH::c7e3ae7e8cfd126a75b41b4a
BATCH_ROOT::sha256:b9322c5950d562f7a3f437ed8c939d98506db4edf34446e8332318513bca46b5
CALL_MANIFEST_ROOT::sha256:fc82581375a195d09a58b7769eb33bba719c7f7e4b7ddd7b5276dcf1ce1d6219
```

## Live barrier

```text
FIVE_VALID_INDEPENDENT_BATCH_BOUND_APPLICATIONS_REQUIRED
```

The automation closes the ingestion-mechanics barrier. It does not fabricate
the five independent applicants needed to close the empirical participation
barrier.

```text
NEXT::KC144.V15::OBSERVE-REPLAY-AND-LEDGER-REAL-SUBMISSIONS
REENTRY::KC144.V1::GID144::M12
HEART_SUCCESSOR::KC144.HEART.SUCCESSOR::8334d289b464ffb89265ee5c4a6193fd
```
