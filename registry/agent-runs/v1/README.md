# KC144 Agent-Run Registry V1

This registry stores immutable content-addressed execution receipts for the
parallel KC144 route compiler.

## Current coordinate

```text
LOOKUP_KEY::KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS
BRANCH::kc144-agent-run-receipts-v1
PARENT_BRANCH::kc144-parallel-navigation-v1
PARENT_SNAPSHOT_COMMIT::475259f5ca3e5da3528eddda59f411baf37e57c0
PARENT_SNAPSHOT_DIGEST::sha256:c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d
RUNTIME_COMMIT::91cf0e3c2e8da10ed0787ebf1c0c0105aaf988a9
RUNTIME_TREE::bc44c4f14b25894a8251e8c1289b718e04eef32a
RUN_ID::sha256:0277d691593684417720414f2a2fd00436811e86d946cdc4eb2b1c0e975beb04
PLAN_DIGEST::sha256:e931514ea1840ec12766ec198ff1989f84d80ff9ffdd01577fa0e568f50a9ad9
MANIFEST_DIGEST::sha256:89cb8d76f3a2cc8a0addfcf1eea3ad5836f7833390a21c25667ecc57ee79d377
AUDIT_ROOT::sha256:30f0a04797aea055a99ea7da21c2583b2e9bb9fec60e2ac6ac01c48d1f266d0a
BUNDLE_DIGEST::sha256:52b8b2896a7bd1fff45dc3df84ac031172a3bc469375e3d3c775c8e9cb0aef59
BUNDLE_FILE_SHA256::sha256:7c4feb1135f9c968cc6adace8fe4a75a56ce21c4ad52349b36c504c33aa2f943
ACCEPTED_RECEIPTS::6
EVENT_COUNT::32
INDEPENDENT_WITNESSES::0
```

- [Framework](../../../KC144_AGENT_RUN_RECEIPTS.md)
- [Machine index](index.json)
- [Current receipt bundle](runs/sha256/02/0277d691593684417720414f2a2fd00436811e86d946cdc4eb2b1c0e975beb04.json)
- [Frozen runtime binding](sources/runtime-trees/bc44c4f14b25894a8251e8c1289b718e04eef32a.json)

The reference run contains five isolated route-simulation results and one
deterministic reducer result. Capacities one through five replay to identical
canonical bytes. The physical worker count and completion order are excluded
from the content-addressed identity graph.

```text
BASE_GRAPH_MUTATED::FALSE
CONTENT_TRANSPORT_CERTIFIED::FALSE
GOVERNANCE_AUTHORITY_GRANTED::FALSE
PRODUCTION_TRUTH_EFFECT::NONE
```
