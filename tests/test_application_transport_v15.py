from __future__ import annotations

import base64
import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)

from kc144_crystal.application_v15 import (
    APPLICATION_SIGNATURE_DOMAIN,
    BatchBoundCandidateApplication,
    CandidateCallBinding,
    application_publication_manifest,
    application_publication_manifest_integrity,
    application_publication_payload,
    application_publication_payload_integrity,
    application_receipt_ledger,
    application_signing_bytes,
    public_application_receipt_ledger,
    verify_batch_bound_application,
)
from kc144_crystal.ceremony_v10 import ROLES
from kc144_crystal.dispatch_v11 import (
    issue_governance_challenge_batch,
)
from kc144_crystal.nomination_v14 import (
    SIGNATURE_DOMAIN,
    SignedCandidateNomination,
    nomination_call_manifest,
    nomination_role_call,
    nomination_signing_bytes,
)
from kc144_crystal.population import digest
from kc144_crystal.selection_v13 import CandidateNomination
from kc144_crystal.v11 import compile_governance_dispatch_runtime
from kc144_crystal.v15 import compile_application_transport_runtime


CHECKED = "2026-07-27T12:00:00+00:00"
ISSUED = "2026-07-27T08:39:35+00:00"
EXPIRES = "2026-08-26T08:39:35+00:00"


def batch_fixture(index: int = 1) -> dict:
    return issue_governance_challenge_batch(
        authority_registry_digest=digest(("V15 authority", index)),
        handoff_bundle_root=digest(("V15 handoff", index)),
        issued_at=ISSUED,
        expires_at=EXPIRES,
    )


def call_context(batch: dict) -> tuple[list[dict], dict]:
    calls = [nomination_role_call(batch, role) for role in ROLES]
    return calls, nomination_call_manifest(batch, calls)


def signed_application(
    index: int,
    roles: tuple[str, ...],
    batch: dict,
    calls: list[dict],
    manifest: dict,
    *,
    target_roles: tuple[str, ...] | None = None,
    call_digest_override: str | None = None,
) -> BatchBoundCandidateApplication:
    private = Ed25519PrivateKey.generate()
    public = base64.b64encode(
        private.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw)
    ).decode("ascii")
    nomination = CandidateNomination(
        nomination_id=f"V15-NOMINATION-{index}",
        candidate_id=f"V15-CANDIDATE-{index}",
        status="NOMINATED",
        test_only=False,
        algorithm="ED25519",
        public_key_b64=public,
        eligible_roles=roles,
        identity_claim_root=digest(("identity", index)),
        external_identity_verification_root=digest(
            ("external-identity", index)
        ),
        external_independence_verification_root=digest(
            ("external-independence", index)
        ),
        institution_root=digest(("institution", index)),
        lineage_root=digest(("lineage", index)),
        jurisdiction_root=digest(("jurisdiction", index)),
        primary_domain_root=digest(("domain", index)),
        authority_root=digest(("authority", index)),
        funding_root=digest(("funding", index)),
        data_control_root=digest(("data", index)),
        staff_control_root=digest(("staff", index)),
        technology_control_root=digest(("technology", index)),
        conflict_disclosure_root=digest(("conflict", index)),
        conflict_status="CLEAR",
        conflict_resolution_root=None,
        nomination_evidence_root=digest(("nomination", index)),
        not_before="2026-01-01T00:00:00+00:00",
        not_after="2027-01-01T00:00:00+00:00",
    )
    inner_unsigned = SignedCandidateNomination(
        envelope_id=f"V15-INNER-{index}",
        nomination=nomination,
        signature_domain=SIGNATURE_DOMAIN,
        signature_b64="",
    )
    inner = replace(
        inner_unsigned,
        signature_b64=base64.b64encode(
            private.sign(nomination_signing_bytes(inner_unsigned))
        ).decode("ascii"),
    )
    calls_by_role = {call["role"]: call for call in calls}
    effective_roles = target_roles if target_roles is not None else roles
    bindings = tuple(
        CandidateCallBinding(
            role=role,
            call_id=calls_by_role[role]["call_id"],
            call_digest=(
                call_digest_override
                if call_digest_override is not None
                else calls_by_role[role]["call_digest"]
            ),
        )
        for role in ROLES
        if role in set(effective_roles)
    )
    outer_unsigned = BatchBoundCandidateApplication(
        application_id=f"V15-APPLICATION-{index}",
        nomination_envelope=inner,
        batch_id=batch["batch_id"],
        batch_root=batch["batch_root"],
        call_manifest_root=manifest["manifest_root"],
        target_calls=bindings,
        submitted_at=CHECKED,
        signature_domain=APPLICATION_SIGNATURE_DOMAIN,
        signature_b64="",
    )
    return replace(
        outer_unsigned,
        signature_b64=base64.b64encode(
            private.sign(application_signing_bytes(outer_unsigned))
        ).decode("ascii"),
    )


