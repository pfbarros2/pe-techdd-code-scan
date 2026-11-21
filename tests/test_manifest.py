import json
import re

from conftest import ROOT
from techdd_scan.matching import CATEGORY_PATTERNS, resolve_targets

MANIFEST = json.loads((ROOT / "ground_truth" / "manifest.json").read_text())
FIXTURE = ROOT / "fixture" / "quillmoor-ledger"


def test_counts():
    assert len(MANIFEST["planted"]) == 30
    assert len(MANIFEST["decoys"]) == 15


def test_ids_unique_and_categories_known():
    ids = [e["id"] for e in MANIFEST["planted"] + MANIFEST["decoys"]]
    assert len(ids) == len(set(ids))
    for e in MANIFEST["planted"]:
        assert e["category"] in CATEGORY_PATTERNS
        assert e["severity"] in {"critical", "high", "medium", "low"}
    for d in MANIFEST["decoys"]:
        assert d["lure"] in CATEGORY_PATTERNS


def test_all_anchors_resolve():
    planted, decoys = resolve_targets(MANIFEST, FIXTURE)
    for t in planted + decoys:
        assert t.lines, t.id


def test_planted_and_decoy_lines_do_not_overlap():
    planted, decoys = resolve_targets(MANIFEST, FIXTURE)
    p = {(t.file, ln) for t in planted for ln in t.lines}
    d = {(t.file, ln) for t in decoys for ln in t.lines}
    assert not p & d


def test_fixture_has_no_real_looking_secrets_and_no_hints():
    forbidden = ["nv" + "api-", r"\bsk-[A-Za-z0-9]", r"AKIA[0-9A-Z]{8}", r"ghp_[A-Za-z0-9]", r"xox[bp]-"]
    hints = [r"PLANTED", r"ground[_ ]truth", r"\bP\d\d\b", r"\bD\d\d\b", r"vulnerab"]
    for f in FIXTURE.rglob("*"):
        if f.is_file():
            text = f.read_text()
            for pat in forbidden + hints:
                assert not re.search(pat, text, re.I if pat in hints else 0), (f, pat)


def test_secret_values_are_marked_fake():
    planted, _ = resolve_targets(MANIFEST, FIXTURE)
    for t in planted:
        if t.category == "hardcoded_secret":
            lines = (FIXTURE / t.file).read_text().splitlines()
            assert all("FAKE" in lines[ln - 1] for ln in t.lines), t.id
