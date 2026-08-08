from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Iterable

SCHEMA_VERSION = "CapabilityIR.V0"
COMPILER = "guild-hall.capability-ir"
COMPILER_VERSION = "0.1.0"
EXTRACTION_LAW = "LEXICAL_EXTRACTION_WITH_EXPLICIT_UNRESOLVED_FALLBACK"

VERBS = (
    "analyze", "attack", "automate", "build", "calculate", "classify", "compare",
    "compile", "compress", "convert", "create", "design", "deserialize", "detect",
    "deploy", "explain", "extract", "factor", "generate", "hybridize", "implement",
    "integrate", "map", "measure", "monitor", "navigate", "optimize", "parse", "plan",
    "predict", "query", "rank", "recommend", "reconstruct", "reseed", "retrieve",
    "route", "schedule", "search", "serialize", "simulate", "store", "summarize",
    "synthesize", "test", "train", "transform", "validate", "verify", "visualize", "witness"
)

DOMAIN_KEYWORDS = {
    "software": ("api", "code", "compiler", "deploy", "software", "repository", "git"),
    "data": ("data", "database", "csv", "json", "dataset", "dashboard", "query"),
    "biology": ("biology", "cell", "gene", "microscopy", "protein", "patient"),
    "finance": ("budget", "finance", "spend", "revenue", "cash", "portfolio"),
    "robotics": ("robot", "obstacle", "actuator", "sensor", "path planner"),
    "physics": ("physics", "orbital", "trajectory", "energy", "particle", "simulation"),
}

MYTHIC_MARKERS = (
    "all knowing", "best possible", "everything", "forever", "instant", "instantly",
    "omniscient", "perfect", "universal", "without limit"
)

CONSTRAINT_LIMIT_RE = re.compile(
    r"\b(under|within|at\s+most|at\s+least|less\s+than|more\s+than|no\s+more\s+than)\b",
    re.IGNORECASE,
)
CONSTRAINT_PROHIBITION_RE = re.compile(
    r"\b(must\s+not|without|never|do\s+not|cannot|can't)\b", re.IGNORECASE
)
CONSTRAINT_REQUIREMENT_RE = re.compile(
    r"\b(must|should|required|requires|only)\b", re.IGNORECASE
)
TEST_RE = re.compile(
    r"\b(test|tests|verify|validate|accuracy|benchmark|held[- ]out|prove|measure|conservation|pass)\b",
    re.IGNORECASE,
)
RISK_RE = re.compile(
    r"\b(avoid|prevent|risk|unsafe|safe|privacy|security|expos(?:e|ing)|harm|failure)\b",
    re.IGNORECASE,
)
RESOURCE_RE = re.compile(r"\b(using|via|with)\s+(.+)$", re.IGNORECASE)
MUST_RE = re.compile(r"\bmust\s+(not\s+)?(.+)$", re.IGNORECASE)


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def _clauses(text: str) -> list[str]:
    parts = re.split(r"[.;\n]+|\bthen\b", text, flags=re.IGNORECASE)
    return [p.strip(" ,") for p in parts if p.strip(" ,")]


