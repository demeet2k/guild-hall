# KC144 Native Kernel Campaign — P2.T4

This branch executes the highest-unblock task selected by `KC144.MATH.META.ORCHESTRATOR.V1.0`:

```text
P2.T4 — Execute native Lean/Rocq kernels
```

## Scope

- `formal/lean/KC144Core.lean` — core-only Lean checks.
- `formal/lean/SelmerIntegralUnit.lean` — finite Selmer arithmetic and residue checks using Mathlib.
- `formal/rocq/KC144Safe.v` — Rocq/Coq safe theorem batch.
- `formal/receipts/kernel_receipt.schema.json` — machine-readable receipt contract.
- `.github/workflows/kc144-native-kernel.yml` — native CI jobs and artifact receipts.

## Authority boundary

A source file, linter pass, or generated receipt template is not a native proof certificate. A subclaim can advance only when its exact source digest is accepted by the declared native checker and the resulting GitHub Actions receipt passes provenance, toolchain, return-code, and placeholder gates.

This branch is separate from the immutable `kc144-completed-crystal-v15` tree and grants no governance or production-truth authority.
