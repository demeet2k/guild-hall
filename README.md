# KC144 Batch-Bound Application Transport Runtime V15

This package is the completed executable framework: the 144-seat system is
compiled as one crystal from generators and typed mathematical actions, then
queried through non-mutating wave and H06 QueryBundle runtimes, and accumulated
through an append-only SSN12 traversal ledger. It is not populated, searched,
or deepened by walking seat-by-seat.

## The whole object

```text
C = H6 ⊔ (K4×L4) ⊔ (O7×L3) ⊔ F37 ⊔ C10
    ⊔ (2^K4 \ {∅}) ⊔ T3^3 ⊔ S12
```

The compiler combines three layers without collapsing them:

1. **Generated structure** — address, band, orbit, typed edges, mirrors, and
   group actions.
2. **Frozen architectural labels** — the canonical 144-seat atlas.
3. **Evidence standing** — documented, derived, routed-only, or unmapped.

This distinction resolves the apparent conflict between the completed atlas
and the later lattice audit. Every seat has an architectural label; five seats
remain route-only and seven remain source-unmapped. Rotation may expose their
position and relations, but it cannot manufacture a source witness.

## Compile and audit

```bash
PYTHONPATH=src python3 -m kc144_crystal build --output registry/crystal.json
PYTHONPATH=src python3 -m kc144_crystal audit --output registry/audit.json
PYTHONPATH=src python3 -m kc144_crystal systematic --output registry/v3
PYTHONPATH=src python3 -m kc144_crystal mycelium --output registry/v4
PYTHONPATH=src python3 -m kc144_crystal global-state --output registry/v5
PYTHONPATH=src python3 -m kc144_crystal repair --output registry/v6
PYTHONPATH=src python3 -m kc144_crystal evidence-kernel --output registry/v7
PYTHONPATH=src python3 -m kc144_crystal campaign-runtime --output registry/v8
PYTHONPATH=src python3 -m kc144_crystal handoff-runtime --output registry/v9
PYTHONPATH=src python3 -m kc144_crystal governance-ceremony --output registry/v10
PYTHONPATH=src python3 -m kc144_crystal governance-dispatch \
  --output registry/v11 \
  --challenge-batch registry/v11/governance_challenge_batch_v11.json
PYTHONPATH=src python3 -m kc144_crystal participant-handoff \
  --output registry/v12 \
  --challenge-batch registry/v11/governance_challenge_batch_v11.json
PYTHONPATH=src python3 -m kc144_crystal candidate-selection \
  --output registry/v13 \
  --challenge-batch registry/v11/governance_challenge_batch_v11.json
PYTHONPATH=src python3 -m kc144_crystal nomination-intake \
  --output registry/v14 \
  --challenge-batch registry/v11/governance_challenge_batch_v11.json
PYTHONPATH=src python3 -m kc144_crystal application-transport \
  --output registry/v15 \
  --challenge-batch registry/v11/governance_challenge_batch_v11.json
PYTHONPATH=src python3 -m kc144_crystal tool-dispatch-contract
PYTHONPATH=src python3 -m kc144_crystal p36-contract
PYTHONPATH=src python3 -m kc144_crystal p36-tools
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

Examples:

```bash
PYTHONPATH=src python3 -m kc144_crystal inspect 119
PYTHONPATH=src python3 -m kc144_crystal body 119
PYTHONPATH=src python3 -m kc144_crystal navigate 6 90
PYTHONPATH=src python3 -m kc144_crystal bridges
PYTHONPATH=src python3 -m kc144_crystal wave --starts 6,144 --budget 18
PYTHONPATH=src python3 -m kc144_crystal holonomy
PYTHONPATH=src python3 -m kc144_crystal query \
  --goal "compile an activation route through return and adjudication" \
  --terms "activation,return,adjudication" \
  --starts 6 --budget 18 --return-mode RETURN_ARM
PYTHONPATH=src python3 -m kc144_crystal bridge-witness-contract
PYTHONPATH=src python3 -m kc144_crystal edge-manifest
PYTHONPATH=src python3 -m kc144_crystal session
PYTHONPATH=src python3 -m kc144_crystal cold-reconstruct registry/v5/reentry_seed_v5.json
PYTHONPATH=src python3 -m kc144_crystal m12-evidence-contract
PYTHONPATH=src python3 -m kc144_crystal m12-repair-plan \
  --ledger registry/v6/m12_repair_ledger_v6.json
