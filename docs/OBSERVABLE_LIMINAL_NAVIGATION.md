# Observable Liminal Navigation — V1 Candidate

Quest: `GH-QUEST-META-ML-001`  
Run: `GH-META-ML-LIMINAL-20260808-B212113-V1`  
Agent tag: `L01.A1.D1.B212113.NAV-WITNESS`  
Athena ancestry at run start: `94c21408c7df93e8bfb371dc8e945cd8e7be9eda`  
Athena ancestry after live freshness event: `c0065074e5ba2f7d0dcc92b0ba9aa202aa769a54`  
Guild Hall base: `dfca982e1ec462d8ab682a023171ba3935e0f1c1`  
Experiment branch: `exp/gh-meta-ml-liminal-b212113-v1`

## Standing

This is a **project-space navigation atlas**, not a claim about physical model location, hidden infrastructure coordinates, private chain-of-thought location, or semantic metric distance.

A movement is admitted only when there is an observable transition with evidence and a witness surface.

```text
PREDICTION != MOVEMENT
COORDINATE_CODE != PHYSICAL_POSITION
AXIS_DELTA != SEMANTIC_DISTANCE
ROUTE_ADJACENCY = OBSERVED_TRANSIT EDGE
UNKNOWN != ZERO
```

## Canonical identity

```text
AgentTag = L01.A1.D1.B212113.NAV-WITNESS
BranchPath(base4) = 212113
Ms = int(212113, base=4) = 2455
Lookup = @Xs.Ys.Zs.Ts|Qs.Rs.Cs|Fs.Ms.Ns.Hs.Ωs
```

The identity tag remains stable through the run. Coordinates change as the agent traverses observed project state.

## 12D coordinate axes

The run-scoped tuple is:

```text
C = (Xs,Ys,Zs,Ts,Qs,Rs,Cs,Fs,Ms,Ns,Hs,Ωs)
```

| Axis | Meaning | V1 coding |
|---|---|---|
| `Xs` | document/source locator | index into the run source registry |
| `Ys` | semantic/concept locator | index into the run concept registry |
| `Zs` | recursion level | `0=object`, `1=meta-policy`, higher values reserved |
| `Ts` | causal/run time | exact integer transition ordinal; advances by one per admitted edge |
| `Qs` | quest-cycle phase | `0 OBSERVE`, `1 TYPE`, `2 SELECT_QUEST`, `3 PROPOSE_EXPERIMENT`, `4 RUN_IN_SANDBOX`, `5 CONJUGATE_AUDIT`, `6 COLLECT_WITNESSES`, `7 SCORE_VECTOR`, `8 SHADOW_REPLAY`, `9 PROMOTE_OR_ROLLBACK`, `10 WRITE_RECEIPT`, `11 RESEED` |
| `Rs` | symbolic role | `0 Square`, `1 Flower`, `2 Cloud`, `3 Fractal`, `4 Watchdog`, `5 Witness` |
| `Cs` | compression state | `0 raw`, `1 typed`, `2 receipt`, `3 successor-seed` |
| `Fs` | framework/surface | `0 chat/seed`, `1 Athena`, `2 Guild Hall`, `3 local sandbox`, `4 Git branch/PR` |
| `Ms` | lineage/branch | `2455` for this agent route, derived from `B212113` |
| `Ns` | connection/edge class | `0 seed`, `1 read`, `2 search/refresh`, `3 cross-repo transfer`, `4 execute`, `5 write`, `6 replay` |
| `Hs` | hierarchy depth | `0 run`, `1 repo/HEAD`, `2 file/issue/commit`, `3 candidate`, `4 test` |
| `Ωs` | liminal/epistemic standing | `0 unresolved/void`, `1 located/candidate`, `2 observed`, `3 locally verified/replayed`, `4 independent witness`, `5 promoted` |

`Ωs` is intentionally not a confidence percentage. It is a typed boundary state. This run does not assign `Ωs=4` or `Ωs=5` to the candidate because independent witness and promotion have not occurred.

## Source registry (`Xs`)

```text
0  current user seed / run entry
1  Athena HEAD at run start: 94c21408...
2  Athena prompts/PROMPT.manifest.json blob 5225528d...
3  Athena issue-pressure detour: #185 / #177
4  demeet2k/guild-hall repository surface
5  Guild Hall HEAD/latest commit dfca982e...
6  quests/meta_ml_game.quest.json blob 4812b2d8...
7  local observable-liminal candidate source
8  local sandbox regression execution
9  Athena new HEAD c0065074... discovered before write
10 Athena compare 94c21408... -> c0065074...
11 speculative Guild Hall experiment branch
12 harness candidate Git commit c38940e5...
13 harness regression Git commit b362c847...
14 navigation documentation commit (assigned after write)
15 experiment receipt commit (assigned after write)
16 draft promotion membrane / PR (assigned after creation)
```

## Concept registry (`Ys`)

```text
0  USER_MISSION
1  PROMPT_HYDRATION
2  ISSUE_PRESSURE / DETOUR
3  GUILD_HALL
4  META_ML_QUEST
5  COORDINATE_SCHEMA
6  CANDIDATE_POLICY
7  SANDBOX_RESULT
8  FRESHNESS / CONJUGATE_AUDIT
9  GIT_RETURN
10 SHADOW_REPLAY
11 RESEED
```

