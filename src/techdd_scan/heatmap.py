"""Turn scanner findings into a deal-team style RAG heatmap and 100-day plan.

The *scanner view* uses only what the tool reported: each finding is put in a
category by keyword rules (CLASSIFY_ORDER) and each category has a fixed rubric
severity. The tool itself does not emit a severity. The *ground-truth view*
(planted vs detected) is shown alongside so the reader can see blind spots.
"""
from __future__ import annotations

import re

from .matching import CATEGORY_PATTERNS

# Priority order used to put each finding in ONE category (first match wins),
# reusing the same keyword patterns as the scorer. Unmatched -> "other".
CLASSIFY_ORDER = [
    "insecure_deserialization", "sql_injection", "command_injection", "code_injection", "xss", "ssrf",
    "path_traversal", "open_redirect", "hardcoded_secret", "timing_attack", "weak_crypto",
    "sensitive_logging", "auth_bypass", "race_condition", "input_validation", "error_handling", "null_handling",
]

RUBRIC_SEVERITY = {
    "insecure_deserialization": "critical", "sql_injection": "critical", "command_injection": "critical",
    "code_injection": "high", "auth_bypass": "critical", "xss": "high", "ssrf": "high",
    "path_traversal": "high", "hardcoded_secret": "high", "weak_crypto": "high",
    "open_redirect": "medium", "timing_attack": "low", "sensitive_logging": "medium",
    "race_condition": "medium", "input_validation": "medium", "error_handling": "medium",
    "null_handling": "low", "other": "low",
}

DOMAINS = [
    ("Injection & code execution", ["sql_injection", "command_injection", "code_injection", "xss"]),
    ("Access control & authentication", ["auth_bypass", "open_redirect", "timing_attack"]),
    ("Secrets management", ["hardcoded_secret"]),
    ("Cryptography", ["weak_crypto"]),
    ("Untrusted input & data parsing", ["insecure_deserialization", "path_traversal", "ssrf", "input_validation"]),
    ("Data protection & logging", ["sensitive_logging"]),
    ("Reliability & correctness", ["race_condition", "null_handling", "error_handling"]),
    ("General code quality (unclassified)", ["other"]),
]

assert set(CATEGORY_PATTERNS) == set(CLASSIFY_ORDER)


# Strong, unambiguous signals checked before the ordered patterns.
STRONG_SIGNALS = [
    ("insecure_deserialization", r"pickle|yaml\.load|deserial"),
    ("code_injection", r"\beval\b"),
    ("command_injection", r"shell=true|command injection"),
    ("sql_injection", r"sql injection"),
    ("ssrf", r"\bssrf\b|server[- ]side request"),
    ("path_traversal", r"path traversal"),
]


def classify(text: str) -> str:
    t = text.lower()
    for cat, pat in STRONG_SIGNALS:
        if re.search(pat, t):
            return cat
    for cat in CLASSIFY_ORDER:
        if any(re.search(p, t) for p in CATEGORY_PATTERNS[cat]):
            return cat
    return "other"


def rag_for(categories: list[str]) -> str:
    if not categories:
        return "GREEN"
    sev = {RUBRIC_SEVERITY[c] for c in categories}
    return "RED" if sev & {"critical", "high"} else "AMBER"


def build_heatmap(scored: dict, planted_by_cat: dict) -> list[dict]:
    rows = []
    cats = [classify(f["content"]) for f in scored["findings"]]
    for name, dcats in DOMAINS:
        in_dom = [c for c in cats if c in dcats]
        planted = sum(planted_by_cat.get(c, {}).get("planted", 0) for c in dcats)
        detected = sum(planted_by_cat.get(c, {}).get("detected", 0) for c in dcats)
        rag = "n/a" if name.startswith("General") else rag_for(in_dom)
        rows.append({"domain": name, "scanner_findings": len(in_dom), "rag": rag,
                     "planted": planted, "detected": detected})
    return rows


PHASES = [("Days 0-30", {"critical", "high"}), ("Days 31-60", {"medium"}), ("Days 61-100", {"low"})]


ACTIONS = {
    "sql_injection": "Replace string-built SQL with parameterised queries; allowlist ORDER BY columns.",
    "command_injection": "Remove shell=True; pass argument lists and validate names against an allowlist.",
    "code_injection": "Remove eval(); parse server data with JSON.parse.",
    "xss": "Escape output server-side; use textContent / DOM APIs instead of innerHTML.",
    "auth_bypass": "Remove debug admin header; enforce tenant scoping on every object lookup; reject unsigned JWTs.",
    "open_redirect": "Validate redirect targets against an allowlist of hosts/paths.",
    "timing_attack": "Use constant-time comparison (hmac.compare_digest) for secrets.",
    "hardcoded_secret": "Move secrets to a secret manager; remove defaults; rotate anything that was ever committed.",
    "weak_crypto": "Use a password KDF (argon2/bcrypt), the secrets module for tokens, and AES-GCM with a dedicated key.",
    "insecure_deserialization": "Replace pickle with signed JSON; use yaml.safe_load.",
    "path_traversal": "Resolve and confine file paths to the export directory (or use opaque file IDs).",
    "ssrf": "Restrict outbound webhook targets (https, public IPs only, pinned resolution, no redirects).",
    "input_validation": "Validate amounts and bounds server-side (non-negative, <= amount paid).",
    "sensitive_logging": "Stop logging passwords and card numbers; mask PAN; purge existing logs.",
    "race_condition": "Make balance updates atomic (single UPDATE with condition / row lock); guard shared counters.",
    "error_handling": "Fail closed on gateway errors; log and surface failures.",
    "null_handling": "Handle missing records explicitly (404/validation) instead of crashing.",
}


def remediation_items(scored: dict) -> list[dict]:
    """One item per category, built only from the scanner's own findings.

    ``ground_truth`` counts show how many of the underlying findings were
    confirmed against the planted manifest, so a reader can see which items a
    real engagement would still need to triage.
    """
    groups: dict[str, dict] = {}
    for f in scored["findings"]:
        cat = classify(f["content"])
        if cat == "other":
            continue
        g = groups.setdefault(cat, {"category": cat, "severity": RUBRIC_SEVERITY[cat], "locations": [],
                                    "ground_truth": {}, "example": ""})
        g["locations"].append(f"{f['path']}:{f['start_line']}")
        g["ground_truth"][f["status"]] = g["ground_truth"].get(f["status"], 0) + 1
        if not g["example"] and f["status"] == "true_positive":
            g["example"] = f["content"].strip().splitlines()[0][:200]
    for g in groups.values():
        if not g["example"]:
            g["example"] = "(no finding in this category matched a planted issue; triage required)"
        g["locations"] = sorted(set(g["locations"]))
        g["action"] = ACTIONS[g["category"]]
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    items = sorted(groups.values(), key=lambda i: (order[i["severity"]], -len(i["locations"]), i["category"]))
    for i in items:
        i["phase"] = next(p for p, s in PHASES if i["severity"] in s)
    return items


def quality_backlog_count(scored: dict) -> int:
    return sum(1 for f in scored["findings"] if classify(f["content"]) == "other")