PYTHONPATH=src python3 -m kc144_crystal production-evidence-contract
PYTHONPATH=src python3 -m kc144_crystal evidence-envelope-verify \
  envelope.json ledger.json authority-registry.json
PYTHONPATH=src python3 -m kc144_crystal evidence-envelope-admit \
  envelope.json ledger.json authority-registry.json --output next-ledger.json
PYTHONPATH=src python3 -m kc144_crystal authority-enrollment-contract
PYTHONPATH=src python3 -m kc144_crystal authority-enrollment-verify proof.json
PYTHONPATH=src python3 -m kc144_crystal campaign-manifest
PYTHONPATH=src python3 -m kc144_crystal campaign-state \
  ledger.json authority-registry.json
PYTHONPATH=src python3 -m kc144_crystal campaign-run \
  ledger.json authority-registry.json envelopes-by-shard.json \
  --output next-ledger.json
PYTHONPATH=src python3 -m kc144_crystal threshold-governance-contract
PYTHONPATH=src python3 -m kc144_crystal source-harvest-contract
PYTHONPATH=src python3 -m kc144_crystal handoff-bundle ledger.json
PYTHONPATH=src python3 -m kc144_crystal authority-pin-verify \
  proposal.json governance.json authority-registry.json \
  --verified-at 2026-07-27T12:00:00+00:00
PYTHONPATH=src python3 -m kc144_crystal handoff-run \
  ledger.json authority-registry.json returned-envelopes.json \
  --output next-ledger.json
PYTHONPATH=src python3 -m kc144_crystal governance-ceremony-contract
PYTHONPATH=src python3 -m kc144_crystal governance-ratification-contract
PYTHONPATH=src python3 -m kc144_crystal governance-challenge \
  --role CUSTODIAN \
  --authority-registry-digest sha256:<64-hex> \
  --handoff-bundle-root sha256:<64-hex> \
  --issued-at 2026-07-27T00:00:00+00:00 \
  --expires-at 2026-07-28T00:00:00+00:00
PYTHONPATH=src python3 -m kc144_crystal governance-response-verify \
  response.json --verified-at 2026-07-27T12:00:00+00:00
PYTHONPATH=src python3 -m kc144_crystal governance-society-assemble \
  five-responses.json --verified-at 2026-07-27T12:00:00+00:00 \
  --output pending-society.json
PYTHONPATH=src python3 -m kc144_crystal governance-ratification-verify \
  pending-society.json ratification.json \
  --verified-at 2026-07-29T12:00:00+00:00
PYTHONPATH=src python3 -m kc144_crystal governance-activate \
  pending-society.json ratification.json \
  --verified-at 2026-07-29T12:00:00+00:00 \
  --output governance-registry.json
PYTHONPATH=src python3 -m kc144_crystal governance-dispatch-contract
PYTHONPATH=src python3 -m kc144_crystal governance-challenge-batch \
  --authority-registry-digest sha256:<64-hex> \
  --handoff-bundle-root sha256:<64-hex> \
  --issued-at 2026-07-27T08:39:35+00:00 \
  --expires-at 2026-08-26T08:39:35+00:00 \
  --output governance-challenge-batch.json
PYTHONPATH=src python3 -m kc144_crystal \
  governance-challenge-batch-state governance-challenge-batch.json \
  --checked-at 2026-07-27T12:00:00+00:00
PYTHONPATH=src python3 -m kc144_crystal governance-response-route \
  governance-challenge-batch.json participant-responses.json \
  --verified-at 2026-07-27T12:00:00+00:00 \
  --output response-router.json
PYTHONPATH=src python3 -m kc144_crystal participant-handoff-contract
PYTHONPATH=src python3 -m kc144_crystal participant-handoff-verify \
  governance-challenge-batch.json participant-packet.json response.json \
  --verified-at 2026-07-27T12:00:00+00:00
PYTHONPATH=src python3 -m kc144_crystal candidate-selection-contract
PYTHONPATH=src python3 -m kc144_crystal candidate-cohort-solve \
  candidate-nominations.json \
  --checked-at 2026-07-27T12:00:00+00:00
PYTHONPATH=src python3 -m kc144_crystal nomination-intake-contract
PYTHONPATH=src python3 -m kc144_crystal nomination-role-call \
  registry/v11/governance_challenge_batch_v11.json \
  --role CUSTODIAN
