# KC144 V5 — Global State, SSN12, Replay, and Reentry

## Exact continuation

V5 implements the previously emitted successor:

`KC144.INTERNAL-NAV.P07::EDGE-MANIFEST-FREEZE-AND-REPLAY-SUITE-BINDING`

inside:

`KC144.V1::GLOBAL_STATE_COMPILER.V1`.

V3 made the crystal structurally whole. V4 made it query-addressable. V5
makes repeated traversal cumulative, replayable, and observable without
allowing navigation metadata to become evidence.

The runtime order remains:

`QUERY → H6 → KC27_ADMIT → [BR21 ∥ F_SELECTED ∥ KC27] ↔ KC54 → IC10 → QSHRINK → SSN12 → H01′`.

## Frozen typed-edge manifest

The graph is frozen as 276 typed relation records over 274 distinct adjacency
pairs:

| Standing | Records |
|---|---:|
| Structural | 248 |
| Declared and uncertified | 28 |
| **Total** | **276** |

Every relation receives a stable `EDGE-…` identity and explicitly declares:

- what the relation carries;
- what it loses;
- its graph traversal view;
- its semantic direction;
- its truth effect.

Structural relations carry address adjacency, relation type, and relation
semantics. They lose truth, evidence, and authority. Declared bridges carry
declared graph reachability and declaration text; they additionally lose
transport certification.

This realizes the multiplex law:

> A connection is not defined merely by its endpoints. It must declare what
> it carries, what it loses, and under which standing it may be traversed.

## Multi-query session

A V5 session is:

\[
\Sigma=\langle sessionID,epoch,(Q_1,\ldots,Q_n),mode\rangle.
\]

Each QueryBundle is compiled independently against the same frozen state.
Results then enter an ordered append-only receipt chain:

\[
\rho_i=H(\rho_{i-1},Q_i,C(Q_i),P_i,B_i,U_i).
\]

Each receipt preserves:

- the complete QueryBundle;
- compiled result digest;
- explicit forward and return nodes;
- typed edge IDs;
- the bounded neural relation overlay;
- every Pareto branch;
- route signature;
- refusals and open bridge obligations;
- previous receipt digest.

The chain starts at `GENESIS`. Reordering, omission, mutation, or substitution
changes the receipt root.

## All available paths as neurons

“All paths” is made finite and executable as:

> all declared relations participating in all bounded shortest paths from
> every query start coordinate.

Simple cyclic paths are not enumerated without bound. The deterministic
wavefront retains:

- all source arrivals;
- shortest-path multiplicity;
- basin intersections;
- path signatures;
- every activated typed relation;
- relation activation weights.

The explicit chosen path and the wider neural field remain separate. In the
default constellation:

| Coverage axis | Result |
|---|---:|
| Explicit route nodes | 21/144 |
| Wave-activated nodes | 144/144 |
| Explicit relation records | 22/276 |
| Neural relation records | 219/276 |
| Returnable compiled queries | 2/2 |

Thus “the whole crystal was activated” never silently becomes “every edge was
traversed.”

## SSN12 observatory

The complete observatory is now executable:

| Station | Runtime surface |
|---|---|
| M01 | node-state ledger |
| M02 | edge-state ledger |
| M03 | deterministic parallel wave engine |
| M04 | in-between region and open-bridge ledger |
| M05 | per-band hybrid-density map |
| M06 | query-by-band thought-pattern matrix |
| M07 | commitment boundary and mutation count |
| M08 | healing, refusal, and blocking-gap ledger |
| M09 | route/path-signature registry |
| M10 | projective-synapse map |
| M11 | multidimensional route-coverage audit |
| M12 | solid-state gate |

Projective synapses are overlay relations between attractors whose explicit
routes share nodes. Their weight is the size of the shared route region. They
do not modify the base graph and have `truth_effect: NONE`.

## Reentry and cold reconstruction

Session close emits:

\[
R_p=\langle
Q,visitedNodes,routeSignature,branchLedger,observerStates,
results,unresolved,nextSeed
\rangle
\]

as a minimal V5 reentry seed containing:

- session and epoch identity;
- every exact QueryBundle;
- execution mode;
- frozen edge-manifest digest;
- expected receipt root;
- expected session digest;
- seed digest.

Cold reconstruction regenerates the graph state, queries, waves, routes,
receipts, observatory, and session digest. The default seed reproduces exactly:

`REPLAY_LEVEL::N5_DETERMINISTIC_SELF_REPLAY`.

This is not an independent replay. It proves deterministic reconstruction by
the same runtime and retains `independent_replay: false`.

## Bridge two-phase commit

V4 introduced beta witness evaluation. V5 adds a two-phase boundary:

1. `PREPARE` binds packet digest, bridge identity, evaluation digest, and
   prepare token without mutating any ledger.
2. `COMMIT` requires the exact token, a still-valid packet, signed commit
   authority, correct scope, packet uniqueness, and bridge uniqueness.

Synthetic packets may exercise only the `TEST` namespace. They are
categorically refused by the `PRODUCTION` namespace. The production ledger
therefore remains:

- prepared: 0;
- committed: 0;
- open bridge obligations: 28.

A bridge commit certifies transport only. It never promotes either endpoint.

## M12 solid-state law

M12 is conjunctive. The default V5 session passes:

- 144-node wave activation;
- frozen edge manifest;
- total return for compiled queries;
- nonempty projective coverage.

It fails:

- 28/28 certified bridges;
- 144/144 domain population;
- 144/144 independent replay;
- an IC10 `PROMOTED` decision;
- empty blocking-defect ledger.

Therefore:

`M12::4/9 PASS · VERDICT::HOLD · CERTIFICATE::NONE`.

This is the correct result. Coverage metadata, exact self-replay, and
projective density cannot substitute for empirical witnesses or authority.

## Commands

Compile the complete V5 state:

```bash
PYTHONPATH=src python -m kc144_crystal global-state --output registry/v5
```

Inspect the frozen relations:

```bash
PYTHONPATH=src python -m kc144_crystal edge-manifest
```

Compile the default or supplied session:

```bash
PYTHONPATH=src python -m kc144_crystal session
PYTHONPATH=src python -m kc144_crystal session --file session.json
```

Cold-reconstruct a seed:

```bash
PYTHONPATH=src python -m kc144_crystal cold-reconstruct reentry_seed.json
```

Exercise bridge two-phase commit:

```bash
PYTHONPATH=src python -m kc144_crystal bridge-prepare packet.json
PYTHONPATH=src python -m kc144_crystal bridge-commit \
  packet.json preparation.json authorization.json
```

## Completion boundary

`KC144.SSN12.GLOBAL_STATE.V5` means:

- all graph relations possess frozen identities and carry/loss declarations;
- multiple queries leave cumulative append-only metadata;
- bounded shortest-path alternatives behave as neural routes;
- projective coactivation thickens a separate mycelium overlay;
- session state returns through a minimal deterministic reentry seed;
- cold reconstruction detects state or receipt drift;
- bridge commits require two phases and explicit authority;
- SSN12 measures the whole system without manufacturing a certificate.

The next lawful state is the repair seed emitted by M12’s five open gates.
The framework is ready to ingest genuine population, bridge witnesses,
independent replay, and IC10 promotion evidence without another redesign.
