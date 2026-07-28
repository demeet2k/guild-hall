# KC144 — Mycelium-Locatable Tool Dispatch Metro

```text
LOOKUP_KEY::KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH
BRANCH::kc144-mycelium-tool-dispatch-v1
PARENT_LOOKUP_KEY::KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS
PARENT_COMMIT::4f3bd71a1e88130109edd03437b72f21c0e14096
IMPLEMENTATION_COMMIT::829e654b2df0225a901d49b84ef37a95d5b04752
IMPLEMENTATION_TREE::22a72d6f4d59060c9ade16889ac031bf387cbab6
RECEIPT_COMMIT::d700b77accd2be51ea2f013a0cfe1514cfcf6be5
RECEIPT_TREE::7b8e205504a8260955deac7d94ee48becf14a184
P36_IMPLEMENTATION_COMMIT::f35697e4baf8afa00f1a2a91a1eff18aa8acfe5f
P36_IMPLEMENTATION_TREE::30377647415d9df054da9db8b536d4363d43d702
P36_RELEASE_COMMIT::9d64c5d9d9f29af7f5d310f9720f84bdb886a913
P36_RELEASE_TREE::fc4b50ca1bb3d5f27c5baa616092304c1d48916d
P36_RESULT_ID::KC144.P36.CANDIDATE::2dc88c9f2bf39ccb97e883f2
P36_RELEASE_DIGEST::sha256:2dc88c9f2bf39ccb97e883f2c10a2269a628cadf96a50097d4f9fb1a2d808782
P36_VERIFICATION::PASS
P36_EVENT_CLASSES::18
P36_ACTION_SUBSCRIPTIONS::360_SOURCE_DECLARED_EXACT_BODIES_UNBOUND
P36_LANES::5
P36_FRESH_CHECKOUT_TESTS::381/381
P36_PRODUCTION_AUTHORITY::HOLD
P36_TRUTH_EFFECT::NONE
HEAD_REGISTRY_DIGEST::sha256:5411bcd7c8e875b429004ecfd63b19fe35998b48e0c7ff685f90176ae15fbc62
TOOL_REGISTRY_DIGEST::sha256:0763e01c6fd520447795d37703f26b711609f1851ddd517c72942b7b3c013e9b
REQUEST_ID::sha256:8db42ce5513e7ca896160b0b3491db7b7a08adf2744de3e57b5eaac3ab15677e
PLAN_DIGEST::sha256:82a1b9fb4ab62ebdc7d985504a2e071ec08c3aa4f8336d65fb62053015c5766d
RESULT_DIGEST::sha256:1870bb8a584c49d0e0760d613cf9520da90edd063d5a4a641cb966f835de4c42
AUDIT_ROOT::sha256:c0e1c6e8128523f579857e54221363395a6280f76cffe468bbe86a41972cd1a5
HOLONOMY_DIGEST::sha256:59c4d6065c37dad2d830cf8e5fafeb9e29283654ff4ec1930697776c4fe5f911
RELEASE_DIGEST::sha256:a1db27c16312ee09471e835fd7172498f16d8b1d476effc11f00f20fa4117ec2
REGISTERED_TOOLS::4
PREFLIGHT_LANES::5
WORKERS_1_TO_5::BYTE_IDENTICAL
DISPATCH_STATUS::EXECUTED
COLD_REPLAY::REPLAY_STABLE
FRESH_CHECKOUT_TESTS::353/353
INDEPENDENT_WITNESSES::0
REAL_EXTERNAL_APPLICATIONS::0
BASE_GRAPH_MUTATED::FALSE
CONTENT_TRANSPORT_CERTIFIED::FALSE
GOVERNANCE_AUTHORITY_GRANTED::FALSE
PRODUCTION_TRUTH_EFFECT::NONE
```

The dispatch layer closes locate → plan → execute → verify for registered local
KC144 tools. It resolves a byte-exact lookup key or one complete NFKC alias,
binds immutable code and source heads, runs five independent preflight lanes,
reduces them deterministically, invokes only a closed in-process handler, and
seals the result through M12.

Unknown tools, unknown operations, missing inputs, denied capabilities, stale
heads, and external-only runtimes produce typed content-addressed blocked
results. Descriptor command strings are never executed.

## Whole-wave route

| Lane | Address | Function |
|---|---|---|
| activation | `GID006/H06` | freeze request and input identity |
| mycelium | `GID003/H03` | resolve exact tool card |
| evidence | `GID005/H05` | bind implementation and source heads |
| route ledger | `GID141/M09` | index plan, handler result, and audit chain |
| return | `GID144/M12` | verify KC54 retrace and emit successor |