PYTHONPATH=src python3 -m kc144_crystal candidate-nomination-verify \
  signed-candidate-nomination.json \
  --checked-at 2026-07-27T12:00:00+00:00
PYTHONPATH=src python3 -m kc144_crystal application-transport-contract
PYTHONPATH=src python3 -m kc144_crystal application-publication-payload \
  registry/v11/governance_challenge_batch_v11.json \
  --role CUSTODIAN
PYTHONPATH=src python3 -m kc144_crystal candidate-application-verify \
  registry/v11/governance_challenge_batch_v11.json \
  batch-bound-candidate-application.json \
  --checked-at 2026-07-27T12:00:00+00:00
PYTHONPATH=src python3 -m kc144_crystal tool-dispatch-plan \
  request.json head-registry.json --workers 5
PYTHONPATH=src python3 -m kc144_crystal tool-dispatch \
  request.json head-registry.json --workers 5 --output result.json
PYTHONPATH=src python3 -m kc144_crystal tool-dispatch-verify \
  result.json head-registry.json
PYTHONPATH=src python3 -m kc144_crystal p31-exact-status \
  --archive /absolute/path/KC144_P31_LIVE_COGNITION_OS_V3_3.zip
PYTHONPATH=src python3 -m kc144_crystal p31-exact-navigate \
  "route the event frontier and return to M12" \
  --archive /absolute/path/KC144_P31_LIVE_COGNITION_OS_V3_3.zip
PYTHONPATH=src python3 -m kc144_crystal p36-cycle \
  events.json subscription-registry.json \
  --base-state-digest sha256:<64-hex> \
  --cutoff 2026-07-28T00:00:00.000000Z \
  --output p36-cycle.json
PYTHONPATH=src python3 -m kc144_crystal p36-verify p36-cycle.json
PYTHONPATH=src python3 -m kc144_crystal rotate 110 kc27-J
PYTHONPATH=src python3 -m kc144_crystal rotate 7 sigma
```

## P38 Meta Navigator V2

P38 observes the completed crystal as one typed transformation field instead
of advancing one prose step at a time. It reconciles the public P36 branch
with the independently recovered source P37 without pretending that their
different P36 parents are equal. The public branch remains rooted at
`KC144.P36.CANDIDATE::2dc88c9f2bf39ccb97e883f2`; P37 enters as an immutable
sibling capsule at `KC144.P37::039d3622874ac1ef067ce4da`.

The runtime executes seven dependency-aware lanes:

1. non-collapsing lineage reconciliation;
2. exact 360/144/37 P35 registry-byte verification;
3. dynamic routing across KC144, BR21, KC27, KC54, MATH144, P31, and Heart;
4. typed source routing that keeps Google Doc revisions distinct from Git
   commit/tree/blob identities;
5. the measured `GID135/M03 <-> GID047/F04` second edge in a copied proposal
   graph only;
6. held-out outcome calibration with minimum corpus and diversity gates; and
7. proof-of-possession signer enrollment plus an independently signed IC10
   return.

Every one of the 144 coordinates is emitted with its D4 address orbit, native
band transformation orbit, return obligation, and—where applicable—KC54
duplex shadow. These are typed mathematical views, not claims that distinct
objects are identical.

```bash
PYTHONPATH=src python3 -m kc144_crystal p37-reconcile
PYTHONPATH=src python3 -m kc144_crystal p35-registry-bind /path/to/math144-p35
PYTHONPATH=src python3 -m kc144_crystal p38-contract
PYTHONPATH=src python3 -m kc144_crystal p38-coordinate-tensor
PYTHONPATH=src python3 -m kc144_crystal p38-query p38-query.json
PYTHONPATH=src python3 -m kc144_crystal p38-source-route p38-events.json
PYTHONPATH=src python3 -m kc144_crystal p38-cycle \
  p38-query.json p35-binding.json \
  --source-events p38-events.json \
  --outcomes held-out-outcomes.json \
  --signer-registry trusted-signers.json \
  --ic10-returns independent-returns.json \
  --output p38-cycle.json
