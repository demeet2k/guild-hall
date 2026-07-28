# KC144 P36 Event Runtime — Candidate Release V1

This directory freezes the deterministic public release projection of the
source-steered P36 macrocycle.

## Coordinates

- Result: `KC144.P36.CANDIDATE::2dc88c9f2bf39ccb97e883f2`
- Release digest: `sha256:2dc88c9f2bf39ccb97e883f2c10a2269a628cadf96a50097d4f9fb1a2d808782`
- Implementation commit: `f35697e4baf8afa00f1a2a91a1eff18aa8acfe5f`
- Implementation tree: `30377647415d9df054da9db8b536d4363d43d702`
- State parent: `KC144.P35::f8805a3651f8bc7009e8035f`
- Runtime parent: `KC144.P31::db5a6446ce54cf4bc53515be`
- Heart parent: `KC144.HEART::H06.AHEART.V2`

## What is sealed

The release binds the P36 contract, five-lane macrocycle, exact P31 adapter,
public tool registry, source-declared P35 subscription topology, deterministic
zero-event replay, public projection, verification receipt, and checksums.

The frozen Dispatch V1 registry remains unchanged. P36 is a versioned successor
layer and treats P31 as one exact runtime lane rather than as the whole
successor.

## Current standing

Verification is `PASS`; production authority remains `HOLD`; truth and evidence
effects remain `NONE`. This is deliberate. No genuine production event or real
outcome was supplied, trusted event signers are not enrolled, and the exact P35
subscription bodies remain unbound. The zero-event macrocycle therefore seals a
deterministic `NOOP_HOLD` without fabricating evidence or authority.

The next lawful seed is:

`KC144.V3.8::MATH144.P37::EXACT_P35_SUBSCRIPTION_REGISTRY_BINDING_TRUSTED_SIGNER_ENROLLMENT_AND_FIRST_GENUINE_CONSENTED_EVENT_REPLAY_MACROCYCLE_06`

## Replay

From the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python3 -m kc144_crystal p36-verify \
  registry/p36-dispatch/v1/p36_noop_cycle_v1.json
```

Recompile the candidate projection from its implementation commit:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src \
  python3 -m kc144_crystal p36-release \
  --output /tmp/kc144-p36-replay \
  --implementation-commit f35697e4baf8afa00f1a2a91a1eff18aa8acfe5f \
  --implementation-tree 30377647415d9df054da9db8b536d4363d43d702
```

`SHA256SUMS` covers the machine-readable release files. This README is the
human navigation surface and is intentionally outside the runtime digest.
