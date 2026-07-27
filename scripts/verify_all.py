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
        "schema": "KC144.VerificationMatrix.V15",
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
