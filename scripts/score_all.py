#!/usr/bin/env python3
"""Score every results/<run>/scan.json against the ground truth.

Writes results/<run>/score.json and results/summary.json (per-run metrics,
cross-run consistency, total LLM calls/tokens). All numbers in README and
reports/ are taken from these files.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from techdd_scan.matching import score_scan  # noqa: E402

MANIFEST = ROOT / "ground_truth" / "manifest.json"
FIXTURE = ROOT / "fixture" / "quillmoor-ledger"


def main():
    runs = []
    for run_dir in sorted((ROOT / "results").glob("run*/")):
        scan = run_dir / "scan.json"
        if not scan.exists():
            continue
        scored = score_scan(scan, MANIFEST, FIXTURE)
        meta = json.loads((run_dir / "run_meta.json").read_text()) if (run_dir / "run_meta.json").exists() else {}
        stats = json.loads((run_dir / "session_stats.json").read_text()) if (run_dir / "session_stats.json").exists() else {}
        scored["run_meta"] = meta
        scored["llm_calls"] = stats.get("llm_requests")
        (run_dir / "score.json").write_text(json.dumps(scored, indent=2))
        s = scored["summary"]
        runs.append({
            "run": run_dir.name, "model": meta.get("model"), "exit_code": meta.get("exit_code"),
            "scan_status": scored["scan_status"],
            "findings": s["findings_total"], "detected": s["planted_detected"], "planted": s["planted_total"],
            "recall": s["recall"], "precision_strict": s["precision_strict"], "precision_unique": s["precision_unique"],
            "true_positive_findings": s["true_positive_findings"], "duplicates": s["duplicate_findings"],
            "near_miss": s["near_miss_findings"], "decoy_fp": s["decoy_false_positives"],
            "decoys_flagged": s["decoys_flagged"], "unplanted": s["unplanted_findings"],
            "missed_ids": s["missed_ids"],
            "llm_calls": stats.get("llm_requests"),
            "input_tokens": (scored["scan_summary"] or {}).get("input_tokens"),
            "output_tokens": (scored["scan_summary"] or {}).get("output_tokens"),
            "total_tokens": (scored["scan_summary"] or {}).get("total_tokens"),
            "elapsed": (scored["scan_summary"] or {}).get("elapsed"),
        })
    if not runs:
        sys.exit("no runs found")
    det = {}
    for r in runs:
        sc = json.loads((ROOT / "results" / r["run"] / "score.json").read_text())
        det[r["run"]] = {pid for f in sc["findings"] for pid in (f["credited_ids"] or [])}
    all_ids = [p["id"] for p in json.loads(MANIFEST.read_text())["planted"]]
    consistency = {pid: [run for run in det if pid in det[run]] for pid in all_ids}
    summary = {
        "runs": runs,
        "planted_detected_in_every_run": sorted(p for p, rs in consistency.items() if len(rs) == len(runs)),
        "planted_detected_in_any_run": sorted(p for p, rs in consistency.items() if rs),
        "planted_never_detected": sorted(p for p, rs in consistency.items() if not rs),
        "per_issue_runs": consistency,
        "totals": {
            "llm_calls": sum(r["llm_calls"] or 0 for r in runs),
            "input_tokens": sum(r["input_tokens"] or 0 for r in runs),
            "output_tokens": sum(r["output_tokens"] or 0 for r in runs),
            "total_tokens": sum(r["total_tokens"] or 0 for r in runs),
        },
    }
    (ROOT / "results" / "summary.json").write_text(json.dumps(summary, indent=2))
    for r in runs:
        print(f"{r['run']}: findings={r['findings']} detected={r['detected']}/{r['planted']} "
              f"precision_strict={r['precision_strict']} decoy_fp={r['decoy_fp']} tokens={r['total_tokens']} calls={r['llm_calls']}")


if __name__ == "__main__":
    main()
