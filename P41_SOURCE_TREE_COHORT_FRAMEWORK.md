# KC144 P41 — Source-Tree / Held-Out Cohort / Third-Edge Boundary

P41 executes the complete successor wave named by the frozen public P40
release. It reconstructs and hydrates the historical 29-head source cohort,
publishes only one-way commitments, pins the current public
`AthenachkaCollective` repository trees, freezes a label-sealed held-out cohort,
verifies an independently enrolled IC10 return, and executes the third proposal
edge exactly once only when every gate is present.

The frozen reference release is an honest `CANDIDATE_HOLD`: source and
repository mechanics are complete, while the held-out cohort and independent
IC10 authority are absent.

## Exact lineage

- Lookup key:
  `KC144.V4.2::MATH144.P41::HYDRATE_REMAINING_22_BODY_HEADS_BIND_CURRENT_REPOSITORY_TREES_FREEZE_NONLEAKING_HELDOUT_COHORT_EXECUTE_THIRD_EDGE_ONLY_IF_ELIGIBLE_AND_RECEIVE_INDEPENDENT_IC10_RETURN_MACROCYCLE_10`
- Public parent:
  `KC144.P40.CANDIDATE::8343b08a8ee5152ed117f281`
- Public parent release:
  `sha256:8343b08a8ee5152ed117f28189c3172c7a56e8d9912e004b8ea8461c5bb18150`
- Public parent commit:
  `ba252f77832520f069ff84af45982df2fdab6017`
- Public parent tree:
  `92ac9565b2f6e229722faf2a4b02e543ab07072e`
- Typed source-fiber predecessor:
  `KC144.P40::f07bae53d9e157e9e8e54473`
- Source-fiber predecessor parent:
  `KC144.P39::9a0a228dc74f001e64507417`
- Return: `KC144.V1::GID144::M12`

The public P40 parent and source-fiber P40 are different lineages. P41 binds
both without merging their parents or renumbering either result.

## Source-body closure

The earlier source-fiber artifact retained the census `29 total / 7 resolved /
22 unhydrated`, but did not publish the original 29 document locators. P41
therefore performs a revision-aware reconstruction:

```text
lower bound, exclusive: 2026-07-28T01:37:13.494Z
upper bound, inclusive: 2026-07-28T05:00:00.000Z
matching historical revisions: 29
retrieved bodies: 29
content-bearing bodies: 27
exact empty bodies: 2
transport residuals: 0
net aggregate gap closed: 22
```

This closes the aggregate hydration gap but does not invent an original
enumeration witness. The public manifest contains only:

```text
source slot
one-way locator commitment
one-way body commitment
CONTENT | EXACT_EMPTY
```

It publishes zero raw document IDs, titles, revision IDs, timestamps, authors,
or body bytes. Its exact root is:

`sha256:2d9606c0d13a85095278acc77e4b237da3131202ea3702190ec8d09b27f240bb`

## Current public repository forest

P41 binds commit identity and Git tree identity separately for the four public
repositories visible under `AthenachkaCollective`:

| Repository | Commit | Tree | Paths |
| --- | --- | --- | ---: |
| `AthenachkaCollective/Athenachka` | `e97663e81f7c464a7a53383c796cc09226776422` | `f3c07ab1be604aed3610e51b48ff944c303448c6` | 39 |
| `AthenachkaCollective/Athenachka-Nexus` | `0122591467a9f164848b60389ccadeb49801f19e` | `bce1537e9261816dc35235c72e85e550dc93ee38` | 33 |
| `AthenachkaCollective/Athenachka-Collective` | `26921c516c7554285d8e952b87168e536f05972c` | `6293abdafd0ffdb0b32a0da54576acebecf3367c` | 26 |
| `AthenachkaCollective/AthenachkaCollective` | `394597e22e2ff89c3476b5a368d4c49544b83473` | `a0ffb3f0c48c7042514fb688d3f9e8b1f164212e` | 1 |

Forest root:

`sha256:e2cef08dbec713419c70d1b9632ed1697b302d70b81aeaccef50f211344d0cef`

A repository head is not a tree, and a bound tree is not a merge, deployment,
or authority grant.

## Nonleaking held-out cohort

P41 accepts only sealed `TASK_OUTCOME` and `EMPIRICAL_RESULT` events observed
strictly after `2026-07-28T07:15:00.000000Z`. A ready cohort requires:

- at least five deduplicated events;
- at least two outcome classes;
- at least three source surfaces;
- at least three routes;
- no revealed evaluation labels; and
- no continuation-only events.

