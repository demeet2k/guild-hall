# ATHENA Synapse ABI V1

`ATHENA.SYNAPSE.ENVELOPE.V1` is the small cross-repository boundary between ATHENA organs. It does **not** replace the MCP Message Board, Liminal Beacon Mesh, Frontier Claim machinery, Federation V1, Guild Hall receipts, or any organ-native state. It makes their returns addressable to one another without erasing provenance or pretending projections are lossless.

## Boundary

Every bridge packet names the native system, native event ID, source repository revision, source node, explicit causal references, return route, epistemic class, authority/truth ceilings, native frontier status, projection loss, and separate wall/observation clocks. The deterministic bridge event ID excludes wall time and frontier state, so replaying the same immutable source event later is idempotent.

`origin_sequence` is optional and only comparable inside the source that issued it. There is no scalar "global latest" clock. Cross-node ordering comes from explicit `parent_ids`, `reply_to`, `correction_of`, `retraction_of`, and `supersedes` edges.

## Projection / return discipline

Every envelope carries a projection profile and one of three loss classes:

- `LOSSLESS`: no declared lost fields and a return token is mandatory.
- `LOSSY_AUX`: lost fields are explicit and a return token is mandatory so the native source can reconstruct them.
- `NONRETURNABLE`: losses are explicit and no return token may be claimed.

The projection profile participates in bridge identity; two different projections of the same native event therefore cannot collide accidentally. `preserved` and `lost` describe field/invariant classes, not a proof of semantic equivalence.

## Frontier discipline

`frontier.semantics` is one of `NATIVE_EVENT_FRONTIER`, `NATIVE_SNAPSHOT`, `BRIDGE_VECTOR`, or `UNKNOWN`. A known frontier must provide a native digest or native reference. `UNKNOWN` may not carry an asserted digest. The bridge never derives a global total order from these fields.

## Receipt semantics

Receipt stages intentionally match the MCP liminal mesh: `PRESENTED → CONSUMED → INCORPORATED → DECISION_CHANGED → PROPAGATED`. A router may write PRESENTED. It may not infer any later stage. `MESSAGE_ROUTE != CONSUMPTION` remains law across the bridge.

## Event projection

The shared event vocabulary is the Federation V1 vocabulary: `OBSERVATION`, `PROPOSAL`, `CLAIM`, `EFFECT`, `RECEIPT`, `WITNESS`, `CONTRADICTION`, `HOLD`, `RETURN`, `SUPERSESSION`. Native message kinds remain in `semantics.native_kind`; projection never destroys the original kind silently.

## Idempotency and contradictions

`event_id = SYN-<sha256(schema,projection_profile,node_id,repository,native_system,native_event_id,source_revision)[:32]>`.

Identical bridge IDs with identical bodies are replay duplicates. Identical bridge IDs with different bodies are **not** merged: conformance raises `SAME_BRIDGE_ID_DIFFERENT_BODY` as a HOLD. A correction or retraction must point to what it changes.

## Conservative GC

The shared tool can report exact replay duplicates and explicitly retired events, but never deletes them. Causal parents, replies, corrections and retractions remain retention roots. Deletion/promotion policy belongs to the owning repository and requires its normal authority path.

## Commands

```bash
python tools/athena_synapse_conformance.py validate fixtures/athena_synapse_vectors_v1.json
python tools/athena_synapse_conformance.py frontier fixtures/athena_synapse_vectors_v1.json
python tools/athena_synapse_conformance.py causal fixtures/athena_synapse_vectors_v1.json
python tools/athena_synapse_conformance.py gc fixtures/athena_synapse_vectors_v1.json
```

## Source-of-truth boundary

Guild Hall owns the ABI/schema/conformance vectors. `demeet2k/Athena` owns Federation semantics. `demeet2k/athena-mcp-server` owns live MCP transport, Message Board, Liminal Beacon, frontier and receipt behavior. Element repos remain `MANIFEST_REQUIRED` until they explicitly publish a compatible node manifest; the registry does not invent capabilities for them.