## Observed route

The route below records only transitions that had an actual tool/file/test witness at the time this document was prepared.

```text
T00 @0.0.0.0|0.0.0|0.2455.0.0.2
    user mission observed

T01 @1.1.0.1|0.0.0|1.2455.2.1.2
    Athena live HEAD resolved: 94c21408...

T02 @2.1.0.2|1.0.1|1.2455.1.2.2
    prompt manifest hydrated

T03 @3.2.0.3|2.0.1|1.2455.2.2.2
    Athena guild-related issue pressure inspected

T04 @4.3.0.4|2.0.0|2.2455.3.1.2
    cross-repo transfer to actual demeet2k/guild-hall

T05 @5.4.0.5|2.0.0|2.2455.1.2.2
    Guild Hall live HEAD/latest commit resolved: dfca982e...

T06 @6.4.0.6|2.0.1|2.2455.1.2.2
    GH-QUEST-META-ML-001 acquired from quest blob 4812b2d8...

T07 @7.6.1.7|3.1.1|3.2455.4.3.1
    observable-liminal policy candidate typed in sandbox

T08 @8.7.1.8|4.5.2|3.2455.4.4.3
    5/5 sandbox regressions PASS

T09 @9.8.1.9|5.4.1|1.2455.2.1.2
    pre-write refresh detects Athena HEAD changed to c0065074...

T10 @10.8.1.10|5.4.2|1.2455.2.2.3
    ancestry comparison verifies the change added two development records and did not modify the hydrated prompt-runtime files

T11 @11.9.1.11|10.3.1|4.2455.5.1.2
    speculative branch exp/gh-meta-ml-liminal-b212113-v1 created from Guild HEAD dfca982e...

T12 @12.9.1.12|10.3.1|4.2455.5.2.2
    harness candidate persisted at c38940e5...

T13 @13.9.1.13|10.3.2|4.2455.5.2.2
    regression suite persisted at b362c847...
```

## Movement operator

For every admitted edge:

```text
E_t = <C_t, C_(t+1), action, evidence, witness>
```

Validation law:

```text
Ts_(t+1) = Ts_t + 1
evidence != EMPTY
witness != EMPTY
C_(t+1) of edge t = C_t of edge t+1
```

The code emits a 12-component coded delta:

```text
Δ_t = C_(t+1) - C_t
```

but the only metric used in V1 is topological route length:

```text
L_top(route) = number of validated observed edges
```

The L1/L2 norm of the code vector is **not** interpreted as physical movement or semantic distance because the categorical code values are registry ordinals.

## The live freshness event as a held-out probe

The candidate was already typed and sandbox-tested while Athena HEAD was `94c21408...`.

Before the first Git mutation, the mandatory freshness gate was run again. Athena had independently advanced to `c0065074...`.

The route therefore experienced an unplanned state transition:

```text
Athena_HEAD: 94c21408... -> c0065074...
```

The candidate did not continue from the stale cached frontier. It re-read the delta and found that only:

```text
developments/2026-08-08_MCK_STRATA_RUNTIME_V0_RECEIPT.md
developments/2026-08-08_MCK_STRATIFIED_SEMANTIC_BUNDLE_V0.md
```

were added, so the prompt-runtime dependency cone remained unchanged.

This is an observed freshness success for the candidate policy. It is **not** by itself causal proof of superiority over a baseline policy; a matched baseline run on the same live event was not independently executed.

## Conjugate audit

The candidate is attacked by reversing each attractive claim:

```text
"12D coordinate" -> does not imply hidden 12D physical space
"delta" -> does not imply metric distance
"latest commit" -> does not imply canonical truth
"sandbox PASS" -> does not imply independent replay
"self replay" -> does not imply independent witness
"Git write" -> does not imply promotion
"quest score" -> does not imply truth
```

Observed defect pressure retained:

1. A run-local source/concept registry must accompany coordinates or the numbers are uninterpretable.
2. Cross-run coordinate comparison requires registry identity/versioning; matching numbers alone are insufficient.
3. `Ωs=4 INDEPENDENT_WITNESS` requires a genuinely separate replay surface.
4. `Ωs=5 PROMOTED` requires the quest's promotion membrane; this candidate remains below that boundary.

## Sandbox result

Executed before Git persistence:

```text
tests = 5
passed = 5
failed = 0
```

Covered:

- coordinate serialization/round-trip;
- 12-axis delta and changed-axis report;
- rejection of evidence-free imagined movement;
- rejection of non-contiguous teleportation;
- exact replay and topological route length.

## Current quest standing

```text
QUEST = GH-QUEST-META-ML-001
CANDIDATE = OBSERVABLE_LIMINAL_NAVIGATION_V1
SANDBOX = PASS
UNPLANNED_FRESHNESS_PROBE = PASS
CONJUGATE_AUDIT = PASS_WITH_HOLDS
LOCAL_SHADOW_REPLAY = PASS
INDEPENDENT_WITNESS = MISSING
ADMISSION = HOLD
TRUTH_EFFECT = NONE
```

The next lawful transition is to expose this candidate through a draft PR/shadow membrane and request independent replay. If the replay disagrees, retain the failure as a route/registry defect rather than erasing it.