def unique_applications(
    batch: dict,
    calls: list[dict],
    manifest: dict,
) -> tuple[BatchBoundCandidateApplication, ...]:
    return tuple(
        signed_application(
            index,
            (role,),
            batch,
            calls,
            manifest,
        )
        for index, role in enumerate(ROLES, start=1)
    )


class ApplicationVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = batch_fixture()
        self.calls, self.manifest = call_context(self.batch)

    def verify(
        self,
        application: BatchBoundCandidateApplication,
        batch: dict | None = None,
    ) -> dict:
        effective_batch = batch or self.batch
        calls, manifest = (
            (self.calls, self.manifest)
            if effective_batch is self.batch
            else call_context(effective_batch)
        )
        return verify_batch_bound_application(
            effective_batch,
            calls,
            manifest,
            application,
            checked_at=CHECKED,
        )

    def test_valid_double_signed_application_passes_without_authority(
        self,
    ) -> None:
        report = self.verify(
            signed_application(
                1,
                (ROLES[0],),
                self.batch,
                self.calls,
                self.manifest,
            )
        )
        self.assertEqual(report["verdict"], "PASS")
        self.assertTrue(report["checks"]["inner_v14_signature_valid"])
        self.assertTrue(
            report["checks"]["candidate_key_outer_signature_valid"]
        )
        self.assertFalse(report["publication_proven"])
        self.assertFalse(report["governance_authority_granted"])

    def test_cross_batch_replay_is_held(self) -> None:
        application = signed_application(
            1,
            (ROLES[0],),
            self.batch,
            self.calls,
            self.manifest,
        )
        report = self.verify(application, batch_fixture(2))
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["batch_root_exact"])
        self.assertFalse(report["cross_batch_replay_admitted"])

    def test_signed_wrong_call_digest_is_held(self) -> None:
        application = signed_application(
            1,
            (ROLES[0],),
            self.batch,
            self.calls,
            self.manifest,
            call_digest_override=digest("wrong call"),
        )
        report = self.verify(application)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["exact_call_bindings"])
        self.assertTrue(
            report["checks"]["candidate_key_outer_signature_valid"]
        )

    def test_target_roles_must_equal_eligible_roles(self) -> None:
        application = signed_application(
            1,
            (ROLES[0], ROLES[1]),
            self.batch,
            self.calls,
            self.manifest,
            target_roles=(ROLES[0],),
        )
        report = self.verify(application)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(report["checks"]["target_role_set_exact"])

    def test_post_signature_time_change_is_held(self) -> None:
        application = signed_application(
            1,
            (ROLES[0],),
            self.batch,
            self.calls,
            self.manifest,
        )
        tampered = replace(
            application,
            submitted_at="2026-07-28T12:00:00+00:00",
        )
        report = self.verify(tampered)
        self.assertEqual(report["verdict"], "HOLD")
        self.assertFalse(
            report["checks"]["candidate_key_outer_signature_valid"]
        )


class PublicationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = batch_fixture()
        self.calls, self.call_manifest = call_context(self.batch)
        self.payloads = [
            application_publication_payload(
                self.batch,
                call,
                self.call_manifest,
            )
            for call in self.calls
        ]

    def test_five_payloads_embed_exact_role_calls(self) -> None:
        self.assertEqual(
            [payload["role"] for payload in self.payloads],
            list(ROLES),
        )
        for call, payload in zip(self.calls, self.payloads):
            self.assertEqual(payload["call"], call)
            self.assertTrue(
                application_publication_payload_integrity(
                    self.batch,
                    call,
                    self.call_manifest,
                    payload,
                )
            )

    def test_payloads_do_not_claim_publication(self) -> None:
        for payload in self.payloads:
            self.assertEqual(
                payload["publication_state"],
                "READY_UNPUBLISHED",
            )
            self.assertIsNone(payload["external_locator_root"])
            self.assertIsNone(payload["publication_receipt_root"])
            self.assertFalse(payload["governance_authority_granted"])

    def test_payload_tampering_fails_integrity(self) -> None:
        tampered = json.loads(json.dumps(self.payloads[0]))
        tampered["audience"] = "substituted"
        self.assertFalse(
            application_publication_payload_integrity(
                self.batch,
                self.calls[0],
                self.call_manifest,
                tampered,
            )
        )

    def test_publication_manifest_is_integral_and_unpublished(
        self,
    ) -> None:
        manifest = application_publication_manifest(
            self.batch,
            self.call_manifest,
            self.calls,
            self.payloads,
        )
        self.assertTrue(
            application_publication_manifest_integrity(
                self.batch,
                self.call_manifest,
                self.calls,
                self.payloads,
                manifest,
            )
        )
        self.assertEqual(manifest["prepared_payload_count"], 5)
        self.assertEqual(manifest["published_payload_count"], 0)
        self.assertFalse(manifest["publication_claimed"])


class ApplicationLedgerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.batch = batch_fixture()
        self.calls, self.manifest = call_context(self.batch)

    def test_duplicate_application_is_preserved_noncounting(self) -> None:
        application = signed_application(
            1,
            (ROLES[0],),
            self.batch,
            self.calls,
            self.manifest,
        )
        ledger = public_application_receipt_ledger(
            application_receipt_ledger(
                self.batch,
                self.calls,
                self.manifest,
                (application, application),
                checked_at=CHECKED,
            )
        )
        self.assertEqual(ledger["application_count"], 2)
        self.assertEqual(ledger["admitted_application_count"], 0)
        self.assertEqual(ledger["held_application_count"], 2)
        self.assertEqual(
            ledger["duplicate_application_ids"],
            [application.application_id],
        )

    def test_invalid_outer_signature_is_not_released_to_v14(self) -> None:
        application = replace(
            signed_application(
                1,
                (ROLES[0],),
                self.batch,
                self.calls,
                self.manifest,
            ),
            signature_b64=base64.b64encode(b"x" * 64).decode("ascii"),
        )
        ledger = public_application_receipt_ledger(
            application_receipt_ledger(
                self.batch,
                self.calls,
                self.manifest,
                (application,),
                checked_at=CHECKED,
            )
        )
        self.assertEqual(ledger["admitted_application_count"], 0)
        self.assertEqual(
            ledger["receipts"][0]["status"],
            "PRESERVED_NONCOUNTING_APPLICATION",
        )


class V15RuntimeTests(unittest.TestCase):
    @staticmethod
    def runtime_context(
        temporary: str,
    ) -> tuple[dict, list[dict], dict]:
        compile_governance_dispatch_runtime(temporary)
        plan = json.loads(
            (
                Path(temporary)
                / "governance_dispatch_plan_v11.json"
            ).read_text(encoding="utf-8")
        )
        batch = issue_governance_challenge_batch(
            authority_registry_digest=plan[
                "authority_registry_digest"
            ],
            handoff_bundle_root=plan["handoff_bundle_root"],
            issued_at=ISSUED,
            expires_at=EXPIRES,
        )
        calls, manifest = call_context(batch)
        return batch, calls, manifest

    def test_all_v15_schemas_parse(self) -> None:
        root = Path(__file__).resolve().parents[1]
        paths = sorted(
            (root / "schemas" / "kc144").glob("*-v15.schema.json")
        )
        self.assertEqual(len(paths), 7)
        for path in paths:
            self.assertIsInstance(
                json.loads(path.read_text(encoding="utf-8")),
                dict,
            )

    def test_live_runtime_stops_before_external_publication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            batch, _, _ = self.runtime_context(temporary)
            release = compile_application_transport_runtime(
                temporary,
                challenge_batch=batch,
            )
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(
                release["prepared_publication_payloads"],
                5,
            )
            self.assertEqual(
                release["published_publication_payloads"],
                0,
            )
            self.assertEqual(release["application_count"], 0)
            self.assertEqual(release["assigned_packet_count"], 0)
            self.assertEqual(
                release["operational_status"],
                "FIVE_EXTERNAL_BATCH_BOUND_APPLICATIONS_REQUIRED",
            )

    def test_unique_applications_route_to_delivery_barrier(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            batch, calls, manifest = self.runtime_context(temporary)
            release = compile_application_transport_runtime(
                temporary,
                challenge_batch=batch,
                applications=unique_applications(
                    batch,
                    calls,
                    manifest,
                ),
                checked_at=CHECKED,
            )
            self.assertEqual(release["verdict"], "PASS")
            self.assertEqual(
                release["admitted_application_count"],
                5,
            )
            self.assertEqual(
                release["solution_status"],
                "UNIQUE_PROVISIONAL_COHORT",
            )
            self.assertEqual(release["assigned_packet_count"], 5)
            self.assertEqual(release["delivered_packet_count"], 0)
            self.assertEqual(
                release["operational_status"],
                "FIVE_PACKET_DELIVERIES_REQUIRED",
            )
            self.assertFalse(release["governance_activated"])


if __name__ == "__main__":
    unittest.main()
