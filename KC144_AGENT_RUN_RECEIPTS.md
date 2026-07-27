# KC144 — Content-Addressed Agent-Run Receipts

```text
LOOKUP_KEY::KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS
PARENT::KC144.V1::PARALLEL_ROUTE_CRYSTAL
ENTRY::GID003/H03/MYCELIAL_NAVIGATION_REGISTRY
SOURCE_BINDING::GID005/H05/SOURCE_EVIDENCE_VERSION_LEDGER
ACTIVATION::GID006/H06/ACTIVATION_REPLAY_RESEED_HUB
EXECUTION::GID135/M03/DETERMINISTIC_PARALLEL_WAVE_ENGINE
RECEIPT_INDEX::GID141/M09/PATH_SIGNATURE_REGISTRY
VERIFICATION_BOUNDARY::GID144/M12/SOLID_STATE_GATE
RETURN::GID001_PRIME
MAXIMUM_PARALLEL_WIDTH::5
BASE_GRAPH_MUTATED::FALSE
CONTENT_TRANSPORT_CERTIFIED::FALSE
GOVERNANCE_AUTHORITY_GRANTED::FALSE
PRODUCTION_TRUTH_EFFECT::NONE
```

This layer converts the parallel route compiler into an auditable run
protocol. It addresses every task, plan, input manifest, run, lease, result,
validation receipt, audit event, manifest, and complete bundle. Five
dependency-ready conflict-free simulations can execute concurrently; their
results enter the reducer only in the plan's canonical content-address order.

Physical worker count, completion order, wall-clock time, provider agent ID,
session ID, and process ID are operational telemetry. They do not enter any
canonical address. Consequently, capacities one through five produce
byte-identical receipt bundles when the normalized task results are identical.

## Identity graph

For canonical JSON function `C`, versioned domain `d`, and value `x`:

```text
A(d,x) = "sha256:" || SHA256(C({"domain":d,"version":1,"value":x}))
```

The transitive graph is:

```text
task bodies ─A(task)→ work IDs
       work IDs + frozen source ─A(plan)→ plan digest
plan + root input + semantic runtime policy ─A(run)→ run ID
run + work + attempt + logical slot ─A(lease)→ lease ID
lease + isolated output records ─A(result)→ result digest
validation + pre/post merge state ─A(receipt)→ receipt digest
ordered logical transitions ─A(event)→ hash-chained audit root
receipts + terminal states + audit root ─A(manifest)→ manifest digest
complete object graph ─A(bundle)→ bundle digest
```

Changing any addressed field changes its address and every transitive parent.
Git commit/tree coordinates bind a published runtime to the exact source
snapshot that it executed.

## Lease and merge law

Each attempt has one immutable logical lease. A result is accepted only when:

- run, plan, work, human task, attempt, lease, and input bindings match;
- the lease is current and not logically expired or superseded;
- artifact destinations are segment-covered by the declared write set;
- artifact base digests match the frozen base;
- expected and produced content digests agree;
- every required check passes;
- local execution is not substituted for a task requiring an independent
  agent; and
- the result claims no governance, transport, or truth effect.

Late and superseded results are quarantine-only. Retry is possible only for
the error codes frozen into the plan and only below the task's attempt limit.
There is no last-writer-wins rule.

## Canonical audit projection

Arrival order is buffered away. The audit chain is generated from logical
transitions:

```text
RUN_OPENED
PLAN_VALIDATED
CAPACITY_FIXED
for each dependency wave:
  EPOCH_OPENED
  WAVE_SELECTED
  for each work ID in canonical merge order:
    LEASE_GRANTED
    RESULT_RECEIVED
    RESULT_ACCEPTED | RESULT_REJECTED | RESULT_QUARANTINED
    SNAPSHOT_COMMITTED
RUN_COMPLETED | RUN_FAILED
```

Every event carries its sequence, logical epoch, subject address, and previous
event hash. Verification checks both hashes and the state-machine projection;
a self-consistent but unlawful event reorder still fails.

## Mycelium location

The tool is a content-addressed overlay on the existing KC144 graph. It adds no
seat and no bridge. An H06 lookup compiles these exact shortest routes:

| Role | Coordinate | Route from H06 | Standing |
|---|---|---|---|
| locate | `GID003/H03` | `006→001→002→003` | structural |
| bind source | `GID005/H05` | `006→005` | structural |
| activate/replay | `GID006/H06` | `006` | structural |
| execute waves | `GID135/M03` | `006→001→144→143→142→141→140→139→138→137→136→135` | declared; `BR019` open |
| index receipts | `GID141/M09` | `006→001→144→143→142→141` | declared; `BR019` open |
| verify/return | `GID144/M12` | `006→001→144` | declared; `BR019` open |

Location is not transport certification. M12 is the integrity verification
boundary for this run; it remains a production `HOLD` unless the wider
independent evidence and authority gates are separately satisfied.

## Executable surface

```text
kc144-crystal mycelium-tools
kc144-crystal mycelium-locate KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS
kc144-crystal agent-run-plan <parallel-route-snapshot.json>
kc144-crystal agent-run-receipts <parallel-route-snapshot.json> --workers 5 --output <bundle.json>
kc144-crystal agent-run-verify <bundle.json> --source <parallel-route-snapshot.json>
```

The systematic V3 compiler emits `tool_registry_v1.json`; every V4+ mycelium
compile inherits it and emits the default H06 location receipt plus the
receipt contract. Unknown or partial aliases return `NOT_FOUND` with no
executable command.

## Reference-run standing

The published reference run wraps the five deterministic route simulations
and one deterministic reducer. It records six accepted receipts and zero
independent witnesses. It demonstrates reproducible scheduling, addressing,
lease validation, merge isolation, audit closure, replay, and navigation. It
does not demonstrate external-agent independence, certified content transport,
governance authority, deployment, or production truth.

```text
NEXT_SEED::KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH
```
