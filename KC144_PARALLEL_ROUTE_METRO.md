# KC144 — Parallel Route Metro

```text
LOOKUP_KEY::KC144.V1::PARALLEL_ROUTE_CRYSTAL
BRANCH::kc144-parallel-navigation-v1
IMMUTABLE_COMMIT::1b653e39d7c09ba8b93a800860244242cd98d397
IMMUTABLE_TREE::d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b
COMPILER_COMMIT::77c67543b0d6df946d7ffa7d17242bf869c3ad1b
COMPILER_TREE::0fdb2184b9c9777f557102a84c44ac034991fe5f
SNAPSHOT_COMMIT::475259f5ca3e5da3528eddda59f411baf37e57c0
SNAPSHOT_DIGEST::sha256:c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d
MAXIMUM_PARALLEL_WIDTH::5
TOTAL_BOUNDED_TYPED_TARGET_PATHS::18402557639
CONTENT_TRANSPORT_CERTIFIED::FALSE
GOVERNANCE_AUTHORITY_GRANTED::FALSE
PRODUCTION_TRUTH_EFFECT::NONE
```

The parallel route crystal executes five independent KC144 simulations against
the same immutable atlas and then performs one deterministic reduction.
One-worker and five-worker executions produce identical bytes.

## Five simultaneous paths

| Route | Mathematical lens | Canonical hops | Shortest typed paths | All bounded typed target paths |
|---|---|---:|---:|---:|
| `A_X16_CONTRACT` | K4/C4 address and contract | 9 | 2 | 8,495,077 |
| `B_BR21_ADVERSARIAL` | C7×C3 operator/return | 10 | 2 | 651,034 |
| `C_KC27_CUBE` | ternary cube/localize-compress-lift | 4 | 1 | 18,392,778,724 |
| `D_KC15_SUPPORT` | support lattice/expressibility | 13 | 24 | 537,780 |
| `E_IC10_ADJUDICATION` | ordered gate chain | 9 | 2 | 95,024 |

Every count is exact inside its declared graph, prefix, target, and hop budget.
Cycles are included. The snapshot expands deterministic shortest witnesses and
compresses the remaining path universe into exact counts by path length.

## Simultaneous coordinate projections

Every traversed GID is resolved through:

```text
NATIVE KC144 IDENTITY
× 12×12 GRID
× ADAPTIVE-BINARY/K4
× DLS 4×4-IN-12×12
× 16×16 INJECTION
× BR21 MODULAR
× KC27 MODULAR
× KC54 DUPLEX
× C144
× 360-DEGREE ROTATION
× 25,920-YEAR PHASE
× PRIME ADDRESS
× D4 ORBIT
× LIMINAL BOUNDARY
```

Each transform receipt records preserved, changed, removed, and added
coordinate states. Endpoint vectors are interned once in the snapshot and edge
receipts reference them exactly, preserving information without repetition.

## Parallel-agent law

```text
WAVE 1::
  SIMULATE A
  SIMULATE B
  SIMULATE C
  SIMULATE D
  SIMULATE E

WAVE 2::
  VALIDATE + DETERMINISTICALLY REDUCE
```

The scheduler admits up to five dependency-ready tasks with nonoverlapping
write sets. Solo, mutation, authorization, and reducer tasks remain sequential.
Workers cannot merge their own output. Completion order never controls merge
order.

If spawning is unavailable, the same task envelopes execute sequentially.
Tasks requiring genuine independent agency become `BLOCKED_CAPABILITY`; the
coordinator cannot impersonate independence.

## Exact navigation

- [Executable branch](https://github.com/demeet2k/guild-hall/tree/kc144-parallel-navigation-v1)
- [Full route algebra](https://github.com/demeet2k/guild-hall/blob/kc144-parallel-navigation-v1/KC144_PARALLEL_ROUTE_FRAMEWORK.md)
- [Parallel-agent scheduler](https://github.com/demeet2k/guild-hall/blob/kc144-parallel-navigation-v1/KC144_PARALLEL_AGENT_SCHEDULER.md)
- [Compiler](https://github.com/demeet2k/guild-hall/blob/kc144-parallel-navigation-v1/src/kc144_crystal/parallel_routes.py)
- [Property tests](https://github.com/demeet2k/guild-hall/blob/kc144-parallel-navigation-v1/tests/test_parallel_routes_v1.py)
- [Snapshot registry](https://github.com/demeet2k/guild-hall/tree/kc144-parallel-navigation-v1/registry/parallel-navigation/v1)
- [Current snapshot](https://github.com/demeet2k/guild-hall/blob/kc144-parallel-navigation-v1/registry/parallel-navigation/v1/snapshots/sha256/c8/c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d.json)

```text
NEXT::KC144.V1::CONTENT-ADDRESSED-AGENT-RUN-RECEIPTS
RETURN::KC144.V15::LIVE_STATE_METRO
PARENT::KC144.V3::NAVIGATION-WAVE-AND-HOLONOMY
```
