# Athena federation contract

This directory makes `demeet2k/guild-hall` a typed participant in the Athena Git Brain.
It does not copy the Athena corpus or grant this repository global authority.

- Resource: `athena.repo.guild-hall@contract-proposal-0.1.0`
- Role: `coordination`
- Authority domain: `coordination-only`
- Base content witness: `742eaab8be2801575d1dd1895ce64b8d3d0237c6`
- Control-plane schema commit: `3d33fbcd6248fc2dc2991fbbab5e93a7eb184246`
- State: `NO_CODE_AUTHORITY`

`repo.json` declares the local surface. `exports.jsonl` exposes bounded
identities. `imports.lock.json` pins the control-plane schema. `edges.jsonl`
contains the forward declaration and its explicit return edge. `status.json`
preserves blockers instead of promoting them away.
