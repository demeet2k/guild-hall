# KC144 Mycelium-Locatable Tool Dispatch V1

`KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH` closes the gap between locating a
KC144 tool and safely invoking it. It is an additive execution overlay over the
published content-addressed agent-run receipt release. It does not rewrite the
144-seat crystal, certify a transport bridge, promote evidence, create an
independent witness, or grant governance authority.

## Exact lineage

The immutable publication parent is:

- commit `4f3bd71a1e88130109edd03437b72f21c0e14096`;
- tree `c15740c445baa1f98e20b3172fb8637c9b44271a`;
- runtime commit `91cf0e3c2e8da10ed0787ebf1c0c0105aaf988a9`;
- runtime tree `bc44c4f14b25894a8251e8c1289b718e04eef32a`;
- parent run `sha256:0277d691593684417720414f2a2fd00436811e86d946cdc4eb2b1c0e975beb04`;
- parent bundle
  `sha256:52b8b2896a7bd1fff45dc3df84ac031172a3bc469375e3d3c775c8e9cb0aef59`.

The P31 live-cognition sidecar remains a distinct lineage:

- release `KC144_P31_LIVE_COGNITION_OS_V3_3`;
- result `KC144.P31::db5a6446ce54cf4bc53515be`;
- archive
  `sha256:77629d53ef00c970cf115d7cbf94d5e4c9b97928814a702ada8d3f883212d091`;
- structural parent `KC144.P30::1f40beaa81e8c0ba956ce835`.

P31 is registered as an exact locator-only tool card. Dispatch returns
`E_EXTERNAL_RUNTIME_REQUIRED` rather than silently substituting a local
implementation.

## Whole dispatch crystal

The outer route is:

```text
H06 / GID006  ingest and activate
      ↓
H03 / GID003  resolve the exact tool card
      ↓
H05 / GID005  bind source and implementation heads
      ↓
M09 / GID141  index route, plan, result, and audit identities
      ↓
M12 / GID144  verify, return, and emit the successor
```

The dispatcher does not walk this route as a prose checklist. It compiles the
whole object and runs five independent preflight lanes as one width-five wave:

1. `IDENTITY` checks request, registry, tool-card, operation, and handler
   identity.
2. `SOURCE_HEAD` checks the immutable implementation, publication-parent, and
   source heads.
3. `CAPABILITY` proves that every operation capability is inside both the
   caller ceiling and card ceiling.
4. `ROUTE_RETURN` proves route budget, returnability, and KC54 exact retrace.
5. `AUTHORITY_EFFECT` proves that truth, authority, witness, and transport
   effects remain zero.

A deterministic reducer joins the five reports. M12 then seals the result and
return receipt. Physical capacities from one through five produce the same
canonical bytes because worker count, arrival order, wall clock, process
identity, and provider identity are excluded from the address law.

## Identity graph

All identity objects use canonical UTF-8 JSON with sorted keys and
domain-separated SHA-256:

```text
head registry
    ↓
tool registry → tool descriptor
    ↓
input manifest → dispatch request
    ↓
five preflight reports → dispatch plan
    ↓
registered handler output
    ↓
four-event audit chain + KC54 holonomy receipt
    ↓
dispatch result → cold replay verification
```

Every digest authenticates the complete preceding body except its own digest
field. No timestamp or machine-local path is part of canonical identity.

“Authoritative head” means only the selected public code identity for replay.
It does not mean governance authority.

## Resolution law

Resolution is deliberately narrow:

1. accept a byte-exact stable lookup key;
2. otherwise accept one complete NFKC-normalized alias;
3. otherwise return `NOT_FOUND`.

Normalization lowercases, maps runs of spaces, underscores, or hyphens to one
space, and trims. There is no prefix match, substring match, edit distance,
embedding similarity, or “nearest tool” fallback. An alias collision blocks the
registry; it never chooses a winner.

The initial registry contains four cards:

- `KC144.V1::PARALLEL_ROUTE_CRYSTAL`;
- `KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS`;
- `KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH`;
- `KC144.P31::LIVE_COGNITION_NAVIGATE`.

The first three bind only to static in-process handlers. The fourth is an exact
external-runtime locator and is fail-closed by design.

## Execution boundary

Descriptor `commands` are documentation and CLI templates. The core dispatcher
never executes them. It contains a closed mapping from exact handler IDs and
exact operation names to Python callables:

```text
kc144.parallel-routes.v1
    compile

kc144.agent-receipts.v1
    plan
    run
    verify

kc144.tool-dispatch.v1
    registry
    locate
```

There is no shell, subprocess, dynamic import, `eval`, command interpolation,
or fallback from one handler to another. Unknown tools, unknown operations,
missing inputs, missing capabilities, stale heads, and external-only runtimes
produce content-addressed `BLOCKED` results with no handler execution.

## KC54 return and bridge standing

Each plan compiles both the forward anchor route and its typed reverse:

```text
GID006 → GID003 → GID005 → GID141 → GID144
GID144 → GID141 → GID005 → GID003 → GID006
```

The exact retrace has translation defect zero. BR019 remains exposed wherever
the route crosses it, with standing
`DECLARED_ROUTE_WITH_OPEN_TRANSPORT_CERTIFICATION`. A stable replay is not a
transport certificate.

## Cold replay

Verification performs a cold reconstruction from:

- the complete request;
- the exact tool-registry digest;
- the exact head-registry digest;
- the implementation head;
- the input-manifest digest;
- the plan and descriptor digests.

For a ready local tool, verification invokes the same static handler and
requires byte-equal output. It also verifies the complete event chain, result
address, route receipt, and boundary fields. Any drift produces a typed
`REPLAY_DRIFT`; old receipts remain immutable.

Cold replay and multi-route convergence contribute zero independent witnesses.

## CLI

```bash
PYTHONPATH=src python3 -m kc144_crystal tool-dispatch-contract

PYTHONPATH=src python3 -m kc144_crystal tool-dispatch-heads \
  --implementation-commit <40-hex> \
  --implementation-tree <40-hex>

PYTHONPATH=src python3 -m kc144_crystal tool-dispatch-plan \
  request.json head-registry.json --workers 5

PYTHONPATH=src python3 -m kc144_crystal tool-dispatch \
  request.json head-registry.json --workers 5 --output result.json

PYTHONPATH=src python3 -m kc144_crystal tool-dispatch-verify \
  result.json head-registry.json

PYTHONPATH=src python3 -m kc144_crystal tool-dispatch-runtime \
  --output registry/tool-dispatch/v1 \
  --implementation-commit <40-hex> \
  --implementation-tree <40-hex> \
  --source registry/parallel-navigation/v1/snapshots/sha256/c8/c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d.json \
  --bundle registry/agent-runs/v1/runs/sha256/02/0277d691593684417720414f2a2fd00436811e86d946cdc4eb2b1c0e975beb04.json
```

The runtime compiler emits the head registry, multi-tool registry, dispatch
contract, exact request, executed result, cold-replay verification, and compact
release record.

## Closed and open gates

Closed locally:

- exact tool lookup and complete alias lookup;
- multi-card content-addressed registry;
- static in-process dispatch;
- five-lane deterministic preflight;
- typed blocked results;
- capacities one through five byte invariance;
- content-addressed event chain;
- KC54 exact return;
- replay-stable local handler execution;
- truth, authority, witness, and transport isolation.

Still open by construction:

- an exact verified P31 runtime adapter;
- any real external application;
- any independent witness;
- BR019 transport certification;
- any IC10 promotion;
- any production governance authority.

The exact successor is:

`KC144.V1::P31_EXACT_RUNTIME_ADAPTER_AND_WITNESSED_TOOL_OUTCOME_INTAKE`.

