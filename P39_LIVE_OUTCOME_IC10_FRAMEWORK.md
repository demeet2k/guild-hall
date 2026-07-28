# KC144 P39 — Live Outcome / Independent IC10 Convergence

P39 is the executable successor to the P38 Meta Navigator V2 candidate. It
closes the *software* side of the remaining outcome-and-authority boundary
without pretending that absent external observations or independent people
already exist.

## Exact identity

- Lookup key:
  `KC144.V4.0::MATH144.P39::LIVE_OUTCOME_CORPUS_INDEPENDENT_IC10_CONVERGENCE_WEIGHT_CALIBRATION_AND_CANONICAL_SUCCESSOR_DECISION_MACROCYCLE_08`
- Parent result: `KC144.P38.CANDIDATE::903b28c3df75072423c72959`
- Parent digest:
  `sha256:903b28c3df75072423c72959a03860ef0d636f6a189b302f4281ca36944963d8`
- Return: `KC144.V1::GID144::M12`

## What is complete

The runtime now provides one deterministic path from externally observed
outcomes to a canonical successor decision:

1. Admit content-addressed, Ed25519-signed live observations.
2. Keep calibration and held-out evidence units disjoint.
3. Reject route-generated, unconsented, future, malformed, test-only, or
   tampered observations.
4. Require at least 12 observations, three source surfaces, three routes, and
   three observations per route in **each** partition.
5. Estimate route probabilities only from the calibration partition with a
   fixed Laplace estimator.
6. Evaluate those probabilities only against the held-out partition with a
   non-degradation Brier gate.
7. Produce proposed normalized weights while executing zero canonical weight
   updates.
8. Freeze a five-seat IC10 registry with unique signer, key, organization, and
   control-root identities.
9. Require three independently controlled, valid Ed25519 returns. Every return
   binds the exact candidate root, corpus root, calibration digest, policy
   digest, decision, and all ten IC10 gates.
10. Emit `SUCCESSOR_READY` only if corpus, calibration, fixed registry, and
    three-of-five convergence all pass.

## What is deliberately not claimed

- A signature proves control of a key, not the truth of an observation.
- Enrollment proves possession and uniqueness, not authority.
- A proposed weight is not a canonical weight.
- `SUCCESSOR_READY` is not production activation.
- No production graph, canonical weight, evidence status, or truth status is
  mutated by P39.

The frozen reference release contains no fabricated live outcomes and no
fabricated independent authorities. Its correct state is `CANDIDATE_HOLD`.

## Fail-closed state transition

```text
signed observations
  -> exact intake
  -> disjoint calibration / held-out corpus
  -> deterministic proposed weights
  -> held-out non-degradation
  -> exact P39 candidate root
  -> fixed five-seat registry
  -> three-of-five independent IC10 returns
  -> canonical SUCCESSOR_READY decision
  -> P40 activation boundary
```

Any missing or mismatched binding terminates in `HOLD`. The only authority
effect P39 can emit is `SUCCESSOR_AUTHORIZATION`, and only after exact
three-of-five convergence. Actual activation and canonical weight mutation are
reserved for P40.

## Frozen candidate receipt

- Implementation commit: `762a556cece499ce3fc12a265aa9f665006ce8aa`
- Implementation tree: `ae4eb814e10ae03a3b9da71950c5a3bc20d6e02a`
- Result: `KC144.P39.CANDIDATE::50f5d2f917e2ee111b798d8d`
- Release digest:
  `sha256:50f5d2f917e2ee111b798d8de2c18ccc4c96678bee6fb010bfa873c65483eeb6`
- Frozen state: `CANDIDATE_HOLD`
- Verification: `PASS`
