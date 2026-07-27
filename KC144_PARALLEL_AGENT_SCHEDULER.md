# KC144 — Deterministic Parallel-Agent Scheduler

```text
LOOKUP_KEY::KC144.V1::PARALLEL_AGENT_SCHEDULER
DEFAULT_WIDTH::5
PLANNING::CANONICAL-DAG
WORKERS::ISOLATED-PRODUCERS
MERGER::SINGLE-DETERMINISTIC-COORDINATOR
FALLBACK::SERIAL-SAME-ENVELOPES-SAME-OUTPUT
```

This scheduler turns one large objective into a dependency graph of bounded
work items. It spawns agents only for tasks that are independent under declared
read/write footprints. Sequential obligations remain explicitly ordered.

The scheduler optimizes throughput without changing epistemic standing:
parallelism allocates thought and tool time; it does not create evidence,
independence, authority, or truth.

## 1. Canonical task

```text
τ =
  <task_id,
   phase,
   instruction,
   dependencies,
   execution_mode,
   capabilities,
   read_set,
   write_set,
   priority,
   attempt_limit,
   output_contract,
   verification_commands,
   independent_agent_required>
```

Execution mode is one of:

- `PARALLEL_WORKER`: may share a wave with nonconflicting work.
- `SOLO_WORKER`: one child agent behind a global barrier.
- `COORDINATOR_ONLY`: mutation, authorization, integration, or final synthesis.
- `DETERMINISTIC_REDUCER`: pure ordered reduction over dependency outputs.

Task identity is content-addressed:

```text
work_id(τ) = SHA256(canonical_json(τ))
```

Once execution begins, agents cannot redefine the plan. A material plan change
terminates the run as `REPLAN_REQUIRED` and produces a successor plan digest.

## 2. Five-part decomposition

Every objective is tested for these five independently executable faces:

```text
T1::INVENTORY_AND_COORDINATE_LOCK
T2::FORMAL_OR_DOMAIN_ANALYSIS
T3::SCHEMA_AND_PROPERTY_LAWS
T4::IMPLEMENTATION_SHARDS
T5::VERIFICATION_AND_ADVERSARIAL_REPLAY
```

The five faces are not always concurrent. The dependency compiler determines
which form an antichain.

Example:

```text
T1
├── T2
├── T3
└── T4a,T4b,T4c
        └── T5
             └── INTEGRATE
```

`T2`, `T3`, and disjoint implementation shards may run together after `T1`.
`T5` cannot begin until its implementation dependencies terminate. Integration
is always coordinator-only.

## 3. Conflict relation

For task `a` with reads `R(a)` and writes `W(a)`, and task `b`:

```text
CONFLICT(a,b) ⇔
  W(a) ∩ (R(b) ∪ W(b)) ≠ ∅
  OR
  W(b) ∩ (R(a) ∪ W(a)) ≠ ∅
```

Resource equality includes directory-prefix overlap. Unknown or wildcard writes
conflict with everything. Read/read overlap is safe.

Plain-text line ranges are not stable ownership boundaries. Shared-file
parallelism requires a typed format and an explicitly registered deterministic
reducer.

## 4. Plan validation

Before spawning, the coordinator:

1. rejects duplicate or empty task IDs;
2. rejects self, missing, and cyclic dependencies;
3. normalizes all resource claims;
4. rejects path traversal, symlink escape, and undeclared wildcard mutation;
5. fixes worker capacity and attempt budgets;
6. freezes the input snapshot and canonical plan digest;
7. computes dependency ranks;
8. records capability requirements.

No task is eligible until every dependency is in an explicitly accepted
terminal state and its result digest is part of the task input manifest.

## 5. Deterministic wave selection

At logical epoch `e`:

```text
READY_e =
  {τ | pending(τ)
       ∧ dependencies_accepted(τ)
       ∧ capabilities_available(τ)}
```

The ready set is sorted by:

```text
(dependency_rank, priority, task_id)
```

The coordinator greedily chooses at most five mutually nonconflicting tasks.
Solo, coordinator-only, and reducer tasks form one-element waves.

Selected tasks all read the same frozen epoch snapshot. Results are buffered
until the wave terminates, then validated and reduced in selection order—not
completion order.

## 6. Agent lease

Each dispatched task receives one lease:

```text
lease_id =
  SHA256(run_id || task_id || attempt || logical_slot)
```

The lease binds:

- task and plan digest;
- immutable input snapshot;
- logical worker slot;
- attempt number;
- allowed resources and tools;
- output size and artifact limits;
- exact output schema;
- deadline policy.

One task has at most one live lease. A late result from an expired or superseded
lease is quarantined and never merged.

## 7. Worker envelope

Workers return one atomic result:

