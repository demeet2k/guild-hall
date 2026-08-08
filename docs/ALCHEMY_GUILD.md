# Alchemy Guild — Chapter 11 Crucible

**Guild ID:** `GH-ALCHEMY-C11`

**Purpose:** repeatedly manufacture new hybrid tools by starting from an intentionally extreme "anime-overpowered" capability fantasy, extracting the actual capabilities hidden inside it, fusing existing mathematical/software/tooling primitives, and forcing the result through an executable Chapter-11 descent until it becomes a buildable quest graph with tests, evidence, residuals, and a successor seed.

The Alchemy Guild is a **meta-quest factory**. Its product is not merely an idea. Its product is a sequence of increasingly real artifacts that another worker can claim, build, test, reject, improve, or promote.

## Chapter 11 law

The guild inherits the Chapter 11 / `S11 — Crucible of Alchemy` role:

> system-scale transmutation: convert partial modules into one bootable subsystem.

Operationally:

```text
CURRENT CORPUS
  -> CHAPTER-11 MANUFACTURING SEED
  -> EXTREME FUTURE OBJECT
  -> HYBRID PRIMITIVE FUSION
  -> 11→21 FUTURE EXPANSION
  -> 21→12'→11' CROWN-AWARE REWRITE
  -> 10→1 GROUNDING DESCENT
  -> EXECUTABLE PROTOTYPE / QUEST GRAPH
  -> TEST + WITNESS
  -> GIT RETURN
  -> RESEED
```

The fantasy ceiling is allowed to be absurd. The capability claim is not.

```text
MYTHIC_SPEC != IMPLEMENTED_CAPABILITY
SIMULATION != EXECUTION
ARCHITECTURE != WORKING_TOOL
SCORE != TRUTH
LATEST != CANONICAL
```

The mythic layer exists to expand the search space. Every later layer must progressively replace dramatic language with interfaces, algorithms, dependencies, tests, and observed evidence.

## The Alchemy operator

For generation `t`:

```text
M_t = MYTHICIZE(S_t, target)
V_t = EXTRACT_VERBS(M_t)
P_t = RETRIEVE_PRIMITIVES(V_t, Git, corpus, tools, math, software)
H_t = HYBRIDIZE(P_t)
C21_t = EXPAND_11_TO_21(H_t)
C11'_t = REWRITE_11(C21_t)
A_t = DESCEND_TO_ARCHITECTURE(C11'_t)
E_t = EXECUTE_WHAT_IS_LAWFULLY_EXECUTABLE(A_t)
O_t = OBSERVE(E_t)
R_t = RESIDUAL(M_t, O_t)
S_(t+1) = RESEED(O_t, R_t, GitDelta_t)
```

The loop is successful only when `S_(t+1)` is strictly more useful than replaying `S_t`: a new primitive, integration, test, compression, failure detector, implementation path, or falsified assumption must exist.

## Roles

### 1. Dreamsmith
Creates the maximum-power fictional specification. It asks: **if this were the signature tool of an impossibly overpowered anime god-engineer, what would it do?** It emits powers as typed capability verbs, not lore.

### 2. Crucible Architect
Finds at least three orthogonal real parent systems and defines the fusion law: interfaces, invariants, transports, shared state, contradictions, and expected synergy.

### 3. Crown Cartographer
Performs the Chapter `11→21` expansion: describes the completed future system, operator stack, architecture, proof shape, bridge requirements, and next hinge.

### 4. Descent Engineer
Runs the inverse route. Every speculative power must descend into known math, algorithms, software, tools, data, APIs, repositories, or an explicit unresolved research obligation.

### 5. Prototype Smith
Chooses the smallest artifact that demonstrates a nontrivial part of the hybrid: code, schema, benchmark, adapter, simulator, retrieval surface, protocol, or reproducible test.

### 6. Adversary
Attempts to kill the design through contradiction, impossible dependencies, hidden authority assumptions, unsafe interfaces, fake metrics, circular evaluation, scaling failure, or simpler competing designs.

### 7. Witness
Replays the artifact and records what actually happened. A generated prediction never counts as an observation.

### 8. ReSeeder
Compresses the observed gain + residual into the next generation. It must create a successor quest unless the lineage is explicitly retired.

## Three simultaneous speeds

### SPARK — immediate
Goal: create one high-novelty hybrid with a concrete schema and one falsifiable prototype target.

Budget discipline: prefer reversible actions and one-step proofs. Deliver `mythic_spec`, `hybrid_parents`, `MVP`, `tests`, and `next_seed`.

### CRUCIBLE — middle
Goal: turn promising SPARK outputs into working subsystems. Build adapters, data contracts, benchmarks, test harnesses, and replay receipts. Resolve interface debt before adding more powers.

### PHILOSOPHER — recursive / long
Goal: study the alchemy loop itself. Compare generations, discover which fusion patterns actually produce verified gain, compress recurring patterns into reusable guild primitives, and retire decorative complexity.

All three lanes should remain populated: imagination without engineering stagnates; engineering without frontier search local-optimizes; meta-learning without real builds self-references.

