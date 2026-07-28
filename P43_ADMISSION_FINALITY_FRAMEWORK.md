# KC144 P43 — Admission, Exactly-Once Finality, and Forward Watch

P43 is the complete executable successor to the frozen public P42 release. It
does not manufacture the three external inputs that P42 correctly left open.
It admits and revalidates them as one root-bound transaction, executes
`P41.EDGE.003` at most once, proves ledger finality by deterministic replay,
and evaluates only forward post-edge outcomes.

## Exact lineage

```text
LOOKUP::KC144.V4.4::MATH144.P43::ADMIT_EXACT_SOURCE_ENUMERATION_WITNESS_COMPLETE_NONLEAKING_HELDOUT_COHORT_RECEIVE_INDEPENDENT_IC10_AUTHORIZATION_EXECUTE_P41_EDGE_003_EXACTLY_ONCE_AND_EVALUATE_FORWARD_POST_EDGE_WATCH_MACROCYCLE_12
PUBLIC_PARENT::KC144.P42.CANDIDATE::57435ce8483f620adc52b3c6
PUBLIC_PARENT_RELEASE::sha256:57435ce8483f620adc52b3c6ddd02f4b69816d00ef5fbabe43a6b0ee657518c7
RETURN::KC144.V1::GID144::M12
```

## Whole-crystal transaction

The first four lanes bind P42 and independently revalidate exact enumeration,
the five-event nonleaking cohort, and the root-specific IC10 authorization.
The next four lanes execute, replay, finalize, and watch. The final two lanes
preserve the private label collision without disclosure and return to M12.

An execution record is valid only when all roots match, the source custodian
and IC10 authorizer remain independently controlled, the ledger contains no
prior execution, and the namespace is `PRODUCTION`. `TEST` can simulate the
same gates but cannot mutate the execution ledger. Once the ledger contains
one valid record, repeated requests return `ALREADY_EXECUTED_IDEMPOTENT`.

The post-edge watch is armed only by a real production record. It rejects
retroactive events, causal reuse of authorization-cohort events, continuation
events, and unsupported event classes. Edge execution changes neither
proposition truth nor general governance authority.

## Frozen release

The public reference release has no external witness, outcome cohort, or IC10
authorization. It therefore remains `CANDIDATE_HOLD`, with zero edge
executions, zero canonical mutations, an unarmed watch, production authority
`HOLD`, and truth effect `NONE`. The runtime includes positive production,
idempotency, simulation, missing-gate, tamper, lineage, and noncollapse tests;
those tests prove machinery, not external readiness.

## Exact implementation and verification receipt

```text
IMPLEMENTATION_COMMIT::704f9d525bcf0eec858939a1f2fc5cfc7e936ebc
IMPLEMENTATION_TREE::f7779ca4abe1a12f1096d49dd35bdc2f56b1cdfe
RESULT::KC144.P43.CANDIDATE::240473a1935faad593c1b8d5
RELEASE_DIGEST::sha256:240473a1935faad593c1b8d5ea74b7171cac43bfac63ad597e0161238c424aa2
REPOSITORY_TESTS::478_RUN_476_PASS_2_EXPECTED_SKIP
VERIFICATION_MATRIX::26/26_PASS
PRODUCTION_AUTHORITY::HOLD
TRUTH_EFFECT::NONE
```
