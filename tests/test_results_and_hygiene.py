import json
import os
import re
import subprocess

import pytest

from conftest import ROOT

SUMMARY = ROOT / "results" / "summary.json"
KEY_PREFIX = "nv" + "api-"  # built at runtime so this file never contains the literal
TEXT_SUFFIXES = {".md", ".py", ".sh", ".json", ".txt", ".html", ".js", ".log", ".toml", ".cfg", ".yml", ".yaml", ""}


def repo_text_files():
    skip = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}
    for p in ROOT.rglob("*"):
        if p.is_file() and not (set(p.relative_to(ROOT).parts) & skip) and p.suffix in TEXT_SUFFIXES:
            yield p


def test_no_api_key_material_in_repo():
    key_file = os.path.expanduser("~/.secrets/nvidia_api_key")
    key = open(key_file).read().strip() if os.path.exists(key_file) else None
    for p in repo_text_files():
        text = p.read_text(errors="replace")
        assert KEY_PREFIX not in text, p  # never print the matched text
        if key:
            assert key not in text, p


@pytest.mark.skipif(not SUMMARY.exists(), reason="no results yet")
def test_readme_block_matches_summary():
    s = json.loads(SUMMARY.read_text())
    readme = (ROOT / "README.md").read_text()
    block = re.search(r"<!-- RESULTS:START.*?<!-- RESULTS:END -->", readme, re.S).group(0)
    prim = next(r for r in s["runs"] if r["run"] == "run1-nemotron-ultra")
    assert f"**{prim['detected']}/{prim['planted']} planted issues detected" in block
    assert f"{s['totals']['llm_calls']} LLM calls" in block
    assert f"{s['totals']['input_tokens']:,} input" in block
    for r in s["runs"]:
        assert f"| {r['run']} |" in block


@pytest.mark.skipif(not SUMMARY.exists(), reason="no results yet")
def test_every_run_has_real_output_and_metadata():
    s = json.loads(SUMMARY.read_text())
    for r in s["runs"]:
        d = ROOT / "results" / r["run"]
        scan = json.loads((d / "scan.json").read_text())
        meta = json.loads((d / "run_meta.json").read_text())
        assert scan["llm"]["model"] == meta["model"]
        assert scan["summary"]["total_tokens"] == r["total_tokens"]
        assert len(scan["comments"]) == r["findings"]


def test_linkedin_draft_rules():
    text = (ROOT / "notes" / "linkedin-draft.md").read_text()
    assert "DRAFT – not approved" in text
    body = text.split("\n\n", 2)[-1]
    assert len(body.split()) < 150
    assert not re.search(r"certified|proven|deloitte", text, re.I)


def test_no_deloitte_branding_in_deliverables():
    for p in list((ROOT / "reports").glob("*")) + [ROOT / "README.md"] + list((ROOT / "fixture").rglob("*")):
        if p.is_file() and p.suffix != ".png":
            assert not re.search(r"deloitte", p.read_text(), re.I), p


def test_git_history_has_no_key_prefix():
    if not (ROOT / ".git").exists():
        pytest.skip("not a git checkout")
    out = subprocess.run(["git", "log", "--all", "-p", "-S" + KEY_PREFIX, "--format=%H"], cwd=ROOT,
                         capture_output=True, text=True)
    assert out.stdout.strip() == ""
