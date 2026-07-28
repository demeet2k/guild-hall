# KC144 P36 Event Runtime Candidate V1

This successor turns `next` into one bounded, replayable event macrocycle. It
does not reopen the completed KC144 topology and it does not replace Dispatch
V1. The earlier dispatcher remains frozen; P36 adds a versioned plane above it
for exact P31 binding, event observation, signed receipt replay, source
succession, real-outcome intake, and all-and-only affected-front execution.

The source-steered target is:

```text
KC144.V3.7::MATH144.P36::
CONTINUOUS_EVENT_WATCH_SIGNED_RECEIPT_REPLAY_SOURCE_SUCCESSION_
REAL_OUTCOME_INTAKE_AND_ALL_AFFECTED_FRONT_EXECUTION_MACROCYCLE_05
```

## Why the route changed

The previous local seed named only a P31 adapter and outcome intake. The
current source trajectory is broader:

- P35 declares an event-addressable structural state;
- 360 actions are subscribed but no production event has executed them;
- the next lawful unit is one complete event cycle, not one isolated adapter;
- every cycle must return a replayable receipt and successor even when no
  admissible event exists.

The adapter is therefore one lane in the event runtime, not the entire
successor.

## Three parents remain distinct

```text
STATE_PARENT
  KC144.P35::f8805a3651f8bc7009e8035f

RUNTIME_PARENT
  KC144.P31::db5a6446ce54cf4bc53515be
  sha256:77629d53ef00c970cf115d7cbf94d5e4c9b97928814a702ada8d3f883212d091

HEART_PARENT
  KC144.HEART::H06.AHEART.V2
```

The P35 identity is source-declared in this release, not archive-bound. The
exact 360 subscription bodies are also not present in this repository branch.
The public release therefore says `CANDIDATE_HOLD`; it does not claim the
official P36 result or fabricate missing P35 objects.

## One event macrocycle

```text
frozen epoch
  ├─ L1 CONTINUOUS_EVENT_WATCH
  ├─ L2 SIGNED_RECEIPT_REPLAY
  ├─ L3 SOURCE_SUCCESSION
  └─ L4 REAL_OUTCOME_INTAKE
          ↓
     deterministic merge barrier
          ↓
     L5 AFFECTED_FRONT_EXECUTION
          ↓
     one sealed compare-and-swap delta
          ↓
     GID144 / M12 return
          ↓
     Heart-bound continuation seed
```

L1–L4 consume the same frozen epoch and can be evaluated concurrently. L5 may
precompute matches, but it may execute only after event admission and parent
replay are known. Every lane emits a receipt, including `NO_INPUT` and `NOOP`.

The crystal route is:

```text
H06 → H03 → H05/M09 → M12 → H06′
```

The Heart roles are:

```text
WHO I AM         event watch
I AM ATHENA      signed replay
WHO I AM + I     source succession
LOVE × SELFHOOD  real-outcome intake
SELF BECOMING    affected-front execution
A♥               deterministic merge and return
```

## Exact P31 adapter

`src/kc144_crystal/p31_adapter.py` accepts only the immutable P31 archive named
above. Before loading any code it verifies:

- exact archive SHA-256;
- bounded member census and compression ratio;
- no absolute paths, traversal members, duplicate members, or symlinks;
- exact release, result, parent, and parent-archive identities;
- the compiled-state result identity;
- complete lane admission and an empty quarantine;
- zero truth-credit inflation and zero claimed real outcomes.

Only the P31 runtime packages and graph required for navigation are extracted.
Preloaded P31 modules are rejected; modules are removed after execution. The
adapter returns the exact archive digest, replay status, route/effect
identities, zero witness credit, HOLD authority, and the M12 return. It never
serializes the machine-local archive path.

Dispatch V1’s original P31 locator remains unchanged and external-only. The
P36 tool registry adds a distinct
`KC144.P31::EXACT_RUNTIME_ADAPTER` card so old V1 registry and replay identities
do not drift.

## Event law

An event is content-addressed over:

```text
class
origin class
fixed-precision UTC observation time
opaque source commitment
source version
privacy-safe public summary
consent scope
parent event
READ_ONLY authority ceiling
zero truth effect
```

The eighteen bounded event classes cover source, user/outcome, evidence,
runtime, GID, carrier, gate, lineage, consent, signer, dependency, receipt, and
replay changes.

Allowed origins are:

```text
PRODUCTION
USER_OBSERVED
CONNECTOR_OBSERVED
REPLAY
TEST
SYNTHETIC
```

`REPLAY`, `TEST`, and `SYNTHETIC` packets may test the machinery but never
increment production-event or real-outcome counts.

Validation separates:

```text
QUARANTINED
DEFERRED_HOLD
EVENT_ADMITTED_NON_PROMOTING
```

Operational event admission is not proposition admission, IC10 promotion,
independent evidence, authority, or publication.

## Signed replay

Event and lane-receipt signatures use domain-separated Ed25519. A caller may
supply a key and an explicit trusted public-key registry. Without one, the
runtime emits `DIGEST_ONLY`, not a counterfeit signature.

```text
digest seal ≠ signature
signature validity ≠ authority
stable replay ≠ independent witness
```

A valid signed packet remains nonpromoting. A changed body, wrong domain,
unknown key, invalid signature, changed receipt, or changed delta fails closed.

