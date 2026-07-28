#!/usr/bin/env python3
"""Safe public-issue ingress for KC144 V15 batch-bound applications.

This adapter performs only transport-layer work:

* parse a GitHub issue-form body;
* reject obvious secret-bearing fields;
* bind the claimed role to the immutable V15 payload digest;
* emit the candidate JSON for the canonical KC144 verifier; and
* wrap the verifier result in a deterministic, non-promotive receipt.

It does not verify identity or independence, select a cohort, grant authority,
or mutate the frozen V15 crystal.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Iterable, Mapping


SCHEMA = "KC144.BatchBoundCandidateApplication.V15"
TITLE_PREFIX = "[KC144 V15 APPLICATION]"
BASE_COMMIT = "1b653e39d7c09ba8b93a800860244242cd98d397"
BASE_TREE = "d2e2f9b92fafdfd17be5088a4a8e6e3a5db1322b"
BATCH_ID = "V11-BATCH::c7e3ae7e8cfd126a75b41b4a"
BATCH_ROOT = (
    "sha256:"
    "b9322c5950d562f7a3f437ed8c939d98506db4edf34446e8332318513bca46b5"
)
CALL_MANIFEST_ROOT = (
    "sha256:"
    "fc82581375a195d09a58b7769eb33bba719c7f7e4b7ddd7b5276dcf1ce1d6219"
)

ROLE_PAYLOAD_DIGESTS = {
    "CUSTODIAN": (
        "sha256:"
        "3714c4cc058ec345b33d4cbdb38741d10ad9520937dab8396670135fc7b74a3b"
    ),
    "INDEPENDENT_REVIEWER": (
        "sha256:"
        "3c8292b222bd4475e36554dc7f64b0988ee529be061690dd63e6374f79625f10"
    ),
    "REPLAY_WITNESS": (
        "sha256:"
        "ac3ec296c8479514a5a51eeba546216f036288843d20ac92ff004e14d1bc60ee"
    ),
    "SOURCE_AUDITOR": (
        "sha256:"
        "502d009c9347dc357ad672077013a0adb3e64bfc2590fb5d3828358b80b53d20"
    ),
    "RETURN_AUDITOR": (
        "sha256:"
        "378340758cbd0ff5dd7f6498a5552d5c80fc7228e1caa8d870e28aab6096769b"
    ),
}

SECRET_KEYS = {
    "access_token",
    "api_key",
    "mnemonic",
    "password",
    "private_key",
    "private_key_b64",
    "recovery_phrase",
    "secret",
    "seed_phrase",
}


class IntakeError(ValueError):
    """A fail-closed transport parsing error."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def sha256_prefixed(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def issue_form_sections(body: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^### (?P<label>[^\r\n]+)\r?\n", body))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(body)
        sections[match.group("label").strip()] = body[start:end].strip()
    return sections


def required_section(sections: Mapping[str, str], label: str) -> str:
    value = sections.get(label, "").strip()
    if not value or value == "_No response_":
        raise IntakeError(f"missing required issue-form section: {label}")
    return value


def extract_json_block(value: str) -> dict[str, Any]:
    fenced = re.search(
        r"```(?:json)?\s*(?P<json>\{.*\})\s*```",
        value,
        flags=re.DOTALL | re.IGNORECASE,
    )
    payload = fenced.group("json") if fenced else value
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise IntakeError("application JSON must be one object")
    return parsed


