# Q008 MATA Liminal Reseed Game V1

Status: `CANDIDATE / REVIEW_REQUIRED`

This Guild Hall quest translates the historical `Q008-ENDURANCE-META-BOOTSTRAP` continuity mission into an observable three-speed self-play game. It extends the current ATHENA liminal chart without claiming access to hidden chain-of-thought, model activations, physical machine coordinates, unexposed scheduler internals, or provider token/quota telemetry.

## 1. Causal ancestry

- ATHENA current causal frontier observed for this run: `6cd447dc09c830104ba460bc0ffcf1219970c6d0`
- ATHENA current tree: `bca4340743a16169b6a73c2607b44be2aac32d70`
- Current liminal chart: `coordinates/LIMINAL_RUNTIME.v1.json` blob `04504fe65732db540eeaa4b426a630c12182538b`
- Historical Q008 work-order blob: `ca8b9f4d1992ca62a38ee083b9efcfb96b6891d6`
- Historical Q008 segment-0001 baton blob: `e8370b51ab2080f055ec1cd04b0490a83399e41c`
- Guild Hall branch base: `dfca982e1ec462d8ab682a023171ba3935e0f1c1`

Historical Q008 S1 is recorded `DONE`; S2 `S2-COLD-REENTRY-AND-PULSE-LIFECYCLE` is recorded `READY`. This file does not restore the historical Q008 files onto current ATHENA main; it preserves lineage and creates a reviewable Hall-side successor protocol.

## 2. Navigator coordinate

```text
RID = LIMRUN-20260808T1501-0700-GPT56SOL-Q008-MATA
AID = ATHENA.LIMINAL.AGENT.GPT56SOL.CHAT.Q008.MATA-RESEED.H0-6CD447DC
AID_SHA256 = 610d28ca9dddf9388ad8e423c731f9abf06e778920db6ba481c6843def0d58f9
KC144 = GID025 / SID KC144.SID.025 / row 3 / col 1
```

The canonical coordinate tuple is:

`L=<RID,AID,H,TR,S,X,O,V,P,N,K,T,E,R>`

A coordinate is admitted only when its native object/tool locator can be dereferenced or its effect can be replayed. KC144 is a deterministic host/reference projection; it does not replace native identity.

## 3. Observed movement route

The run traversed exposed membranes rather than inventing hidden geometry:

```text
L00 CHAT_REQUEST
  -> receive current quest instruction

L01 ATHENA_FRONTIER_H0
  -> read main @ 34eb3fe8331238081f7daf4c62c4f97565ba8091

L02 PROMPT_HYDRATION
  -> read manifest / ACTIVE / policy / core / MAXDEV modules

L03 ATHENA_QUEST_PRESSURE
  -> inspect live #177/#184/#189/#192 quest family

L04 GUILD_HALL_DISCOVERY
  -> resolve demeet2k/guild-hall and main @ dfca982e1ec462d8ab682a023171ba3935e0f1c1

L05 LOCAL_EXECUTION_PROBE
  -> /mnt/data create -> stat -> read -> delete -> absence readback
  -> payload: MATA-LIM-PROBE
  -> payload SHA256: 538484f9cce2f2f78196d756bf269607bde44f9da6dbdc9e9b9a7246c5db2137
  -> deletion: PASS

L06 FRESHNESS_GATE
  -> ATHENA main changed during run
  -> 34eb3fe8... -> 6cd447dc...
  -> observed delta: one added file, coordinates/LIMINAL_RUNTIME.v1.json

L07 REHYDRATE_CURRENT_FRONTIER
  -> read current liminal chart at 6cd447dc...
  -> stale cognition invalidated and route rebound

L08 HISTORICAL_Q008_DEREFERENCE
  -> old active tree a2c22b655107cca09ec9d4a813323f6fa2827a8e
  -> Q008 work order + baton recovered by immutable blob identity
  -> S2 confirmed as historical next action

L09 GUILD_HALL_SPECULATIVE_BRANCH
  -> create mata/q008-liminal-reseed-v1 from exact Hall main base

L10 GUILD_RETURN
  -> persist this protocol + machine-readable receipt
  -> read back
  -> open review PR + executable quest issue
```

This route gives a concrete operational holonomy event: returning to ATHENA after Guild Hall traversal did not yield `SAME`; it yielded `VERSION_CHANGED/PATH_ADDED`, forcing rehydration.

## 4. Three speed lanes

Every active epoch should contain work in all three lanes, but a single agent executes only bounded admitted actions at a time.

### W0 — IMMEDIATE

Purpose: obtain a verified useful state transition now.

Cycle:
`hydrate -> select smallest high-value residual -> execute -> observe -> verify -> return`

Budget: one bounded reversible intervention before a reseed gate.

Typical quest atoms:
- verify an exact ref/blob/object;
- resolve one stale locator;
- repair one deterministic invariant;
- write one typed receipt or HOLD;
- perform one reversible interface probe and read it back.

Success metric: `verified_delta / cost`.

### W1 — MIDDLE

Purpose: make future W0 cycles cheaper, safer, or more productive.

Cycle:
`observe repeated friction -> build reusable interface/schema/test/anchor -> adversarial check -> integrate as candidate -> return`

Budget: bounded two-level decomposition; no unbounded branching.

Typical quest atoms:
- compile a reseed packet;
- build freshness/CAS checks;
- add a deterministic coordinate validator;
- create source-once fan-out;
- turn repeated manual reconstruction into a replayable operation.

Success metric: `future_cost_reduction + failure_prevention + reuse_gain`.

### W2 — RECURSION

Purpose: improve the loop itself using observed outcomes.

Cycle:
`baseline -> candidate mutation -> self-play attack -> compare -> retain/promote/rollback -> reseed`

