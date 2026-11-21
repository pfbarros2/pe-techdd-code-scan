#!/usr/bin/env python3
"""Derive LLM call counts from an OCR session log (no prompts/keys copied).

Usage: session_stats.py <run_dir> [ocr_home]
Reads session_id from <run_dir>/scan.json, finds the matching
~/.opencodereview/sessions/**/<session_id>.jsonl and writes
<run_dir>/session_stats.json with event counts and per-file request counts.
"""
import collections
import json
import pathlib
import sys

run_dir = pathlib.Path(sys.argv[1])
home = pathlib.Path(sys.argv[2] if len(sys.argv) > 2 else "/tmp/pe-techdd-ocr-home")
scan = json.loads((run_dir / "scan.json").read_text())
sid = scan.get("session_id")
matches = list((home / ".opencodereview" / "sessions").rglob(f"{sid}.jsonl")) if sid else []
if not matches:
    sys.exit(f"session log not found for {sid}")
events = collections.Counter()
per_file = collections.Counter()
usage = collections.Counter()
for line in matches[0].read_text().splitlines():
    d = json.loads(line)
    t = d.get("type")
    events[t] += 1
    if t == "llm_request":
        per_file[d.get("filePath") or "(run-level)"] += 1
    if t == "llm_response":
        u = d.get("usage") or {}
        for k, v in u.items():
            if isinstance(v, (int, float)):
                usage[k] += v
out = {"session_id": sid, "llm_requests": events.get("llm_request", 0),
       "llm_responses": events.get("llm_response", 0), "tool_calls": events.get("tool_call", 0),
       "event_counts": dict(events), "llm_requests_per_file": dict(sorted(per_file.items())),
       "usage_from_session_log": dict(usage)}
(run_dir / "session_stats.json").write_text(json.dumps(out, indent=2))
print(json.dumps({k: out[k] for k in ("llm_requests", "llm_responses", "tool_calls")}))
