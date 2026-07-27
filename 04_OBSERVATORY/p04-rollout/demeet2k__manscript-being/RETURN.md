# Return Contract — demeet2k/manscript-being

This repository is a federated Athena seed at immutable snapshot
`5d4e03045001ede922af94fb7bd1ae326f6877ec`. The branch name `main` is a
discovery pointer, not the identity of this return packet.

## Return path

1. Read `SEED.json` for identity and role.
2. Read `PROVENANCE.json` for the source ledger and control-plane witness.
3. Read `RELATIONS.json` for typed lateral routes.
4. Read `STATE.json` before treating this packet as published or replayed.
5. Return to `demeet2k/Athena` at `850a7af91b2b418adfb70547a9473a182abd9b6a`.

## Declared routes

- `legacy-of` → `repo-manuscript-being`

## Refusal law

If the pinned commit, source-ledger digest, or target identity cannot be
recovered, return `UNRESOLVED` with the failed coordinate. Do not substitute a
branch head, a similarly named repository, or a textually similar artifact.
