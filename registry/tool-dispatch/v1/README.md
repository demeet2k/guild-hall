# KC144 mycelium tool-dispatch registry

This directory is the immutable receipt generation for
`KC144.V1::MYCELIUM_LOCATABLE_TOOL_DISPATCH`.

The executable implementation is commit
`829e654b2df0225a901d49b84ef37a95d5b04752`, tree
`22a72d6f4d59060c9ade16889ac031bf387cbab6`.

Start with:

- `dispatch_release_v1.json` for the compact release coordinates;
- `head_registry_v1.json` for exact replay heads;
- `tool_registry_v2.json` for the four tool cards;
- `dispatch_contract_v1.json` for execution laws;
- `dispatch_request_v1.json` and `dispatch_result_v1.json` for the readable
  aliases of the frozen content-addressed request and result;
- `dispatch_verification_v1.json` for the cold-replay verdict;
- `requests/sha256/` and `results/sha256/` for immutable address paths.

The recorded invocation resolves and executes the registered
`KC144.V1::CONTENT_ADDRESSED_AGENT_RUN_RECEIPTS` verifier in process. It returns
`PASS`, seals an exact KC54 retrace, and leaves BR019 visible and uncertified.

P31 is locatable under `KC144.P31::LIVE_COGNITION_NAVIGATE` but remains blocked
with `E_EXTERNAL_RUNTIME_REQUIRED`; no local handler is substituted.

This release adds zero independent witnesses, zero real external applications,
zero governance authority, zero truth effect, and zero transport
certifications.
