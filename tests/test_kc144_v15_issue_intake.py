from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).parents[1] / "tools" / "kc144_v15_issue_intake.py"
SPEC = importlib.util.spec_from_file_location("kc144_v15_issue_intake", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def application() -> dict:
    return {
        "schema": MODULE.SCHEMA,
        "application_id": "V15-APPLICATION::TEST",
        "nomination_envelope": {
            "schema": "KC144.SignedCandidateNomination.V14",
            "signature_b64": "x" * 88,
        },
        "batch_id": MODULE.BATCH_ID,
        "batch_root": MODULE.BATCH_ROOT,
        "call_manifest_root": MODULE.CALL_MANIFEST_ROOT,
        "target_calls": [
            {
                "role": "CUSTODIAN",
                "call_id": "V14-CALL::CUSTODIAN::8abe29b03d1dea61",
                "call_digest": (
                    "sha256:"
                    "f2744aec6d1e87540d1e95390b933b08e68dfc5c55a85bb1f84a35e70110f77a"
                ),
            }
        ],
        "submitted_at": "2026-07-27T12:00:00+00:00",
        "signature_domain": "KC144.V15.BATCH_BOUND_CANDIDATE_APPLICATION",
        "signature_b64": "x" * 88,
    }


def event(value: dict | None = None) -> dict:
    payload = value or application()
    body = f"""### Target role
CUSTODIAN

### Immutable payload digest
{MODULE.ROLE_PAYLOAD_DIGESTS["CUSTODIAN"]}

### Application identifier
V15-APPLICATION::TEST

### Signed V15 application JSON
```json
{json.dumps(payload)}
```

### Public evidence locators
https://example.test/evidence sha256:abc

### Submission declarations
- [x] public only
"""
    return {
        "action": "opened",
        "issue": {
            "number": 144,
            "title": f"{MODULE.TITLE_PREFIX} test",
            "body": body,
            "html_url": "https://github.com/demeet2k/guild-hall/issues/144",
            "created_at": "2026-07-27T12:00:00Z",
            "updated_at": "2026-07-27T12:00:00Z",
        },
        "repository": {"full_name": "demeet2k/guild-hall"},
        "sender": {"login": "candidate"},
    }


class ExtractionTests(unittest.TestCase):
    def test_extracts_and_binds_public_application(self) -> None:
        extracted, context = MODULE.extract_event(event())
        self.assertEqual(extracted["application_id"], "V15-APPLICATION::TEST")
        self.assertEqual(context["claimed_role"], "CUSTODIAN")
        self.assertTrue(context["application_sha256"].startswith("sha256:"))
        self.assertFalse(context["private_material_detected"])

    def test_wrong_payload_digest_fails_closed(self) -> None:
        candidate = event()
        candidate["issue"]["body"] = candidate["issue"]["body"].replace(
            MODULE.ROLE_PAYLOAD_DIGESTS["CUSTODIAN"], "sha256:" + "0" * 64
        )
        with self.assertRaises(MODULE.IntakeError):
            MODULE.extract_event(candidate)

    def test_secret_key_field_fails_closed(self) -> None:
        candidate_application = application()
        candidate_application["private_key_b64"] = "forbidden"
        with self.assertRaises(MODULE.IntakeError):
            MODULE.extract_event(event(candidate_application))

    def test_selected_role_must_be_targeted(self) -> None:
        candidate_application = application()
        candidate_application["target_calls"][0]["role"] = "RETURN_AUDITOR"
        with self.assertRaises(MODULE.IntakeError):
            MODULE.extract_event(event(candidate_application))


class ReceiptTests(unittest.TestCase):
    def test_pass_is_non_promotive(self) -> None:
        _, context = MODULE.extract_event(event())
        report = {
            "verdict": "PASS",
            "checks": {"outer_signature_valid": True},
            "verification_digest": "sha256:" + "1" * 64,
        }
        receipt = MODULE.receipt_from_report(context, report, 0, None)
        self.assertEqual(
            receipt["intake_state"],
            "CRYPTOGRAPHIC_TRANSPORT_PASS_EXTERNAL_EVIDENCE_PENDING",
        )
        self.assertFalse(receipt["governance_authority_granted"])
        self.assertFalse(receipt["cohort_selected"])
        self.assertEqual(receipt["truth_effect"], "NONE")

    def test_missing_report_is_hold(self) -> None:
        _, context = MODULE.extract_event(event())
        receipt = MODULE.receipt_from_report(
            context, None, 1, "sha256:" + "2" * 64
        )
        self.assertEqual(receipt["transport_verdict"], "HOLD")
        self.assertEqual(receipt["intake_state"], "HOLD")


if __name__ == "__main__":
    unittest.main()