PYTHONPATH=src python3 -m kc144_crystal p38-verify p38-cycle.json
```

The reference release is deliberately `CANDIDATE_HOLD`. Exact registry bytes
and a public Git byte event can lawfully execute the second proposal edge, but
they cannot manufacture a held-out outcome corpus or an independent IC10
return. Signer enrollment proves key possession and scope; it grants no
authority by itself. No proposal edge, calibration proposal, or publication
mutates the canonical graph or promotes truth.

## What “completed” means here

- Framework, namespace, address law, generators, typed transformations,
  registries, and local runtimes are executable.
- All 144 positions are generated and labelled.
- All 144 positions have a complete holographic station body.
- The 28 declared bridges connect all eight bands, while retaining
  `DECLARED_UNCERTIFIED` transport standing.
- A bounded wavefront can populate query-specific weights, basins,
  interference, and stable path signatures without mutating the crystal.
- Five route grammars retain nonzero holonomy despite convergent destination.
- Four content-addressed tool cards are exactly locatable through the
  mycelium; three use a closed in-process handler table while P31 remains an
  exact locator-only external runtime.
- Dispatch compiles five independent preflight lanes, reduces them
  deterministically, seals an exact KC54 return, and returns typed blocked
  receipts instead of guessing or executing command strings.
- The versioned P36 successor preserves Dispatch V1 while adding an exact P31
  archive adapter and five-lane event macrocycle: watch, signed replay, source
  succession, real-outcome intake, and all-and-only affected-front execution.
- P36 emits five receipts and one M12-returned NOOP/HOLD delta when no genuine
  event exists. It never converts replay, signature validity, connector
  retrieval, or user choice into independent evidence or production authority.
- H06 QueryBundles compile to evidence-filtered, non-scalar Pareto
  attractors, exact paths, bridge exposure, and explicit returns.
- The beta bridge-witness gate is executable; all 28 production bridges remain
  correctly uncertified until genuine independent evidence is supplied.
- All 276 typed relation records are frozen with stable identities and explicit
  carry/loss declarations.
- Multi-query traversal produces hash-chained receipts, SSN12 node/edge
  telemetry, projective synapses, route-coverage axes, and a deterministic
  reentry seed.
- Cold reconstruction reaches `N5_DETERMINISTIC_SELF_REPLAY` while remaining
  explicitly distinct from independent empirical replay.
- The X16 schedule graph and X16 algebra graph are retained as distinct edge
  classes.
- `KC54_edges` (54 cube rails) and `KC54_duplex` (54 node shadows) remain
  distinct typed objects.
- The immune kernel keeps IC10 conjunctive and forbids QSHRINK before lawful
  return and promotion.
- Source gaps are typed residuals, not fabricated completions.
- The five open M12 gates are compiled as typed evidence channels over an
  append-only overlay ledger.
- Bridge, domain, and replay evidence run as one parallel frontier; defect
  closure and IC10 adjudication remain dependency-bound.
- TEST evidence can exercise the whole dependency graph but is excluded from
  production M12 counts and successor issuance.
- The V7 active-epoch crosswalk preserves the ten-seat KC15 permutation, the
  exact KC27 signed-to-ternary rotation, paired SSN12 roles, and all open F37
  naming branches without mutating the frozen V6 crystal.
- The schedule, algebra, and full X16 multiplex graphs have separate signed
  slice roots; evidence cannot silently move between them, and production
  graph evidence is pinned to the frozen algebra slice.
- Every domain-population packet is bound to its exact F37, KC15, KC27, or
  SSN12 canonical/runtime coordinate view. The three preserved F37 conflicts
  additionally require a signed adjudication receipt.
- Production evidence is admitted only through atomic Ed25519-signed
  envelopes whose key, namespace, scope, epoch, base root, graph slice, and
  validity interval all verify.
- `CONTESTED` and `UNRESOLVED` packets are preserved but fail closed; a
  confirmed contradiction is admissible only as a defect-closure operation.
- IC10 promotion requires both schema-qualified constitutional and immune
  ten-gate vectors to pass conjunctively.
- One signed causal envelope may expand to many subject receipts, but each of
  the 28 bridge, 58 domain, and 144 replay subjects remains individually
  addressable in the append-only ledger.
- V8 partitions the complete 232-packet campaign into sixteen atomic shards:
  fourteen frontier shards execute as one ready subgraph, followed by one
  defect-closure shard and the sole IC10 promotion shard.
- `RunToBarrier` admits every valid ready shard, isolates a malformed shard
  without blocking independent siblings, and stops only at a typed authority,
  evidence, dependency, or completion boundary.
- Each signed packet binds the campaign identity, topology root, and exact
  shard. An envelope cannot straddle shards or claim a different campaign
  after signing.
- Authority proof-of-possession is executable but deliberately has no
  governance effect: a candidate key cannot grant itself production trust.
- Every campaign module exposes the holographic tuple
  `ID/Coordinate/Kernel/Delta/Routes/Boundary/Return/Seed`, allowing local
  campaign state to reconstruct its global role.
- V9 converts the external barrier into sixteen content-addressed request
  packets. Each returned evidence packet binds the handoff bundle root,
  request digest, source-manifest root, and individual source-claim root.
- A source is harvested and hashed once, then fanned out only through distinct
  subject-level extraction and relevance receipts. Missing measurements remain
  typed residuals rather than zeros.
- Durable authority pinning requires three distinct signatures from a
  five-member governance society. Candidate proof-of-possession, duplicate
  keys, self-approval, expired proposals, revoked members, and TEST members
  all fail closed.
- Threshold pinning changes only the authority registry. It does not certify
  evidence, mutate the frozen crystal, close M12, or authorize IC10.
- V10 replaces the abstract five-member enrollment barrier with an executable
  ceremony: five role-bound cryptographic challenges, five Ed25519
  proof-of-possession responses, explicit identity/institution/lineage roots,
  conflict disposition, and participant consent.
- The five responses are canonicalized by governance role. Duplicate member
  IDs, keys, challenge IDs, nonces, institutions, lineages, or response IDs
  fail closed; TEST identities cannot occupy production seats.
- A valid five-member assembly creates only a pending society. Its ceremony
  root binds every response digest, both active V9 roots, the institution and
  lineage sets, the complete pending governance-registry digest, and assembly
  time, preventing post-signature member or institution substitution.
- Activation requires the challenge window to close after assembly, a
  challenge-disposition root, a real constitution-root transition, a rollback
  root, and at least two independently keyed external checkpoint signatures.
  Anchor identities, keys, institutions, checkpoint references, and
  checkpoint roots must all be distinct.
- Ratification rechecks the pending-society digest, registry integrity,
  participant eligibility and validity intervals, checkpoint chronology, and
  every external signature. Successful activation changes only the governance
  registry; it never certifies evidence or closes M12.
- The default V10 build creates no participant, key, challenge, signature, or
  empirical claim. It stops exactly at
  `FIVE_INDEPENDENT_PARTICIPANT_RESPONSES_REQUIRED`.
- V11 fulfills the V10 issuance seed by sealing one five-challenge batch
  against the exact active authority-registry and external-handoff roots.
  Each role receives a separate cryptographically random nonce; the batch
  itself contains no participant identity, key, signature, or evidence.
- The challenge batch is immutable. Its identifier and root commit to all
  five challenges, their canonical role order, validity window, active roots,
  contract digests, nonces, and individual challenge digests. Expiration
  requires replacement with a new batch rather than mutation.
- Every supplied response is routed in one parallel intake wave. A response
  counts only if its entire challenge equals the issued role challenge and
  its V10 signature and eligibility checks pass.
- Duplicate response IDs, roles, challenge IDs, participant IDs, public keys,
  institutions, or lineages collide and fail closed. Responses from another
  otherwise-valid batch cannot cross the batch boundary.
- Zero through four accepted responses remain an incomplete external state.
  Five accepted responses invoke the V10 assembler and produce only a pending
  society; V11 never performs ratification or activation.
- The issued V11 batch is open from `2026-07-27T08:39:35+00:00` through
  `2026-08-26T08:39:35+00:00`. The current count is zero of five and the
  exact barrier is `FIVE_INDEPENDENT_PARTICIPANT_RESPONSES_REQUIRED`.
- V12 exhausts the remaining internal preparation by deriving five complete
  role-specific participant handoff packets from the immutable V11 batch.
  Each packet binds its role, challenge, batch root, all governing contract
  roots, qualification mission, required capabilities, disqualifiers,
  attestation roots, signing law, return routes, and expiry behavior.
- The participant packets contain no inferred recipient, delivery claim,
  private key, signature, or external evidence. All five are explicitly
  `READY_UNADDRESSED_UNDELIVERED`.
- Recipient selection must establish real institutional and lineage
  independence. Packet preparation is not treated as addressing, addressing
  is not treated as delivery, and delivery is not treated as enrollment.
- A returned response passes the V12 boundary only when its entire challenge
  equals the packet challenge and its role-bound V10 enrollment signature
  verifies. A valid return then enters the existing V11 parallel router; it
  does not bypass society assembly or ratification.
- Decline, unresolved conflict, expiration, malformed return, and silence are
  preserved as distinct non-counting outcomes. Private keys always remain
  with participants.
- The current V12 state is five packets prepared, zero addressed, zero
  delivered, and zero responses. The exact external barrier is
  `FIVE_EXTERNAL_PARTICIPANT_HANDOFFS_REQUIRED`.
- V13 compiles recipient selection as a bounded constraint problem rather
  than a name list. Every nomination remains a declared candidate with zero
  authority until later signed enrollment.
- Candidate admission requires a current non-TEST nomination, a well-formed
  Ed25519 public key, one or more eligible roles, identity and external
  verification roots, disposed conflicts, and explicit evidence roots for
  institution, lineage, jurisdiction, domain, authority, funding, data,
  staff, and technology control.
- Every candidate pair is audited for shared identity, key, institution,
  lineage, jurisdiction, domain, authority, funding, data control, staff
  control, and technology control. Shared control is an explicit dependence
  edge, not independent corroboration.
- A five-seat cohort requires one distinct eligible candidate per role and
  exactly ten compatible pairwise audits. The solver explores assignments
  with a hard node budget and fails closed if the budget is exhausted.
- `NO_COHORT` yields no cohort. `MULTIPLE_COHORTS` also yields no selected
  cohort and requires explicit source-authorized selection. The solver never
  chooses a lexicographically convenient governance society.
- `UNIQUE_PROVISIONAL_COHORT` still grants no authority: the exact V12
  packets must be delivered and the V10 signed responses must independently
  pass before assembly.
- No candidates were inferred from contacts, documents, names, or prior
  relationships. The current V13 registry contains zero nominations and the
  exact barrier is `FIVE_EXTERNAL_CANDIDATE_NOMINATIONS_REQUIRED`.
- V14 turns that nomination barrier into a complete signed intake membrane:
  five role-bound calls are derived from the immutable V11 batch and bind the
  five exact V12 participant packet digests, V13 selection law, role mission,
  capabilities, evidence dimensions, canonical signature domain, and return
  boundary.
- Each candidate submission is a canonical V14 envelope signed by the Ed25519
  key declared inside its V13 nomination. Post-signature changes to role,
  evidence roots, identity, validity, or key material invalidate the complete
  envelope.
- Signature verification proves control of the declared key only. It does not
  independently establish identity, institutional affiliation, independence,
  evidence-root truth, fitness, delivery, enrollment, or governance authority.
- Duplicate envelope, nomination, or candidate identifiers are preserved as
  non-counting HOLD receipts. Invalid and expired submissions are also
  preserved without entering the cohort solver.
- A unique V13 cohort binds all five candidate declarations to their exact
  role calls and immutable V12 participant packets, together with all ten
  pair-audit digests. This binding is provisional, unaddressed, undelivered,
  and authority-free.
- `NO_COHORT`, `MULTIPLE_COHORTS`, and solver-budget exhaustion bind no
  packets. Ambiguity still requires explicit source-authorized selection.
- The current V14 state has five role calls prepared, zero published, zero
  signed submissions, zero packet assignments, and no governance activation.
  Its exact next seed is
  `KC144.V14::PUBLISH-FIVE-ROLE-CALLS-AND-INGEST-REAL-SIGNED-NOMINATIONS`.
- V15 closes the remaining cross-batch replay and call-substitution seam.
  The inner V14 signature still binds every nomination field; a second
  candidate signature now binds that exact signed envelope to the active V11
  batch identifier and root, the immutable V14 call-manifest root, the exact
  call identifier and digest for every eligible role, and submission time.
- The declared eligible-role set and the outer application's target-call set
  must be identical and canonically ordered. A candidate cannot declare broad
  eligibility while signing only a narrower transport surface.
- Applications from another batch, an altered manifest, a substituted call,
  a noncanonical role set, an invalid time window, or a post-signature
  mutation are preserved as non-counting HOLD receipts even when the inner
  nomination remains valid.
- Five publication payloads embed the complete V14 role calls and their
  immutable V12 packet references. They are ready for external transport but
  remain explicitly `READY_UNPUBLISHED`; no locator or publication receipt is
  invented.
- Duplicate application, envelope, nomination, or candidate identifiers are
  preserved and release no inner envelope to V14. Only a unique valid V15
  application crosses the transport membrane.
- Double-signature verification proves candidate-key control and byte
  integrity, not external publication, identity, independence, fitness,
  delivery, enrollment, ratification, or governance authority.
- The current V15 state has five publication payloads prepared, zero
  published, zero applications, zero packet assignments, and no governance
  activation. Its exact next seed is
  `KC144.V15::PUBLISH-FIVE-BATCH-BOUND-CALL-PAYLOADS-AND-INGEST-REAL-APPLICATIONS`.
- `KC144.V2::POPULATE_MATH144` is emitted only after a production M12
  certificate passes all nine gates.

“Completed” does not claim external deployment, independent cold replay, or
solid-state certification. Those are live empirical states, not missing
architecture.

## Integrated runtimes

- `kc144_crystal`: whole-crystal generator, transformer, population compiler,
  and global auditor.
- `kc144`: frozen atlas validator and bounded router.
- `memory_crystal`: P03 metro, P04 federation compiler, and P06 live internal
  navigation/reentry.
- `athena_git_brain`: immutable resource identity, witnessed graph routing,
  return plans, and conjunctive promotion readiness.
- `athena_immune`: append-only immune cycle, IC10, KC54 audit, trust revision,
  repair scheduling, reentry permits, and QSHRINK.

The `evidence/` directory preserves the executed GID051, GID082, and GID090
witnesses plus the canonical source texts used for this synthesis.

See `SYSTEMATIC_FRAMEWORK_V3.md` for the complete crystal synthesis and
`MYCELIUM_FRAMEWORK_V4.md` for the query, route, witness, and return runtime.
See `GLOBAL_STATE_FRAMEWORK_V5.md` for the edge manifest, traversal ledger,
SSN12 observatory, two-phase bridge commit, cold reconstruction, and M12 gate.
See `M12_REPAIR_FRAMEWORK_V6.txt` for the evidence packet, append-only repair
ledger, dependency DAG, M12 recomputation, and exact MATH144 issuance law.
The generated `registry/v7` documents define the production authority
registry, active-epoch crosswalk, graph-slice registry, signed-envelope
contract, and current fail-closed readiness state.
The generated `registry/v8` documents define the exact parallel campaign,
authority-enrollment boundary, ready-subgraph state, run-to-barrier report,
and current external-governance barrier.
The generated `registry/v9` documents define threshold governance, transparent
revocation state, source-once/fan-out evidence requirements, sixteen external
handoff requests, resumable return admission, and the current five-member
governance-enrollment barrier.
The generated `registry/v10` documents define the five-role enrollment
ceremony, external ratification contract, exact empty-seat plan, fail-closed
runtime state, and current live-human response barrier.
The generated `registry/v11` documents preserve the issued five-role
challenge batch, batch-bound parallel response router, dispatch contract,
live operational plan, runtime state, and release.
The generated `registry/v12` documents define the complete participant
handoff contract and manifest, five role-specific packets, batch-bound return
verification, current external-delivery barrier, runtime state, and release.
The generated `registry/v13` documents define candidate declarations, the
multidimensional dependence graph, bounded role-assignment solver, exact
10-pair independence law, empty live candidate registry, runtime state, and
current nomination barrier.
The generated `registry/v14` documents define the signed nomination intake
contract, five role-bound calls, immutable call manifest, fail-closed receipt
ledger, provisional cohort-to-packet assignment manifest, runtime state, and
current external publication/intake barrier.
The generated `registry/v15` documents define the batch-bound application
transport contract, five publication-ready role payloads, immutable
publication manifest, double-signature application ledger, runtime state, and
current external publication/application barrier.

P39 and P40 extend the live-cognition frontier without weakening any external
boundary. `registry/p39-live-outcome/v1` provides signed outcome admission,
strict calibration/held-out separation, deterministic weight proposals, a
fixed five-seat IC10 registry, and exact three-of-five successor authorization.
`registry/p40-activation/v1` adds the compare-and-swap canonical weight commit,
typed sibling-lineage reconciliation, single-generation activation, and a
forward-only post-activation outcome watch. The frozen releases contain no
fabricated outcomes or authorities and therefore remain honest HOLD snapshots.

See `P39_LIVE_OUTCOME_IC10_FRAMEWORK.md` and
`P40_ACTIVATION_TRANSACTION_FRAMEWORK.md` for the exact executable laws,
receipts, non-collapse boundaries, and successor seeds.