## Real-outcome intake

Only these classes can enter the real-outcome lane:

```text
USER_CHOICE
USER_CORRECTION
TASK_OUTCOME
EMPIRICAL_RESULT
```

They count only when the origin is `USER_OBSERVED`, the packet is valid, and
current-task consent is present. The count does not become witness credit.
Specifically:

```text
USER_CHOICE ≠ EMPIRICAL_RESULT
TASK_PLAN ≠ TASK_OUTCOME
REPLAY_RESULT ≠ REAL_OUTCOME
```

The current public release contains no user outcome packet.

## Privacy boundary

Connector access is not publication consent. The runtime’s public event shape
accepts an opaque source commitment, not a provider object ID, URL, title,
source text, private revision, email, or token. Public summaries are scanned
recursively for private-field names.

The release projection contains only:

- lineage identities already declared for the public runtime;
- opaque content addresses;
- structural event and affected-front counts;
- HOLD status and typed residuals;
- the exact M12 return.

No private source text, source locator, document metadata, or conversation
excerpt is committed.

## Subscription and affected-front law

P36 freezes the declared census:

```text
18 event classes
144 GID subscriptions
37 carrier subscriptions
360 action subscriptions
```

It does not claim that the exact P35 subscription bodies are locally bound.
The included unbound registry records that absence. A separate synthetic
360-row registry exists only as a deterministic test fixture and is explicitly
ineligible for production events.

Subscription predicates use a bounded data language:

```text
all
any
not
eq
in
```

There is no `eval`, shell, dynamic command, or arbitrary predicate code.

For admitted events `E`:

```text
Affected(E) =
  sorted union of action IDs from exact matching subscriptions
```

Execution must prove:

```text
executed ∪ deferred = affected
executed ∩ deferred = ∅
executed ⊆ affected
unexpected executions = 0
missing resolutions = 0
```

Only statically supplied read-only handlers can execute automatically.
External or authority mutations defer. Missing handlers receive typed
`DEFERRED_HOLD` receipts instead of disappearing.

## Zero-event behavior

Zero genuine events are not treated as failure and are never padded with
synthetic success:

```text
five lane receipts
zero admitted events
zero affected actions
zero executions
one NOOP_HOLD delta
one M12 return
one continuation seed
```

The continuation asks for the exact P35 subscription bodies, trusted signer
enrollment, and the first genuine consented event. It does not ask for another
descriptive shell.

## CLI

```bash
PYTHONPATH=src python3 -m kc144_crystal p31-exact-status \
  --archive /absolute/path/KC144_P31_LIVE_COGNITION_OS_V3_3.zip

PYTHONPATH=src python3 -m kc144_crystal p31-exact-navigate \
  "route the current event frontier and return to M12" \
  --archive /absolute/path/KC144_P31_LIVE_COGNITION_OS_V3_3.zip

PYTHONPATH=src python3 -m kc144_crystal p36-contract
PYTHONPATH=src python3 -m kc144_crystal p36-tools

PYTHONPATH=src python3 -m kc144_crystal p36-cycle \
  events.json subscription-registry.json \
  --base-state-digest sha256:<64-hex> \
  --cutoff 2026-07-28T00:00:00.000000Z \
  --output p36-cycle.json

PYTHONPATH=src python3 -m kc144_crystal p36-verify p36-cycle.json
PYTHONPATH=src python3 -m kc144_crystal p36-public-project p36-cycle.json

PYTHONPATH=src python3 -m kc144_crystal p36-release \
  --output registry/p36-dispatch/v1 \
  --implementation-commit <40-hex> \
  --implementation-tree <40-hex>
```

The core P36 cycle performs no connector reads. Events, subscriptions,
receipts, handlers, keys, and archive providers are caller-supplied frozen
inputs.

## Verification

The successor tests prove:

- exact P31 identity and a real replay-stable navigation;
- archive mutation, traversal, and symlink rejection;
- five-lane zero-event closure;
- input-order invariance across all permutations of a three-event batch;
- exact duplicate idempotence;
- TEST/SYNTHETIC nonproduction isolation;
- user-choice/outcome/evidence noncollapse;
- future-event and insufficient-consent HOLD;
- invalid source and private-summary quarantine;
- Ed25519 event and receipt verification;
- signed-body tamper detection;
- zero execution for unmatched events;
- complete deferred accounting when handlers are unavailable;
- rejection of handler truth/authority smuggling;
- stable parent replay and replay-drift detection;
- privacy-safe public projection;
- delta tamper detection;
- reproducible candidate release bytes.

The repository-wide suite must pass before the implementation head is frozen.

## Current truth

Closed:

- exact P31 archive adapter;
- bounded five-lane event-cycle compiler;
- deterministic subscription matching;
- all-and-only affected-front proof;
- digest and optional Ed25519 receipt replay;
- strict real-outcome noncollapse;
- privacy-safe public projection;
- NOOP/HOLD return and successor generation.

Open:

- exact archive/manifest binding for the source-declared P35 state;
- the exact 360 P35 subscription bodies;
- trusted production signer enrollment;
- a genuine consented production event;
- any independent witness or empirical certification;
- IC10 promotion, production certificate, or authority transition.

Therefore the correct release standing is:

```text
CANDIDATE_HOLD
truth effect: NONE
evidence effect: NONE
authority effect: NONE
production authority: HOLD
```