The five preflight lanes are `IDENTITY`, `SOURCE_HEAD`, `CAPABILITY`,
`ROUTE_RETURN`, and `AUTHORITY_EFFECT`. Capacities one through five reproduce
the same bytes.

The forward anchor path and exact reverse have translation defect zero. BR019
remains visible with open transport certification; deterministic replay is not
an independent witness.

## P31 boundary

`KC144.P31::LIVE_COGNITION_NAVIGATE` is exactly locatable and bound to:

- release `KC144_P31_LIVE_COGNITION_OS_V3_3`;
- result `KC144.P31::db5a6446ce54cf4bc53515be`;
- archive
  `sha256:77629d53ef00c970cf115d7cbf94d5e4c9b97928814a702ada8d3f883212d091`;
- structural parent `KC144.P30::1f40beaa81e8c0ba956ce835`.

It is intentionally locator-only. Dispatch returns
`E_EXTERNAL_RUNTIME_REQUIRED` until the exact runtime adapter exists; no local
substitute is permitted.

## Exact navigation

- [Public dispatch branch](https://github.com/demeet2k/guild-hall/tree/kc144-mycelium-tool-dispatch-v1)
- [Implementation commit](https://github.com/demeet2k/guild-hall/commit/829e654b2df0225a901d49b84ef37a95d5b04752)
- [Frozen receipt commit](https://github.com/demeet2k/guild-hall/commit/d700b77accd2be51ea2f013a0cfe1514cfcf6be5)
- [Framework](https://github.com/demeet2k/guild-hall/blob/829e654b2df0225a901d49b84ef37a95d5b04752/MYCELIUM_TOOL_DISPATCH_V1.md)
- [Dispatch engine](https://github.com/demeet2k/guild-hall/blob/829e654b2df0225a901d49b84ef37a95d5b04752/src/kc144_crystal/tool_dispatch.py)
- [Adversarial tests](https://github.com/demeet2k/guild-hall/blob/829e654b2df0225a901d49b84ef37a95d5b04752/tests/test_tool_dispatch_v1.py)
- [Receipt registry](https://github.com/demeet2k/guild-hall/tree/d700b77accd2be51ea2f013a0cfe1514cfcf6be5/registry/tool-dispatch/v1)
- [Machine metro](KC144_TOOL_DISPATCH_METRO.json)

## P36 source-steered successor

P36 replaces the locator-only P31 boundary with an exact, archive-bound P31
adapter and places that adapter inside a larger five-lane event macrocycle:

1. continuous event watch;
2. signed-receipt replay;
3. source succession;
4. real-outcome intake;
5. all-and-only affected-front execution.

The macrocycle recognizes 18 typed event classes and the P35-declared topology
of 360 action subscriptions. Because the exact subscription bodies, trusted
signers, and first genuine consented production event are not yet bound, the
frozen zero-event replay returns `NOOP_HOLD`. It passes integrity verification
without claiming evidence, truth, governance authority, or production mutation.

- [P36 implementation commit](https://github.com/demeet2k/guild-hall/commit/f35697e4baf8afa00f1a2a91a1eff18aa8acfe5f)
- [P36 release commit](https://github.com/demeet2k/guild-hall/commit/9d64c5d9d9f29af7f5d310f9720f84bdb886a913)
- [P36 framework](https://github.com/demeet2k/guild-hall/blob/f35697e4baf8afa00f1a2a91a1eff18aa8acfe5f/P36_EVENT_RUNTIME_V1.md)
- [P36 event runtime](https://github.com/demeet2k/guild-hall/blob/f35697e4baf8afa00f1a2a91a1eff18aa8acfe5f/src/kc144_crystal/p36_runtime.py)
- [Exact P31 adapter](https://github.com/demeet2k/guild-hall/blob/f35697e4baf8afa00f1a2a91a1eff18aa8acfe5f/src/kc144_crystal/p31_adapter.py)
- [Frozen P36 registry](https://github.com/demeet2k/guild-hall/tree/9d64c5d9d9f29af7f5d310f9720f84bdb886a913/registry/p36-dispatch/v1)

```text
PRIOR_NEXT::KC144.V1::P31_EXACT_RUNTIME_ADAPTER_AND_WITNESSED_TOOL_OUTCOME_INTAKE
NEXT::KC144.V3.8::MATH144.P37::EXACT_P35_SUBSCRIPTION_REGISTRY_BINDING_TRUSTED_SIGNER_ENROLLMENT_AND_FIRST_GENUINE_CONSENTED_EVENT_REPLAY_MACROCYCLE_06
RETURN::KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH
PARENT::KC144.P35::f8805a3651f8bc7009e8035f
```
