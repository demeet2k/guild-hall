# KC144 V4 — Mycelium Query, Route, Witness, and Return Compiler

## What V4 adds

V3 completed the crystal as a generated 144-seat object and made the entire
declared graph traversable. V4 makes that object query-operational.

The new runtime compiles the H06 query object

\[
Q=\langle
qID,g,\tau,D,O,K,\partial,e_0,S,b,R
\rangle
\]

where:

- \(qID\) is the immutable query identity;
- \(g\) is the goal;
- \(\tau\) is the term set;
- \(D\) is the domain or band restriction;
- \(O\) is the requested operator vocabulary;
- \(K\) is the invariant vocabulary;
- \(\partial\) is the boundary vocabulary;
- \(e_0\) is the minimum evidence floor;
- \(S\) is the set of starting coordinates;
- \(b\) is the route budget;
- \(R\) is the requested return mode.

It returns an evidence-filtered set of semantic attractors, their disclosed
rank vectors, exact typed graph paths, every uncertified bridge on which those
paths depend, and an explicit return plan.

## The compilation

\[
\operatorname{Compile}(Q)=
\operatorname{Return}
\circ\operatorname{Route}
\circ\operatorname{Pareto}
\circ\operatorname{Resonate}
\circ\operatorname{EvidenceFloor}
\circ\operatorname{Domain}
(Q,\mathcal C_{144}).
\]

The order matters.

1. `Domain` removes seats outside requested bands.
2. `EvidenceFloor` removes seats whose standing is insufficient.
3. `Resonate` measures goal, term, operator, invariant, and boundary matches.
4. `Pareto` retains nondominated candidates without hiding the dimensions
   inside a single score.
5. `Route` compiles an exact path from the nearest declared start coordinate.
6. `Return` emits no return, a structural retrace, a typed retrace, or the
   global return arm.

No stage modifies the frozen graph or evidence overlay.

## Evidence floors

| Floor | Admission rule |
|---|---|
| `STRUCTURAL` | any generated KC144 seat |
| `SOURCE_DECLARED` | only a source-declared domain resident |
| `INDEPENDENT_REPLAY` | only a GID with an explicit independent replay overlay |
| `PROMOTABLE` | only a GID explicitly marked promotable by the evidence overlay |

The current production release has no independent replay or promotable
overlay. Queries at those floors therefore return a typed refusal:
`EVIDENCE_FLOOR_UNSATISFIED`. This is a successful immune response, not a
runtime failure.

## Non-scalar attractor ranking

Every candidate exposes:

\[
v(x)=
(h_g,h_\tau,h_O,h_K,h_\partial,d_S).
\]

The first five coordinates are maximized; graph distance \(d_S\) is minimized.
A candidate enters the frontier only when no other candidate is at least as
good in every coordinate and strictly better in one.

This prevents an undocumented weighting formula from collapsing semantics,
operator fit, invariant fit, boundary fit, and proximity into one supposedly
objective number.

## Typed routes and bridge exposure

Each path segment records:

- source and target GID;
- selected relation;
- selected standing;
- every alternate typed relation over the same endpoints;
- bridge ID when the selected relation is inter-band and uncertified.

Native structural relations are preferred when a native relation and a
declared bridge share endpoints. The route therefore does not pretend to
depend on a bridge when an existing structural edge suffices.

A compiled path has one of two standings:

- `STRUCTURAL_ROUTE`;
- `DECLARED_ROUTE_WITH_OPEN_TRANSPORT_CERTIFICATION`.

The latter is traversable as a graph path but cannot transport truth until its
listed bridge witnesses are admitted.

## Returns

V4 exposes four return modes:

| Mode | Meaning |
|---|---|
| `NONE` | no return requested |
| `RETRACE` | reverse the graph path; not claimed as semantic inversion |
| `TYPED_RETRACE` | reverse the path under the target seat’s declared return obligation |
| `RETURN_ARM` | join the verified global arm and reseed at `GID001′` |

The return compiler lists its own open bridge dependencies. A successful
forward route therefore cannot hide a broken or uncertified return.

## Bridge-witness admission

Each one of the 28 declared bridges may be upgraded only through:

\[
\beta_{ij}=
\langle
F_i,F_j,T_{ij},K_{\mathrm{pres}},\Delta_{ij},R_{ji},W_{ij}
\rangle.
\]

The executable gate checks:

1. the bridge ID resolves in the frozen registry;
2. packet endpoints exactly match the declaration;
3. \(T_{ij}\) is typed;
4. \(K_{\mathrm{pres}}\) contains exact preserved invariants;
5. \(\Delta_{ij}\) explicitly declares loss, including an explicit `NONE`;
6. the validity corridor is declared;
7. \(R_{ji}\) begins at the target, terminates at the source, and is
   traversable;
8. \(W_{ij}\) contains an authoritative, signed B3/B4 verifier distinct from
   the author;
9. evidence roots are not duplicated.

Passing this gate certifies only that bridge’s transport inside its declared
corridor. It never promotes either station.

The production witness ledger is empty. Consequently:

- declared bridges: 28;
- certified bridge transports: 0;
- open bridge transport obligations: 28.

Synthetic fixtures prove the gate’s mechanics but never enter the production
ledger.

## Executable interface

Compile the complete V4 release:

```bash
PYTHONPATH=src python -m kc144_crystal mycelium --output registry/v4
```

Compile a direct query:

```bash
PYTHONPATH=src python -m kc144_crystal query \
  --goal "compile an activation route through return and adjudication" \
  --terms "activation,return,adjudication" \
  --operators "RETURN" \
  --starts "6" \
  --budget 18 \
  --return-mode RETURN_ARM
```

Compile an exact JSON QueryBundle:

```bash
PYTHONPATH=src python -m kc144_crystal query --file query.json
```

Inspect the contracts:

```bash
PYTHONPATH=src python -m kc144_crystal query-contract
PYTHONPATH=src python -m kc144_crystal bridge-witness-contract
```

Evaluate a bridge witness without mutating the production ledger:

```bash
PYTHONPATH=src python -m kc144_crystal bridge-witness packet.json
```

## Completion boundary

`KC144.MYCELIUM.FRAMEWORK.V4` means the crystal can now receive a complete
query, resolve it across all 144 seats at once, retain multiple incomparable
attractors, compile exact paths, expose route debt, and generate return plans.

It does not claim:

- that any of the 28 bridge transports is certified;
- that an independent cold replay has occurred;
- that any station is newly promotable;
- that federation contracts are externally published;
- that solid state has been reached.

The framework has moved from **whole-crystal observability** to
**whole-crystal addressability**. The next evidence-bearing action is no
longer vague: supply one genuine bridge witness, one independent replay, or
one source-bound domain resident, and the correct gate and route are already
waiting for it.

V5 implements the cumulative successor without altering this contract:
`KC144.INTERNAL-NAV.P07::EDGE-MANIFEST-FREEZE-AND-REPLAY-SUITE-BINDING`.
See `GLOBAL_STATE_FRAMEWORK_V5.md`.
