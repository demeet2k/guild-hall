# KC144 Parallel Navigation Registry V1

This registry stores immutable, coordinate-bound outputs of the five-lane
parallel route compiler.

## Current coordinate

```text
IMMUTABLE_COMMIT::1b653e39d7c09ba8b93a800860244242cd98d397
IMMUTABLE_TREE::d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b
COMPILER_COMMIT::77c67543b0d6df946d7ffa7d17242bf869c3ad1b
COMPILER_TREE::0fdb2184b9c9777f557102a84c44ac034991fe5f
SNAPSHOT_DIGEST::sha256:c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d
SNAPSHOT_FILE_SHA256::sha256:55edf1d37b065229863544c556954537b2b8a6c7dc355a92960832336d1e3188
MAXIMUM_PARALLEL_WIDTH::5
```

- [Parallel route framework](../../../KC144_PARALLEL_ROUTE_FRAMEWORK.md)
- [Parallel-agent scheduler](../../../KC144_PARALLEL_AGENT_SCHEDULER.md)
- [Current snapshot](snapshots/sha256/c8/c8e1a1a7c55a144b7bf20b49ff3fd01ca292a0cd34f134ce0a0abf0d9ac0bc1d.json)
- [Compiler binding](sources/compiler-trees/0fdb2184b9c9777f557102a84c44ac034991fe5f.json)

Snapshots are deterministic products of the immutable atlas coordinate and the
exact compiler commit/tree. They enumerate the complete bounded typed-path
universe for each declared route while expanding only a bounded set of shortest
witnesses.

```text
CONTENT_TRANSPORT_CERTIFIED::FALSE
GOVERNANCE_AUTHORITY_GRANTED::FALSE
PRODUCTION_TRUTH_EFFECT::NONE
```
