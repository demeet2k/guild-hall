#!/usr/bin/env python3
import hashlib
import json
import pathlib
import re
import subprocess
import sys


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(command):
    return subprocess.run(command, check=False, capture_output=True, text=True)


def main():
    if len(sys.argv) != 7:
        print(
            "USAGE::verify_handoff.py MANIFEST SIGNATURE PUBLIC_KEY "
            "PAYLOAD DECODER_A DECODER_B"
        )
        return 64

    manifest_path, signature, public_key, payload, decoder_a, decoder_b = (
        pathlib.Path(value) for value in sys.argv[1:]
    )
    signature_result = run([
        "openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(public_key),
        "-rawin", "-in", str(manifest_path), "-sigfile", str(signature),
    ])
    if signature_result.returncode != 0:
        print("HANDOFF::BLOCK::MANIFEST_SIGNATURE_INVALID")
        return 2

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected_payload = manifest["subjectCID"].removeprefix("sha256:")
    observed_payload = sha256(payload)
    if expected_payload != observed_payload:
        print(
            "HANDOFF::BLOCK::PAYLOAD_DIGEST_MISMATCH "
            f"EXPECTED::{expected_payload} OBSERVED::{observed_payload}"
        )
        return 3

    result_a = run([sys.executable, str(decoder_a), str(payload), expected_payload])
    result_b = run(["node", str(decoder_b), str(payload), expected_payload])
    if result_a.returncode != 0 or result_b.returncode != 0:
        print("HANDOFF::BLOCK::REFERENCE_DECODER_FAILURE")
        print(result_a.stdout.strip())
        print(result_b.stdout.strip())
        return 4

    pattern = re.compile(r"PROJECTION::([0-9a-f]{64})")
    projection_a = pattern.search(result_a.stdout)
    projection_b = pattern.search(result_b.stdout)
    expected_projection = manifest["semanticProjection"].removeprefix("sha256:")
    if not projection_a or not projection_b:
        print("HANDOFF::BLOCK::PROJECTION_RECEIPT_MISSING")
        return 5
    if not (
        projection_a.group(1)
        == projection_b.group(1)
        == expected_projection
    ):
        print("HANDOFF::BLOCK::SEMANTIC_PROJECTION_MISMATCH")
        return 6

    print(
        "HANDOFF::PASS "
        f"MANIFEST::{sha256(manifest_path)} "
        f"PAYLOAD::{observed_payload} "
        f"PROJECTION::{expected_projection}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