def iter_keys(value: Any) -> Iterable[str]:
    if isinstance(value, Mapping):
        for key, nested in value.items():
            yield str(key)
            yield from iter_keys(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from iter_keys(nested)


def secret_key_hits(application: Mapping[str, Any]) -> list[str]:
    return sorted(
        {
            key
            for key in iter_keys(application)
            if key.casefold().replace("-", "_") in SECRET_KEYS
        }
    )


def target_roles(application: Mapping[str, Any]) -> list[str]:
    bindings = application.get("target_calls")
    if not isinstance(bindings, list):
        raise IntakeError("target_calls must be an array")
    roles: list[str] = []
    for binding in bindings:
        if not isinstance(binding, Mapping) or not isinstance(binding.get("role"), str):
            raise IntakeError("every target_calls entry must contain a role")
        roles.append(str(binding["role"]))
    return roles


def extract_event(event: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    issue = event.get("issue")
    repository = event.get("repository")
    sender = event.get("sender")
    if not isinstance(issue, Mapping) or not isinstance(repository, Mapping):
        raise IntakeError("event must contain issue and repository objects")

    title = str(issue.get("title", ""))
    if not title.startswith(TITLE_PREFIX):
        raise IntakeError(f"issue title must start with {TITLE_PREFIX}")

    sections = issue_form_sections(str(issue.get("body", "")))
    role = required_section(sections, "Target role").splitlines()[0].strip()
    payload_digest = required_section(
        sections, "Immutable payload digest"
    ).splitlines()[0].strip()
    claimed_application_id = required_section(
        sections, "Application identifier"
    ).splitlines()[0].strip()
    application = extract_json_block(
        required_section(sections, "Signed V15 application JSON")
    )

    if role not in ROLE_PAYLOAD_DIGESTS:
        raise IntakeError(f"unknown target role: {role}")
    if payload_digest != ROLE_PAYLOAD_DIGESTS[role]:
        raise IntakeError("payload digest does not match the immutable role payload")
    if application.get("schema") != SCHEMA:
        raise IntakeError(f"application schema must be {SCHEMA}")
    if application.get("application_id") != claimed_application_id:
        raise IntakeError("form application identifier does not match application JSON")
    if application.get("batch_id") != BATCH_ID:
        raise IntakeError("application batch_id does not match the active immutable batch")
    if application.get("batch_root") != BATCH_ROOT:
        raise IntakeError("application batch_root does not match the active immutable batch")
    if application.get("call_manifest_root") != CALL_MANIFEST_ROOT:
        raise IntakeError(
            "application call_manifest_root does not match the immutable manifest"
        )
    roles = target_roles(application)
    if role not in roles:
        raise IntakeError("selected role is absent from application target_calls")
    hits = secret_key_hits(application)
    if hits:
        raise IntakeError(
            "secret-bearing JSON keys are forbidden: " + ", ".join(hits)
        )

    application_bytes = canonical_json(application).encode("utf-8")
    issue_number = int(issue["number"])
    issue_url = str(issue.get("html_url", ""))
    repo_name = str(repository.get("full_name", ""))
    actor = str(sender.get("login", "")) if isinstance(sender, Mapping) else ""
    observed_at = str(issue.get("updated_at") or issue.get("created_at") or "")
    context = {
        "schema": "KC144.PublicIssueApplicationContext.V1",
        "repository": repo_name,
        "issue_number": issue_number,
        "issue_url": issue_url,
        "event_action": str(event.get("action", "")),
        "actor": actor,
        "observed_at": observed_at,
        "checked_at": observed_at,
        "claimed_role": role,
        "claimed_payload_digest": payload_digest,
        "application_id": claimed_application_id,
        "application_sha256": sha256_prefixed(application_bytes),
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "batch_id": BATCH_ID,
        "batch_root": BATCH_ROOT,
        "call_manifest_root": CALL_MANIFEST_ROOT,
        "evidence_locators_present": bool(
            required_section(sections, "Public evidence locators")
        ),
        "private_material_detected": False,
        "truth_effect": "NONE",
        "governance_authority_granted": False,
    }
    context["context_digest"] = sha256_prefixed(
        canonical_json(context).encode("utf-8")
    )
    return application, context


def receipt_from_report(
    context: Mapping[str, Any],
    report: Mapping[str, Any] | None,
    verifier_exit: int,
    stderr_digest: str | None,
) -> dict[str, Any]:
    transport_verdict = (
        str(report.get("verdict", "HOLD")) if isinstance(report, Mapping) else "HOLD"
    )
    verifier_pass = verifier_exit == 0 and transport_verdict == "PASS"
    body = {
        "schema": "KC144.PublicApplicationIntakeReceipt.V1",
        "transport_id": "KC144.CANDIDATE.APPLICATION.TRANSPORT.V15",
        "repository": context.get("repository"),
        "issue_number": context.get("issue_number"),
        "issue_url": context.get("issue_url"),
        "observed_at": context.get("observed_at"),
        "application_id": context.get("application_id"),
        "application_sha256": context.get("application_sha256"),
        "claimed_role": context.get("claimed_role"),
        "claimed_payload_digest": context.get("claimed_payload_digest"),
        "base_commit": BASE_COMMIT,
        "base_tree": BASE_TREE,
        "batch_id": BATCH_ID,
        "batch_root": BATCH_ROOT,
        "call_manifest_root": CALL_MANIFEST_ROOT,
        "verifier_exit": verifier_exit,
        "transport_verdict": transport_verdict,
        "transport_checks": (
            dict(report.get("checks", {})) if isinstance(report, Mapping) else {}
        ),
        "transport_verification_digest": (
            report.get("verification_digest")
            if isinstance(report, Mapping)
            else None
        ),
        "intake_state": (
            "CRYPTOGRAPHIC_TRANSPORT_PASS_EXTERNAL_EVIDENCE_PENDING"
            if verifier_pass
            else "HOLD"
        ),
        "stderr_digest": stderr_digest,
        "identity_independence_externally_proven": False,
        "cohort_selected": False,
        "packet_assigned": False,
        "governance_authority_granted": False,
        "production_certificate_issued": False,
        "truth_effect": "NONE",
        "frozen_crystal_mutated": False,
        "return_address": "KC144.V1::GID144::M12",
    }
    receipt_digest = sha256_prefixed(canonical_json(body).encode("utf-8"))
    return {
        **body,
        "receipt_id": f"KC144.V15.ISSUE.{context.get('issue_number')}::{receipt_digest[7:31]}",
        "receipt_digest": receipt_digest,
    }


def command_extract(args: argparse.Namespace) -> int:
    event = read_json(args.event)
    application, context = extract_event(event)
    write_json(args.application, application)
    write_json(args.context, context)
    return 0


def command_receipt(args: argparse.Namespace) -> int:
    context = read_json(args.context)
    report: Mapping[str, Any] | None = None
    if args.report.is_file() and args.report.stat().st_size:
        try:
            candidate = read_json(args.report)
            if isinstance(candidate, Mapping):
                report = candidate
        except (json.JSONDecodeError, OSError):
            report = None
    stderr_digest = None
    if args.stderr.is_file() and args.stderr.stat().st_size:
        stderr_digest = sha256_prefixed(args.stderr.read_bytes())
    receipt = receipt_from_report(
        context,
        report,
        verifier_exit=args.verifier_exit,
        stderr_digest=stderr_digest,
    )
    write_json(args.output, receipt)
    return 0 if receipt["transport_verdict"] == "PASS" else 2


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser()
    commands = value.add_subparsers(dest="command", required=True)

    extract = commands.add_parser("extract")
    extract.add_argument("--event", type=Path, required=True)
    extract.add_argument("--application", type=Path, required=True)
    extract.add_argument("--context", type=Path, required=True)
    extract.set_defaults(handler=command_extract)

    receipt = commands.add_parser("receipt")
    receipt.add_argument("--context", type=Path, required=True)
    receipt.add_argument("--report", type=Path, required=True)
    receipt.add_argument("--stderr", type=Path, required=True)
    receipt.add_argument("--verifier-exit", type=int, required=True)
    receipt.add_argument("--output", type=Path, required=True)
    receipt.set_defaults(handler=command_receipt)
    return value


def main() -> int:
    args = parser().parse_args()
    try:
        return int(args.handler(args))
    except (IntakeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as error:
        raise SystemExit(f"KC144 V15 intake HOLD: {error}") from error


if __name__ == "__main__":
    raise SystemExit(main())
