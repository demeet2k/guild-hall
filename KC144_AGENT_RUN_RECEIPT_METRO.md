# KC144 — Content-Addressed Agent-Run Receipt Metro

```text
LOOKUP_KEY::KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS
BRANCH::kc144-agent-run-receipts-v1
PARENT_BRANCH::kc144-parallel-navigation-v1
PARENT_SNAPSHOT_COMMIT::475259f5ca3e5da3528eddda59f411baf37e57c0
PARENT_SNAPSHOT_DIGEST::sha256:c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d
RUNTIME_COMMIT::91cf0e3c2e8da10ed0787ebf1c0c0105aaf988a9
RUNTIME_TREE::bc44c4f14b25894a8251e8c1289b718e04eef32a
RECEIPT_COMMIT::4f3bd71a1e88130109edd03437b72f21c0e14096
RECEIPT_TREE::c15740c445baa1f98e20b3172fb8637c9b44271a
RUN_ID::sha256:0277d691593684417720414f2a2fd00436811e86d946cdc4eb2b1c0e975beb04
PLAN_DIGEST::sha256:e931514ea1840ec12766ec198ff1989f84d80ff9ffdd01577fa0e568f50a9ad9
MANIFEST_DIGEST::sha256:89cb8d76f3a2cc8a0addfcf1eea3ad5836f7833390a21c25667ecc57ee79d377
AUDIT_ROOT::sha256:30f0a04797aea055a99ea7da21c2583b2e9bb9fec60e2ac6ac01c48d1f266d0a
BUNDLE_DIGEST::sha256:52b8b2896a7bd1fff45dc3df84ac031172a3bc469375e3d3c775c8e9cb0aef59
BUNDLE_FILE_SHA256::sha256:7c4feb1135f9c968cc6adace8fe4a75a56ce21c4ad52349b36c504c33aa2f943
TASK_RECEIPTS::6
AUDIT_EVENTS::32
MAXIMUM_PARALLEL_WIDTH::5
WORKERS_1_TO_5::BYTE_IDENTICAL
INDEPENDENT_WITNESSES::0
BASE_GRAPH_MUTATED::FALSE
CONTENT_TRANSPORT_CERTIFIED::FALSE
GOVERNANCE_AUTHORITY_GRANTED::FALSE
PRODUCTION_TRUTH_EFFECT::NONE
```

The receipt layer seals the existing five-lane route crystal as one
content-addressed execution graph: task → plan → input → run → lease → result
→ receipt → event chain → manifest → bundle. Five route tasks form the first
dependency wave; one deterministic reducer forms the second. Physical worker
count, result arrival order, wall-clock time, and provider identity are
noncanonical telemetry, so capacities one through five reproduce identical
bytes.

## Mycelium coordinates

| Function | Address | Exact route from H06 | Standing |
|---|---|---|---|
| locate | `GID003/H03` | `006→001→002→003` | structural |
| bind source | `GID005/H05` | `006→005` | structural |
| activate/replay | `GID006/H06` | `006` | structural |
| execute waves | `GID135/M03` | `006→001→144→143→142→141→140→139→138→137→136→135` | declared; `BR019` open |
| index receipts | `GID141/M09` | `006→001→144→143→142→141` | declared; `BR019` open |
| verify/return | `GID144/M12` | `006→001→144` | declared; `BR019` open |

The tool overlay does not add graph edges. Location and local execution do not
certify semantic transport across `BR019`, grant governance authority, or
change production truth.

## Exact navigation

- [Executable receipt branch](https://github.com/demeet2k/guild-hall/tree/kc144-agent-run-receipts-v1)
- [Framework](https://github.com/demeet2k/guild-hall/blob/91cf0e3c2e8da10ed0787ebf1c0c0105aaf988a9/KC144_AGENT_RUN_RECEIPTS.md)
- [Receipt compiler](https://github.com/demeet2k/guild-hall/blob/91cf0e3c2e8da10ed0787ebf1c0c0105aaf988a9/src/kc144_crystal/agent_receipts.py)
- [Mycelium tool registry](https://github.com/demeet2k/guild-hall/blob/91cf0e3c2e8da10ed0787ebf1c0c0105aaf988a9/src/kc144_crystal/tool_registry.py)
- [Adversarial tests](https://github.com/demeet2k/guild-hall/blob/91cf0e3c2e8da10ed0787ebf1c0c0105aaf988a9/tests/test_agent_run_receipts_v1.py)
- [Receipt registry](https://github.com/demeet2k/guild-hall/tree/4f3bd71a1e88130109edd03437b72f21c0e14096/registry/agent-runs/v1)
- [Current receipt bundle](https://github.com/demeet2k/guild-hall/blob/4f3bd71a1e88130109edd03437b72f21c0e14096/registry/agent-runs/v1/runs/sha256/02/0277d691593684417720414f2a2fd00436811e86d946cdc4eb2b1c0e975beb04.json)
- [Machine metro](KC144_AGENT_RUN_RECEIPT_METRO.json)

```text
NEXT::KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH
RETURN::KC144.V1::PARALLEL_ROUTE_CRYSTAL
PARENT::KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS
```