```text
ρ =
  <run_id,
   plan_digest,
   task_id,
   attempt,
   lease_id,
   input_manifest_digest,
   status,
   claims,
   artifacts,
   checks,
   diagnostics,
   result_digest>
```

Allowed statuses:

```text
SUCCESS
NO_CHANGE
BLOCKED
RETRYABLE_FAILURE
PERMANENT_FAILURE
```

Unvalidated partial prose is not merged. Claims must point to evidence inside
the envelope. Artifacts declare destination, base digest, result digest, and
semantic write key.

## 8. Coordinator validation

For each buffered result in canonical task order:

1. verify task, lease, attempt, and input bindings;
2. validate the result schema and byte limits;
3. reject undeclared writes and stale base digests;
4. stage artifacts outside the authoritative tree;
5. run task-local checks in declared order;
6. run global invariants;
7. accept or reject the envelope atomically;
8. merge accepted artifacts;
9. record the resulting snapshot digest.

No last-writer-wins resolution exists. Unequal values for the same structured
key are a conflict.

## 9. Retry law

Only enumerated transient failures retry:

- spawn or transport failure;
- expired lease;
- truncated envelope;
- retryable tool failure;
- merge conflict caused by an accepted base transition.

Permissions, policy refusal, false assertions, unsupported capabilities, and
permanent verification failures do not retry automatically.

Every retry gets a new lease and fresh input manifest. Speculative duplicate
workers and random ordering are forbidden.

## 10. Spawn fallback

If spawning is temporarily unavailable:

```text
PARALLEL_WORKER -> LOCAL_CANONICAL_EXECUTION
SOLO_WORKER     -> LOCAL_CANONICAL_EXECUTION
COORDINATOR     -> COORDINATOR
REDUCER         -> COORDINATOR
```

The local route passes through the same result envelope and validator.

If `independent_agent_required=true`, fallback is forbidden:

```text
SPAWN_UNAVAILABLE
  -> BLOCKED_CAPABILITY
  -/-> COORDINATOR_IMPERSONATION
```

Execution venue may change throughput, never acceptance semantics.

## 11. Canonical audit ledger

Every logical transition is hash-chained:

```text
RUN_OPENED
PLAN_VALIDATED
CAPACITY_FIXED
EPOCH_OPENED
WAVE_SELECTED
LEASE_GRANTED
RESULT_RECEIVED
RESULT_REJECTED | RESULT_ACCEPTED
SNAPSHOT_COMMITTED
RETRY_SCHEDULED | TASK_BLOCKED
RUN_COMPLETED
```

Wall-clock time, opaque provider IDs, and arrival order live in a separate
telemetry stream. They cannot affect the canonical audit root.

## 12. Reference algorithm

```text
VALIDATE plan
FREEZE input snapshot, capacity, limits, plan digest

WHILE nonterminal tasks exist:
    PROPAGATE blocked dependencies
    READY := canonically sorted eligible tasks
    IF READY is empty:
        FAIL DAG_STALLED

    WAVE := maximal bounded nonconflicting prefix of READY
    DISPATCH with leases, or enter declared serial fallback
    WAIT until every WAVE task terminates or expires

    FOR task IN canonical WAVE order:
        VALIDATE atomic result envelope
        STAGE authorized artifacts
        RUN declared checks
        ACCEPT+MERGE or REJECT+RETRY/BLOCK

FINALIZE manifest
VERIFY audit chain
REPLAY with worker capacities 1..5
REQUIRE identical canonical output
```

## 13. Required metamorphic tests

```text
SHUFFLED-TASK-INPUT        -> SAME WAVES
SHUFFLED-COMPLETION-ORDER  -> SAME MERGE
WORKERS 1,2,3,4,5          -> SAME RESULT DIGEST
READ/WRITE COLLISION       -> DIFFERENT WAVES
SOLO TASK                  -> SINGLETON WAVE
MISSING DEPENDENCY         -> FAIL CLOSED
DEPENDENCY CYCLE           -> FAIL CLOSED
UNDECLARED WRITE           -> REJECT RESULT
STALE BASE                 -> RETRY OR BLOCK
EXPIRED LEASE              -> REJECT LATE RESULT
SPAWN FAILURE              -> SERIAL SAME ENVELOPES
INDEPENDENCE REQUIRED      -> BLOCK, NEVER IMPERSONATE
AUDIT EVENT MUTATION       -> CHAIN FAILURE
```

```text
NEXT::KC144.V1::PARALLEL-AGENT-RUN-RECEIPTS
RETURN::KC144.V1::PARALLEL_ROUTE_CRYSTAL
PARENT::KC144.V1::DEPENDENCY-AWARE-FIVE-WAVE-EXECUTION
```