A repeated `next` cannot enter this cohort. The empty frozen reference cohort
has root:

`sha256:32c39e8e130b32168cbc54c1e14485e3afb3647fd28b7b87273f775e711083a1`

## Independent IC10 return

The IC10 gate requires an external registry entry with a unique signer,
organization, control root, validity window, raw Ed25519 public key, and signed
proof of key control. An authorization return must then sign and exactly bind:

- the third-edge candidate root;
- the source commitment manifest root;
- the public repository forest root;
- the sealed held-out cohort root;
- signer, organization, and control root;
- scope and verdict;
- issue/expiry window; and
- unique nonce.

An enrolled signature with mismatched roots, scope, organization, control root,
validity window, or nonce remains rejected. The frozen release has zero registry
entries and zero accepted independent returns.

## Third-edge transaction

The exact candidate is:

```text
P41.EDGE.003
KC144.V1::GID084::I04
  <- BIDIRECTIONAL_CAUSAL_ABLATION ->
KC144.V1::GID047::F04
```

The execution law is:

```text
29 source commitments retrieved with zero transport residual
  + four exact public commit/tree bindings
  + five-event diverse nonleaking held-out cohort
  + one registry-bound independent IC10 authorization
  -> execute the copied-proposal-graph edge exactly once
```

The test namespace exercises the successful transaction without production
mutation. The production namespace records one graph mutation only when all
four gates pass. Otherwise it emits `HELD_NOT_EXECUTED` and zero mutations.

## Nine-lane macrocycle

1. Bind the exact frozen public P40 parent.
2. Bind the divergent source-fiber P40 as a typed predecessor, not a parent.
3. Verify all 29 anonymous source commitments and the 22-head aggregate closure.
4. Bind the four public repository commit/tree pairs.
5. Freeze and validate the nonleaking held-out cohort.
6. Verify registry enrollment and independent IC10 return.
7. Evaluate and, only if eligible, execute the third edge once.
8. Preserve the separate Git-Brain P41 label without publishing its private
   locator or merging it into this lineage.
9. Reduce receipts and return to M12.

## Frozen reference roots and state

- Contract:
  `sha256:f13b8f2c33e99f343f214e2fe6eeb8a57559f73e8ffa18922b8a7ade95c4c244`
- Edge candidate:
  `sha256:e90c498739dbf13933796d34391a0ec4ba1db25e800cf686c78a728485d339ed`
- IC10 evaluation:
  `sha256:3c8b21d35a8c5a0247665655ab160167f734835fb7808b59c23cf58c4d2d5fdb`
- Third-edge execution:
  `sha256:5af65445159d8c844295d315d6d26057820bcf144d6de27f2468207cb74b048e`
- Macrocycle:
  `sha256:dc4655b753026707a6a1011c0e1348c30be8e5c0bac3ae790f34197606e4a7b9`

Frozen state:

```text
SOURCE_HEADS_REHYDRATED::29
NET_SOURCE_HEADS_CLOSED::22
PUBLIC_REPOSITORY_TREES_BOUND::4
HELDOUT_OUTCOMES::0/5
INDEPENDENT_IC10_RETURNS::0
THIRD_EDGE::HELD_NOT_EXECUTED
CANONICAL_GRAPH_MUTATIONS::0
PARALLEL_P41_MERGES::0
DEPLOYMENTS::0
PROMOTIONS::0
PRODUCTION_MUTATED::false
TRUTH_EFFECT::NONE
GLOBAL_RELEASE::HOLD
```

This is a complete executable boundary with incomplete external evidence.

## Frozen candidate receipt

- Implementation commit:
  `dab8df8ce76c3f58ee0df8501719e384e95872f7`
- Implementation tree:
  `bdb136a38990b4f2cc9d889e339826d630fd9b05`
- Result:
  `KC144.P41.CANDIDATE::482d03a3ff02af3e5656468d`
- Release digest:
  `sha256:482d03a3ff02af3e5656468d345e6ece6fb40f2daaaa0a508d38b6042a4eb1c9`
- Frozen state: `CANDIDATE_HOLD`
- Verification: `PASS`

## Successor

`KC144.V4.3::MATH144.P42::BIND_EXACT_SOURCE_ENUMERATION_WITNESS_INGEST_FIRST_FIVE_NONLEAKING_HELDOUT_OUTCOMES_RECEIVE_EXTERNAL_IC10_EDGE_AUTHORIZATION_EXECUTE_THIRD_EDGE_ONCE_AND_FREEZE_POST_EDGE_WATCH_MACROCYCLE_11`
