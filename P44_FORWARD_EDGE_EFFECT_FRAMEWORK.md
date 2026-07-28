# KC144 P44 — Forward Outcome Window and Canonical Edge Effect

P44 observes the effect of the exactly-once P41 edge transaction without
collapsing execution, empirical performance, truth, or authority. It binds the
exact public P43 parent, requires a valid one-record execution ledger, admits
only strictly forward nonreused outcomes, measures nondegradation across
diverse routes, and freezes a finite edge-effect receipt only when every gate
passes.

## Exact lineage

```text
PUBLIC_PARENT::KC144.P43.CANDIDATE::240473a1935faad593c1b8d5
PUBLIC_PARENT_RELEASE::sha256:240473a1935faad593c1b8d5ea74b7171cac43bfac63ad597e0161238c424aa2
RETURN::KC144.V1::GID144::M12
```

The measurement window requires at least five `TASK_OUTCOME` or
`EMPIRICAL_RESULT` events, two event classes, and three distinct routes. Every
event must occur strictly after execution, carry baseline and candidate
scores, and remain outside the authorization cohort. The candidate mean may
not degrade relative to baseline, and at least three individual events must be
nondegrading.

Passing those finite conditions freezes a
`FROZEN_CANONICAL_EDGE_EFFECT` receipt. It does not establish general
optimality, proposition truth, route-weight authority, model-weight authority,
or governance authority.

The public reference has an exact frozen P43 parent whose external production
gates remain unsatisfied. P44 therefore honestly remains `CANDIDATE_HOLD` with
zero forward outcomes, no finalized production edge, no frozen effect, zero
canonical mutations, production authority `HOLD`, and truth effect `NONE`.