## Mandatory quest cycle

Every Alchemy quest executes this sequence:

1. **HYDRATE** — read current Git HEAD, relevant corpus, active quests, prior lineage, and available tools.
2. **MYTHICIZE** — write the maximum-power fictional tool specification.
3. **DECOMPOSE** — translate every "power" into testable capability verbs and constraints.
4. **PARENT-CENSUS** — retrieve at least three real systems that already implement useful sub-capabilities.
5. **FUSE** — design the hybrid topology, data flow, control flow, invariants, failure boundaries, and new operation created by the combination.
6. **CROWN (`11→21`)** — imagine the completed system and identify the architecture implied by success.
7. **REWRITE (`21→12'→11'`)** — use the crown to correct the seed, definitions, operator stack, and assumptions.
8. **DESCEND (`10→1`)** — map each future object to known math/code/software/proof; mark unresolved gaps explicitly.
9. **MVP** — select the smallest high-information artifact that can be built or tested now.
10. **ATTACK** — run counterexamples, ablations, simpler-baseline comparison, safety/authority checks, and scaling tests.
11. **RETURN** — persist artifact + evidence + residual + lineage to Git.
12. **RESEED** — generate the next quest from the strongest unresolved capability gap.

## Hybridization grammar

A hybrid is admitted only if it creates a new useful operation rather than a collage.

For parent systems `P_1 ... P_n`:

```text
H = <P, I, T, X, N, F, W>

P = parent systems
I = preserved invariants
T = typed transports/interfaces between parents
X = cross-effects produced only by composition
N = genuinely new native operation(s)
F = failure / incompatibility surface
W = witness plan
```

Promotion condition:

```text
NewOperation(H)
AND IntegrationGain(H) > IntegrationCost(H)
AND Replayable(H)
AND NoAuthorityMinting(H)
AND ResidualExplicit(H)
```

## Quest output contract

Every generated hybrid quest must include:

- immutable quest ID and lineage (`parent_quest_id`, generation, base Git HEAD);
- mythic name + one-sentence impossible ceiling;
- capability verbs extracted from the fantasy;
- real parent systems and why each contributes something orthogonal;
- hybrid topology and interface contracts;
- Chapter-21 crown object;
- grounding/descent table;
- MVP artifact;
- dependency graph;
- acceptance tests and kill tests;
- safety/authority boundaries;
- evidence state (`authored`, `inferred`, `tested`, `observed`, `unresolved`);
- residual ledger;
- Git writeback targets;
- successor/reseed rule.

Machine-readable outputs validate against `quests/alchemy_forge.schema.json`.

## First lineage: AZOTH-Ω / WorldSmith Compiler

### Mythic ceiling

**AZOTH-Ω** is imagined as an omniscient invention engine: give it any desired capability and it instantly sees every relevant discipline, invents the best hybrid architecture, materializes the implementation, proves it works, learns from failure, and upgrades itself forever.

That is intentionally fictional. The realizable target is narrower and useful:

> a repo-aware invention compiler that converts an ambitious capability request into a typed capability graph, retrieves relevant existing primitives, proposes orthogonal hybrid architectures, compiles them into executable work packages, routes proofs/tests, records evidence and residuals, and emits the next improved seed.

### Candidate parents

1. **Git/GitHub causal memory** — lineage, branches, issues, commits, executable work surfaces.
2. **RAG / knowledge retrieval** — recover relevant prior art, corpus state, math, software, and evidence.
3. **Typed graph / KC144 navigation** — represent capabilities, dependencies, transports, residuals, and alternate routes.
4. **Planner / compiler** — convert a target graph into ordered work packages with explicit interfaces.
5. **Sandbox + verifier** — execute prototypes, counterexamples, ablations, and replay tests.
6. **Evidence ledger** — preserve `prediction != observation` and prevent fantasy from becoming an accidental capability claim.

### New native operation

```text
INVENT(goal, state)
  -> <capability_IR,
      parent_candidates,
      hybrid_architectures,
      executable_quest_graph,
      proof_obligations,
      residual_ledger,
      successor_seed>
```

The first build target is not "omniscience". It is a deterministic **Capability IR + Hybrid Quest Compiler** that can take one ambitious tool request and emit a schema-valid, source-linked, test-bearing quest package.

## Reseed law

At the end of every generation calculate:

```text
GAIN_t = verified new operation + integration + evidence + reusable compression
DEBT_t = unresolved dependencies + fragility + cost + unsafe assumptions + duplication
FRONTIER_t = highest-value residual not already covered by an active quest
```

Then:

```text
if GAIN_t > 0:
    next_seed = compress(successes, failures, FRONTIER_t)
elif falsification_created_reusable_detector:
    next_seed = redesign_around(failure_detector)
else:
    retire_or_fork(lineage)
```

No empty loop resets. **A reseed must be paid for by a durable delta or a reusable falsification.**

## Win condition

The guild wins a generation when an absurd fictional capability has been transformed into at least one **real, claimable, testable, repo-backed advancement** and the next generation begins from observed state rather than from the original fantasy.
