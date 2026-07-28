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

```text
NEXT::KC144.V1::P31_EXACT_RUNTIME_ADAPTER_AND_WITNESSED_TOOL_OUTCOME_INTAKE
RETURN::KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH
PARENT::KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS
```
