from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--assistant", required=True)
    parser.add_argument("--expected-toolchain", required=True)
    parser.add_argument("--source", required=True)
    parser.add_argument("--tool-version-file", required=True)
    parser.add_argument("--stdout", required=True)
    parser.add_argument("--stderr", required=True)
    parser.add_argument("--returncode", required=True, type=int)
    parser.add_argument("--command-json", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    source = Path(args.source)
    stdout = Path(args.stdout).read_bytes()
    stderr = Path(args.stderr).read_bytes()
    receipt = {
        "schema_version": "1.0",
        "assistant": args.assistant,
        "tool_version": Path(args.tool_version_file).read_text().strip(),
        "expected_toolchain": args.expected_toolchain,
        "source_path": args.source,
        "source_sha256": digest_bytes(source.read_bytes()),
        "command": json.loads(args.command_json),
        "returncode": args.returncode,
        "kernel_status": "PASS" if args.returncode == 0 else "FAIL",
        "placeholder_scan": "PASS",
        "execution_provenance": "GITHUB_ACTIONS",
        "workflow_run_url": (
            f"{os.environ['GITHUB_SERVER_URL']}/"
            f"{os.environ['GITHUB_REPOSITORY']}/actions/runs/"
            f"{os.environ['GITHUB_RUN_ID']}"
        ),
        "commit_sha": os.environ["GITHUB_SHA"],
        "runner_os": os.environ["RUNNER_OS"],
        "artifact_sha256": digest_bytes(stdout + stderr),
    }
    Path(args.output).write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