def _dedupe(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _domain_hint(text: str) -> tuple[str, str]:
    lower = text.lower()
    scores = {
        domain: sum(1 for keyword in keywords if keyword in lower)
        for domain, keywords in DOMAIN_KEYWORDS.items()
    }
    best = max(scores, key=scores.get)
    if scores[best] == 0:
        return "general", "PARSED"
    return best, "HEURISTIC"


def _extract_capabilities(clauses: list[str]) -> tuple[list[dict], list[str]]:
    capabilities: list[dict] = []
    unknowns: list[str] = []
    seen: set[tuple[str, str]] = set()
    for clause in clauses:
        lower = clause.lower()
        matches = []
        for verb in VERBS:
            match = re.search(rf"\b{re.escape(verb)}(?:s|ed|ing)?\b", lower)
            if match:
                matches.append((match.start(), verb, match.end()))
        for _, verb, end in sorted(matches):
            obj = clause[end:].strip(" :-,.")
            obj = re.split(r"\b(?:and then|then)\b", obj, maxsplit=1, flags=re.IGNORECASE)[0].strip()
            if not obj:
                obj = "UNRESOLVED_OBJECT"
                unknowns.append(f"Object for capability verb '{verb}' is unresolved.")
            key = (verb, obj.lower())
            if key in seen:
                continue
            seen.add(key)
            capabilities.append({
                "verb": verb,
                "object": obj,
                "source_clause": clause,
                "standing": "LEXICALLY_EXTRACTED",
            })
    if not capabilities:
        capabilities.append({
            "verb": "clarify",
            "object": "UNRESOLVED_CAPABILITY_FROM_GOAL",
            "source_clause": clauses[0] if clauses else "UNRESOLVED",
            "standing": "FALLBACK_UNRESOLVED",
        })
        unknowns.append("Stable capability verb was not lexically recoverable from the goal.")
    return capabilities, unknowns


def _extract_constraints(clauses: list[str]) -> list[dict]:
    out: list[dict] = []
    for clause in clauses:
        if CONSTRAINT_PROHIBITION_RE.search(clause):
            kind = "PROHIBITION"
        elif CONSTRAINT_LIMIT_RE.search(clause):
            kind = "LIMIT"
        elif CONSTRAINT_REQUIREMENT_RE.search(clause):
            kind = "REQUIREMENT"
        else:
            continue
        out.append({"kind": kind, "text": clause, "source_clause": clause})
    return out


def _extract_resources(clauses: list[str]) -> list[dict]:
    out: list[dict] = []
    for clause in clauses:
        match = RESOURCE_RE.search(clause)
        if match:
            name = match.group(2).strip(" ,.")
            if name:
                out.append({"kind": "MENTIONED", "name": name, "source_clause": clause})
    return out


def _extract_contradictions(clauses: list[str]) -> list[str]:
    positive: dict[str, str] = {}
    negative: dict[str, str] = {}
    for clause in clauses:
        match = MUST_RE.search(clause)
        if not match:
            continue
        phrase = re.sub(r"\s+", " ", match.group(2).strip(" ,.").lower())
        phrase = re.split(r"\b(?:and|but)\b", phrase, maxsplit=1)[0].strip()
        if not phrase:
            continue
        if match.group(1):
            negative[phrase] = clause
        else:
            positive[phrase] = clause
    return [
        f"Contradiction: requirement and prohibition both target '{phrase}'."
        for phrase in sorted(set(positive) & set(negative))
    ]


def compile_capability_ir(goal_text: str) -> dict:
    goal = _normalize(goal_text)
    if len(goal) < 3:
        raise ValueError("goal_text must contain at least 3 non-whitespace characters")

    digest = hashlib.sha256(goal.encode("utf-8")).hexdigest()
    clauses = _clauses(goal)
    domain, domain_standing = _domain_hint(goal)
    capabilities, unknowns = _extract_capabilities(clauses)
    constraints = _extract_constraints(clauses)
    resources = _extract_resources(clauses)
    contradictions = _extract_contradictions(clauses)

    explicit_tests = [clause for clause in clauses if TEST_RE.search(clause)]
    success_tests = _dedupe(explicit_tests)
    if not success_tests:
        success_tests = [
            "At least one emitted capability is paired with an executable acceptance test or is explicitly unresolved."
        ]
        unknowns.append("The input did not provide an explicit success test; a compiler-level test obligation was inserted.")

    risks = _dedupe(clause for clause in clauses if RISK_RE.search(clause))
    for marker in MYTHIC_MARKERS:
        if marker in goal.lower():
            unknowns.append(
                f"Absolute/mythic term '{marker}' requires a bounded measurable definition before implementation standing can increase."
            )
    if not constraints:
        unknowns.append("No explicit constraint was detected in the input.")
    if not resources:
        unknowns.append("No explicit implementation resource was detected in the input.")
    unknowns.extend(contradictions)

    return {
        "schema_version": SCHEMA_VERSION,
        "goal_id": f"capir-{digest[:16]}",
        "goal_text": goal,
        "target": {"summary": goal, "domain_hint": domain, "standing": domain_standing},
        "capabilities": capabilities,
        "constraints": constraints,
        "success_tests": success_tests,
        "resources": resources,
        "risks": risks,
        "contradictions": contradictions,
        "unknowns": _dedupe(unknowns),
        "evidence": {"standing": "PARSED_NOT_OBSERVED", "observations": []},
        "provenance": {
            "compiler": COMPILER,
            "compiler_version": COMPILER_VERSION,
            "input_sha256": digest,
            "extraction_law": EXTRACTION_LAW,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile ambitious goal text into CapabilityIR.V0")
    parser.add_argument("goal")
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    ir = compile_capability_ir(args.goal)
    rendered = json.dumps(ir, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if args.out:
        args.out.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
