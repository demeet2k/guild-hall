# Return to Athena

This repository is a `coordination` participant, not the federation root.

1. Read `.athena/repo.json` and resolve `athena.repo.guild-hall@contract-proposal-0.1.0`.
2. Preserve the repository occurrence witnessed by base commit `742eaab8be2801575d1dd1895ce64b8d3d0237c6`.
3. Follow `edge.guild-hall-to-control` in `.athena/edges.jsonl`.
4. Carry the local manifest, exact repository commit, control commit
   `3d33fbcd6248fc2dc2991fbbab5e93a7eb184246`, and any route receipt.
5. Resolve the control plane at
   `github://demeet2k/Athena@3d33fbcd6248fc2dc2991fbbab5e93a7eb184246/.athena/repo.json`.
6. If the manifest, carrier, generator lineage, witness, or reverse edge is
   missing, stop with the defect recorded in `.athena/status.json`.

This return is `compensated`: it preserves identity, role, provenance, and
authority boundaries, but it does not claim that this repository reproduces the
full Google Docs, conversation memory, manuscript corpus, or Athena runtime.
