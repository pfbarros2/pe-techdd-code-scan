"""Deterministic matching of scanner findings to the ground-truth manifest.

Rules (documented in README "Scoring method"; rules_version 2):

1. Line resolution: each manifest entry lists one or more ``anchors``; every
   fixture line containing an anchor substring is a target line. A planted
   issue may also list ``related`` locations (other files on the same data
   flow, e.g. the route that feeds a vulnerable helper).
2. Location match (planted issue): finding path equals the issue's file (or a
   related file) AND some target line t in that file satisfies
   ``start_line - LINE_WINDOW <= t <= end_line + LINE_WINDOW``.
3. Category match: the finding's prose (``content`` only, lower-cased; the
   quoted code is ignored) matches at least one regex in CATEGORY_PATTERNS
   for the planted issue's category.
4. A finding that satisfies 2 and 3 for one or more planted issues is a
   true-positive finding and credits detection to every issue it matches.
   A true-positive finding that credits no new issue is a duplicate.
5. A finding with a location match but no category match is a "near miss"
   (counted as a false positive in strict precision, reported separately).
6. Any other finding is unmatched. If its range is within DECOY_WINDOW lines
   of a decoy target line AND its prose matches the decoy's ``lure``
   category (the vulnerability the safe code superficially resembles), it is
   a decoy false positive. Otherwise it is an "unplanted" finding (a false
   positive for strict precision; it may still be a legitimate observation,
   see results/run1-nemotron-ultra/manual_triage.json).
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

RULES_VERSION = 2
LINE_WINDOW = 3
DECOY_WINDOW = 2

_SENS = r"(password|card|\bpan\b|pii|credential|sensitive|plaintext|secret)"
_LOG = r"(\blog\b|\blogs\b|logged|logging|logger)"

CATEGORY_PATTERNS: dict[str, list[str]] = {
    "sql_injection": [r"sql injection", r"\bsql\b.{0,60}(inject|concatenat|interpolat|f-string|unsanitiz|untrusted|user[- ]controlled|user input)",
                      r"inject.{0,40}\bsql\b", r"order by.{0,80}(inject|user[- ]controlled|untrusted|user input)", r"parameteri[sz]ed (query|queries|statement)"],
    "xss": [r"\bxss\b", r"cross[- ]site scripting", r"innerhtml", r"(without|no|missing|not) (html[- ])?escap", r"unescaped",
            r"html injection", r"script injection"],
    "hardcoded_secret": [r"hard[- ]?coded", r"secrets? (in|into|committed to) (the )?(source|code|repo)", r"credentials? (in|embedded in) (the )?(source|code|connection string)",
                         r"default (signing )?(key|secret|password)", r"embedded (password|secret|credential)", r"fallback (key|secret)"],
    "auth_bypass": [r"bypass", r"backdoor", r"\bidor\b", r"insecure direct object", r"tenant (isolation|check|scop|ownership)", r"without tenant",
                    r"ownership", r"access control", r"privilege escalation", r"(without|no|skip\w*|disabl\w*) (any )?(signature|verification)",
                    r"alg.{0,12}none", r"unauthori[sz]ed access", r"forge"],
    "race_condition": [r"race", r"toctou", r"not thread[- ]safe", r"without (any |a )?(lock|synchroni)", r"atomic", r"double[- ]spend",
                       r"check[- ]then[- ]act", r"concurrent (withdraw|request|access|modif|increment|update)"],
    "null_handling": [r"(returns?|returning|is|be|being|of|or|to) `?none`?\b", r"nonetype", r"\bnull\b", r"undefined", r"typeerror",
                      r"attributeerror", r"optional chaining"],
    "insecure_deserialization": [r"deserial", r"unsafe (yaml|loader|load)", r"arbitrary (python )?(code|object)", r"remote code", r"\brce\b",
                                 r"code execution", r"safe_load"],
    "weak_crypto": [r"md5", r"sha-?1\b", r"\becb\b", r"weak (hash|crypto|cipher|random)", r"not cryptographically", r"insecure random",
                    r"cryptographically (secure|strong|weak)", r"predictab", r"\bprng\b", r"bcrypt", r"argon", r"pbkdf", r"scrypt", r"unsalted", r"\bsalt"],
    "input_validation": [r"validat", r"negative", r"upper bound", r"bounds", r"(excessive|exceed\w*|arbitrary) (amount|refund)"],
    "path_traversal": [r"travers", r"\.\./", r"(normali[sz]|sanitiz|restrict|canonical).{0,30}path", r"arbitrary file"],
    "command_injection": [r"command injection", r"shell injection", r"shell=true", r"arbitrary (shell )?command", r"os command"],
    "ssrf": [r"\bssrf\b", r"server[- ]side request", r"internal (network|service|address|host|endpoint)", r"metadata (service|endpoint)",
             r"private ip", r"arbitrary url"],
    "sensitive_logging": [_LOG + r".{0,80}" + _SENS, _SENS + r".{0,80}" + _LOG],
    "timing_attack": [r"timing", r"constant[- ]time", r"compare_digest"],
    "error_handling": [r"swallow", r"silent", r"except exception:\s*pass", r"(report|return|treat)\w*.{0,40}success", r"mask\w* (the )?(error|failure)",
                       r"bare except", r"catch\w* (all|too broad)"],
    "code_injection": [r"\beval\b", r"code injection", r"arbitrary (code|javascript)"],
    "open_redirect": [r"open redirect", r"unvalidated redirect", r"redirect.{0,60}(unvalidat|arbitrary|any url|attacker|malicious|external)"],
}

SEVERITIES = ["critical", "high", "medium", "low"]


@dataclass
class Target:
    id: str
    file: str
    lines: list[int]
    category: str | None = None
    severity: str | None = None
    description: str = ""
    extra: dict = field(default_factory=dict)  # related file -> target lines
    lure: str | None = None

    def lines_in(self, path: str) -> list[int]:
        if path == self.file:
            return self.lines
        return self.extra.get(path, [])


@dataclass
class Finding:
    idx: int
    path: str
    start_line: int
    end_line: int
    text: str
    content: str


@dataclass
class MatchResult:
    assignments: dict[int, list] = field(default_factory=dict)  # finding idx -> planted ids
    detected: dict[str, int] = field(default_factory=dict)  # planted id -> first finding idx
    duplicates: list[int] = field(default_factory=list)
    near_miss: dict[int, list[str]] = field(default_factory=dict)
    decoy_fp: dict[int, str] = field(default_factory=dict)
    unplanted: list[int] = field(default_factory=list)


def _anchor_lines(fixture_root: Path, file: str, anchors: list[str], ident: str) -> list[int]:
    lines = (fixture_root / file).read_text().splitlines()
    hits = sorted({i + 1 for a in anchors for i, l in enumerate(lines) if a in l})
    if not hits:
        raise ValueError(f"anchor not found for {ident} in {file}")
    return hits


def resolve_targets(manifest: dict, fixture_root: Path) -> tuple[list[Target], list[Target]]:
    planted = []
    for e in manifest["planted"]:
        extra = {r["file"]: _anchor_lines(fixture_root, r["file"], r["anchors"], e["id"]) for r in e.get("related", [])}
        planted.append(Target(e["id"], e["file"], _anchor_lines(fixture_root, e["file"], e["anchors"], e["id"]),
                              e["category"], e["severity"], e.get("description", ""), extra))
    decoys = [Target(e["id"], e["file"], _anchor_lines(fixture_root, e["file"], e["anchors"], e["id"]),
                     description=e.get("why_safe", ""), lure=e.get("lure"))
              for e in manifest["decoys"]]
    return planted, decoys


def normalise_path(path: str) -> str:
    p = path.replace("\\", "/").lstrip("./")
    marker = "quillmoor-ledger/"
    if marker in p:
        p = p.split(marker, 1)[1]
    return p


def load_findings(scan: dict) -> list[Finding]:
    out = []
    for i, c in enumerate(scan.get("comments", [])):
        start = int(c.get("start_line") or 0)
        end = int(c.get("end_line") or start)
        if end < start:
            start, end = end, start
        # Category matching uses the reviewer's prose only (not the quoted code),
        # so a comment cannot "match" just because the code it quotes contains a keyword.
        text = str(c.get("content") or "").lower()
        out.append(Finding(i, normalise_path(c.get("path", "")), start, end, text, c.get("content", "")))
    return out


def category_matches(category: str, text: str) -> bool:
    return any(re.search(p, text) for p in CATEGORY_PATTERNS[category])


def _distance(f: Finding, lines: list[int]) -> int:
    best = None
    for t in lines:
        d = 0 if f.start_line <= t <= f.end_line else min(abs(t - f.start_line), abs(t - f.end_line))
        best = d if best is None else min(best, d)
    return best if best is not None else 10**9


def match(findings: list[Finding], planted: list[Target], decoys: list[Target]) -> MatchResult:
    res = MatchResult()
    for f in findings:
        loc = [t for t in planted if _distance(f, t.lines_in(f.path)) <= LINE_WINDOW]
        cat = [t for t in loc if category_matches(t.category, f.text)]
        if cat:
            res.assignments[f.idx] = [t.id for t in cat]
            new = [t.id for t in cat if t.id not in res.detected]
            for pid in new:
                res.detected[pid] = f.idx
            if not new:
                res.duplicates.append(f.idx)
            continue
        if loc:
            res.near_miss[f.idx] = [t.id for t in loc]
            continue
        dec = [d for d in decoys if d.file == f.path and _distance(f, d.lines) <= DECOY_WINDOW
               and d.lure and category_matches(d.lure, f.text)]
        if dec:
            res.decoy_fp[f.idx] = min(dec, key=lambda d: _distance(f, d.lines)).id
        else:
            res.unplanted.append(f.idx)
    return res


def summarise(findings: list[Finding], planted: list[Target], decoys: list[Target], res: MatchResult) -> dict:
    n = len(findings)
    tp_findings = len(res.assignments)
    by_cat: dict[str, dict] = {}
    by_sev: dict[str, dict] = {s: {"planted": 0, "detected": 0} for s in SEVERITIES}
    for t in planted:
        c = by_cat.setdefault(t.category, {"planted": 0, "detected": 0, "ids_missed": []})
        c["planted"] += 1
        by_sev[t.severity]["planted"] += 1
        if t.id in res.detected:
            c["detected"] += 1
            by_sev[t.severity]["detected"] += 1
        else:
            c["ids_missed"].append(t.id)
    detected = len(res.detected)
    return {
        "findings_total": n,
        "planted_total": len(planted),
        "planted_detected": detected,
        "recall": round(detected / len(planted), 4) if planted else 0.0,
        "true_positive_findings": tp_findings,
        "duplicate_findings": len(res.duplicates),
        "near_miss_findings": len(res.near_miss),
        "decoy_false_positives": len(res.decoy_fp),
        "decoys_flagged": sorted(set(res.decoy_fp.values())),
        "decoys_total": len(decoys),
        "unplanted_findings": len(res.unplanted),
        "precision_strict": round(tp_findings / n, 4) if n else 0.0,
        "precision_unique": round(detected / (detected + n - tp_findings), 4) if n else 0.0,
        "by_category": by_cat,
        "by_severity": by_sev,
        "missed_ids": [t.id for t in planted if t.id not in res.detected],
    }


def score_scan(scan_path: Path, manifest_path: Path, fixture_root: Path) -> dict:
    scan = json.loads(Path(scan_path).read_text())
    manifest = json.loads(Path(manifest_path).read_text())
    planted, decoys = resolve_targets(manifest, fixture_root)
    findings = load_findings(scan)
    res = match(findings, planted, decoys)
    summary = summarise(findings, planted, decoys, res)
    per_finding = []
    for f in findings:
        status = (
            "duplicate" if f.idx in res.duplicates else
            "true_positive" if f.idx in res.assignments else
            "near_miss" if f.idx in res.near_miss else
            "decoy_false_positive" if f.idx in res.decoy_fp else
            "unplanted"
        )
        per_finding.append({
            "idx": f.idx, "path": f.path, "start_line": f.start_line, "end_line": f.end_line,
            "status": status,
            "planted_ids": res.assignments.get(f.idx),
            "credited_ids": [p for p, i in res.detected.items() if i == f.idx] or None,
            "near_miss_ids": res.near_miss.get(f.idx),
            "decoy_id": res.decoy_fp.get(f.idx),
            "content": f.content,
        })
    return {"summary": summary, "findings": per_finding,
            "scan_summary": scan.get("summary"), "scan_status": scan.get("status"), "llm": scan.get("llm"),
            "rules": {"rules_version": RULES_VERSION, "line_window": LINE_WINDOW, "decoy_window": DECOY_WINDOW}}