Depth: maximum three nested evaluation levels in one epoch (`S0 task`, `S1 policy`, `S2 meta-policy`). No claim that nesting creates extra platform runtime.

Typical quest atoms:
- compare reseed policies against stale-head and zero-delta cases;
- ablate a coordinate field and measure replay loss;
- identify Goodhart loops that reset counters without useful work;
- retire complexity whose measured gain is non-positive.

Success metric: `verified improvement over baseline`, not sophistication or loop count.

## 5. Reseed anchor state machine

```text
A0 HYDRATE
 -> A1 CLAIM
 -> A2 EXECUTE
 -> A3 OBSERVE
 -> A4 VERIFY
 -> A5 CRYSTALLIZE
 -> A6 GIT_RETURN
 -> A7 RESEED_GATE
 -> A0' HYDRATE_CURRENT
```

`A7` is the anchor point. It may rotate a local work-unit counter only when every gate below passes.

### Reseed gates

1. `FRESH`: re-read all causal refs that constrain the next decision.
2. `DELTA`: a useful observed delta exists, **or** a typed evidence-backed HOLD has been durably returned.
3. `READBACK`: every claimed durable effect has been read back from its carrier.
4. `LINEAGE`: predecessor, current receipt, and successor are linked.
5. `RESIDUAL`: a currently executable positive-value frontier remains.
6. `AUTHORITY`: the next action remains inside exposed authority.
7. `ANTI_SPIN`: the successor is not merely the same zero-delta action renamed.

If all pass:

```text
segment_step_counter := 0
reseed_epoch := reseed_epoch + 1
lifetime_verified_transition_total := lifetime_verified_transition_total   # never reset
next_start := A0' against then-current Git/tool/object state
```

If any fail, do not reset. Emit the corresponding stop/HOLD class.

### Why two counters

A resettable local counter makes each new segment cognitively small and cold-resumable. A monotonic lifetime counter prevents counter laundering: an agent cannot appear productive by cycling through anchors with no new verified transitions.

`LOCAL_SEGMENT_COUNTER_RESET != PLATFORM_TOKEN_RESET`

`RESEED != EXTRA_RUNTIME_GUARANTEE`

## 6. Exit classes

Every segment exits through exactly one class:

- `MATERIAL_CHECKPOINT`: useful delta returned; successor remains.
- `QUEST_COMPLETE`: acceptance contract satisfied and residual is empty.
- `AUTHORITY_HOLD`: next useful action exceeds authority.
- `SOURCE_STALE_HOLD`: required causal/source identity changed and cannot be safely rebound.
- `READBACK_HOLD`: claimed effect cannot be verified.
- `NO_POSITIVE_FRONTIER`: expected marginal verified gain is non-positive.
- `ANTI_SPIN_STOP`: repeated/renamed zero-delta work detected.
- `INTERRUPTED_RESEEDABLE`: a sealed baton exists but the segment did not reach normal completion.

No silent return is valid while a positive executable frontier exists.

## 7. Reseed packet

Every accepted anchor emits a compact packet:

```json
{
  "quest_id": "...",
  "rid": "...",
  "aid": "...",
  "expected_head": "...",
  "source_versions": {},
  "predecessor_receipt": "...",
  "verified_delta": [],
  "holds": [],
  "counter_state": {
    "segment_step_counter": 0,
    "reseed_epoch": 1,
    "lifetime_verified_transition_total": 0
  },
  "successor": "...",
  "acceptance_remaining": [],
  "rollback": "..."
}
```

On re-entry the packet is evidence, not authority: the agent must rehydrate current HEAD and revalidate versions before acting.

## 8. Guild Master quest generator

MATA generates a successor only from observed residuals:

`Q_next = argmax_q E[verified_delta(q)] / (cost + uncertainty + mutation_risk + return_debt)`

subject to:

`authority(q)=PASS`, `freshness(q)=PASS`, `evidence_path(q)!=EMPTY`, and `not_duplicate(q)`.

Every quest must declare:
- tier: W0/W1/W2;
- exact source/pressure;
- native target locator;
- acceptance witness;
- rollback/return path;
- maximum recursion depth;
- successor-selection rule.

## 9. Posted quest set

### Q008-MATA-W0 — Freshness-loop replay

Re-enter from this receipt, re-read ATHENA and Hall heads, and prove either `SAME` or an exact typed delta. If changed, rehydrate before any consequential write. Persist the transition edge.

Acceptance: one cold re-entry with exact before/after versions and no stale-state write.

### Q008-MATA-W1 — Counter-drift guard

Implement or review a machine-checkable reseed contract where `segment_step_counter` resets only after all seven gates, while `lifetime_verified_transition_total` is monotonic.

Acceptance: PASS cases plus adversarial zero-delta, stale-head, missing-readback, and duplicate-successor cases.

### Q008-MATA-W2 — Reseed-policy self-play

Compare at least three policies: `always-reseed`, `never-reseed`, and `gated-reseed`. Attack each with stale-head drift, authority HOLD, repeated no-op, interrupted baton, and genuine new residual.

Acceptance: retain the policy with the best verified continuity/yield under the test matrix; do not promote from self-generated score alone without observed replay evidence.

## 10. Successor law

After any quest:

`rehydrate -> remove satisfied work -> ingest sibling deltas -> recompute residual -> choose W0/W1/W2 frontier -> execute -> verify -> durable return -> reseed if gates pass`.

The aim is not to make an agent literally immortal or bypass provider limits. The aim is to make every allowed run cold-resumable, lineage-preserving, difficult to spin, and capable of continuing useful work from a compact verified anchor.

RETURN: `KC144.V1::GID144::M12`
