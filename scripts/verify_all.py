#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def run(label: str, command: list[str], cwd: Path = ROOT, env: dict[str, str] | None = None) -> dict[str, object]:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    return {
        "label": label,
        "command": command,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }


def main() -> int:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    runs = [
        run(
            "P45 second window, route/surface stability, and reversible retention",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "p45-release",
                "--output",
                "registry/p45-edge-retention/v1",
                "--implementation-commit",
                "0000000000000000000000000000000000000000",
                "--implementation-tree",
                "0000000000000000000000000000000000000000",
            ],
            env=env,
        ),
        run(
            "P44 forward outcomes, nondegradation, and canonical edge effect",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "p44-release",
                "--output",
                "registry/p44-edge-effect/v1",
                "--implementation-commit",
                "0616d4d391bcec661c4d493dc4a8b81413af8640",
                "--implementation-tree",
                "ce731a5a4b964d483f81f93788b3f1276db5db0b",
            ],
            env=env,
        ),
        run(
            "P43 admission, exactly-once finality, replay, and forward watch",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "p43-release",
                "--output",
                "registry/p43-admission-finality/v1",
                "--implementation-commit",
                "704f9d525bcf0eec858939a1f2fc5cfc7e936ebc",
                "--implementation-tree",
                "f7779ca4abe1a12f1096d49dd35bdc2f56b1cdfe",
            ],
            env=env,
        ),
        run(
            "P42 enumeration, outcome, IC10, edge transaction, and post-edge watch",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "p42-release",
                "--output",
                "registry/p42-edge-transaction/v1",
                "--implementation-commit",
                "d9f4904b033cb5039af2516dc1bb257113802f75",
                "--implementation-tree",
                "4826261e3f9944e963e1545a1b03388d23332c49",
            ],
            env=env,
        ),
        run(
            "P41 source-tree cohort, third-edge, and IC10 boundary",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "p41-release",
                "--output",
                "registry/p41-source-tree-cohort/v1",
                "--implementation-commit",
                "dab8df8ce76c3f58ee0df8501719e384e95872f7",
                "--implementation-tree",
                "bdb136a38990b4f2cc9d889e339826d630fd9b05",
            ],
            env=env,
        ),
        run(
            "P40 activation transaction and post-activation watch",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "p40-release",
                "--output",
                "registry/p40-activation/v1",
                "--implementation-commit",
                "1451b0ec0e7bec6efdc35f1ad30c8efa5c4473df",
                "--implementation-tree",
                "c46260fb616fc4a3eeb91f730904c004e16a1169",
            ],
            env=env,
        ),
        run(
            "P39 live-outcome and independent-IC10 runtime",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "p39-release",
                "--output",
                "registry/p39-live-outcome/v1",
                "--implementation-commit",
                "762a556cece499ce3fc12a265aa9f665006ce8aa",
                "--implementation-tree",
                "ae4eb814e10ae03a3b9da71950c5a3bc20d6e02a",
            ],
            env=env,
        ),
        run(
            "application transport V15 runtime",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "application-transport",
                "--output",
                "registry/v15",
                "--challenge-batch",
                "registry/v11/governance_challenge_batch_v11.json",
            ],
            env=env,
        ),
        run(
            "nomination intake V14 runtime",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "nomination-intake",
                "--output",
                "registry/v14",
                "--challenge-batch",
                "registry/v11/governance_challenge_batch_v11.json",
            ],
            env=env,
        ),
        run(
            "candidate selection V13 runtime",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "candidate-selection",
                "--output",
                "registry/v13",
                "--challenge-batch",
                "registry/v11/governance_challenge_batch_v11.json",
            ],
            env=env,
        ),
        run(
            "participant handoff V12 runtime",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "participant-handoff",
                "--output",
                "registry/v12",
                "--challenge-batch",
                "registry/v11/governance_challenge_batch_v11.json",
            ],
            env=env,
        ),
        run(
            "governance dispatch V11 runtime",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "governance-dispatch",
                "--output",
                "registry/v11",
                "--challenge-batch",
                "registry/v11/governance_challenge_batch_v11.json",
            ],
            env=env,
        ),
        run(
            "governance ceremony V10 runtime",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "governance-ceremony",
                "--output",
                "registry/v10",
            ],
            env=env,
        ),
        run(
            "external handoff V9 runtime",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "handoff-runtime",
                "--output",
                "registry/v9",
            ],
            env=env,
        ),
        run(
            "parallel campaign V8 runtime",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "campaign-runtime",
                "--output",
                "registry/v8",
            ],
            env=env,
        ),
        run(
            "production evidence V7 kernel",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "evidence-kernel",
                "--output",
                "registry/v7",
            ],
            env=env,
        ),
        run(
            "M12 repair V6 compiler",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "repair",
                "--output",
                "registry/v6",
            ],
            env=env,
        ),
        run(
            "global state V5 compiler",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "global-state",
                "--output",
                "registry/v5",
            ],
            env=env,
        ),
        run(
            "mycelium V4 compiler",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "mycelium",
                "--output",
                "registry/v4",
            ],
            env=env,
        ),
        run(
            "systematic V3 compiler",
            [
                sys.executable,
                "-m",
                "kc144_crystal",
                "systematic",
                "--output",
                "registry/v3",
            ],
            env=env,
        ),
        run(
            "whole test suite",
            [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
            env=env,
        ),
        run(
            "complete crystal audit",
            [sys.executable, "-m", "kc144_crystal", "audit"],
            env=env,
        ),
        run(
            "upstream 74-fact lattice",
            [sys.executable, "evidence/canonical/lattice_reference.py"],
            env=env,
        ),
        run(
            "GID082 canonicalization",
            [sys.executable, "canon.py"],
            ROOT / "evidence/executed/GID082",
            env={**env, "PYTHONPATH": f"{ROOT / 'evidence/executed/GID082'}:{ROOT / 'evidence/executed/GID090'}"},
        ),
        run(
            "GID082 answerability",
            [sys.executable, "answerable.py"],
            ROOT / "evidence/executed/GID082",
            env=env,
        ),
        run(
            "GID082 ablation",
            [sys.executable, "ablation.py"],
            ROOT / "evidence/executed/GID082",
            env={**env, "PYTHONPATH": f"{ROOT / 'evidence/executed/GID082'}:{ROOT / 'evidence/executed/GID090'}"},
        ),
        run(
            "GID090 promotion kernel",
            [sys.executable, "run.py"],
            ROOT / "evidence/executed/GID090",
            env=env,
        ),
        run(
            "GID051 RA13 signed handoff",
            [
                sys.executable,
                "verify_handoff.py",
                "gid051_f08_ra13_manifest.json",
                "gid051_f08_ra13_manifest.sig",
                "test_signing_public.pem",
                "gid051_f08_ra12_payload.json",
                "decoder_a.py",
                "decoder_b.js",
            ],
            ROOT / "evidence/executed/GID051_RA13",
            env=env,
        ),
    ]
    passed = sum(run_result["exit_code"] == 0 for run_result in runs)
    report = {
        "schema": "KC144.VerificationMatrix.P45",
        "verdict": "PASS" if passed == len(runs) else "FAIL",
        "passed": passed,
        "total": len(runs),
        "runs": runs,
    }
    (ROOT / "registry" / "verification.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({k: v for k, v in report.items() if k != "runs"}, indent=2))
    for result in runs:
        print(f"[{'PASS' if result['exit_code'] == 0 else 'FAIL'}] {result['label']}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
