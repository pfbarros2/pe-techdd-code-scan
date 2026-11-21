#!/usr/bin/env bash
# Run `ocr scan` (whole-codebase mode) against the isolated fixture copy.
#
# Usage: scripts/run_scan.sh <run_label> [model]
#
# Environment:
#   OCR_BIN          path to the ocr binary (default: ocr on PATH)
#   OCR_BASE_URL     OpenAI-compatible base URL (default: NVIDIA API catalog)
#   OCR_API_KEY_FILE file holding the API key (default: ~/.secrets/nvidia_api_key)
#   OCR_PROVIDER     provider alias written to an ISOLATED ocr config (default: demo-endpoint)
#
# The key is read into an environment variable for this process only. OCR is
# configured with api_key_cmd="printenv DEMO_LLM_API_KEY", so the key is never
# written to config.json, the command line, or any output file.
set -euo pipefail
set +x
LABEL="${1:?run label required}"
MODEL="${2:-nvidia/nemotron-3-ultra-550b-a55b}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OCR_BIN="${OCR_BIN:-ocr}"
BASE_URL="${OCR_BASE_URL:-https://integrate.api.nvidia.com/v1}"
KEY_FILE="${OCR_API_KEY_FILE:-$HOME/.secrets/nvidia_api_key}"
PROVIDER="${OCR_PROVIDER:-demo-endpoint}"
OUT="$REPO_ROOT/results/$LABEL"
mkdir -p "$OUT"

WORK="$("$REPO_ROOT/scripts/prepare_workspace.sh")"

# Isolated OCR home so we never touch a user's real ~/.opencodereview
export OCR_HOME_DIR="${OCR_HOME_DIR:-/tmp/pe-techdd-ocr-home}"
mkdir -p "$OCR_HOME_DIR"
export HOME="$OCR_HOME_DIR"

DEMO_LLM_API_KEY="$(tr -d '\r\n' < "$KEY_FILE")"
export DEMO_LLM_API_KEY

"$OCR_BIN" config set provider "$PROVIDER" >/dev/null
"$OCR_BIN" config set "custom_providers.$PROVIDER.url" "$BASE_URL" >/dev/null
"$OCR_BIN" config set "custom_providers.$PROVIDER.protocol" openai >/dev/null
"$OCR_BIN" config set "custom_providers.$PROVIDER.model" "$MODEL" >/dev/null
"$OCR_BIN" config set "custom_providers.$PROVIDER.api_key_cmd" "printenv DEMO_LLM_API_KEY" >/dev/null
"$OCR_BIN" config set "custom_providers.$PROVIDER.extra_body" '{"temperature":0}' >/dev/null
"$OCR_BIN" config set "custom_providers.$PROVIDER.timeout_sec" 600 >/dev/null

START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
set +e
"$OCR_BIN" scan --repo "$WORK" --format json --output "$OUT/scan.json" \
  --concurrency "${OCR_CONCURRENCY:-4}" --timeout "${OCR_TIMEOUT_MIN:-60}" --color never \
  2> "$OUT/scan.stderr.raw.log"
RC=$?
set -e
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)

# Scrub: remove any occurrence of the key from logs (defence in depth), then drop raw
python3 - "$OUT" <<'PY'
import os, sys, pathlib
out = pathlib.Path(sys.argv[1]); key = os.environ["DEMO_LLM_API_KEY"]
raw = out / "scan.stderr.raw.log"
text = raw.read_text(errors="replace") if raw.exists() else ""
(out / "scan.stderr.log").write_text(text.replace(key, "[REDACTED]"))
raw.unlink(missing_ok=True)
for p in out.glob("*"):
    if p.is_file() and key in p.read_text(errors="replace"):
        p.write_text(p.read_text(errors="replace").replace(key, "[REDACTED]"))
        print("WARNING: key scrubbed from", p.name)
PY
unset DEMO_LLM_API_KEY

OCR_VERSION="$("$OCR_BIN" --version | head -1)"
python3 - "$OUT" "$LABEL" "$MODEL" "$BASE_URL" "$START" "$END" "$RC" "$OCR_VERSION" <<'PY'
import json, sys, pathlib
out, label, model, url, start, end, rc, ver = sys.argv[1:]
json.dump({"label": label, "model": model, "base_url": url, "temperature": 0,
           "started_utc": start, "finished_utc": end, "exit_code": int(rc),
           "ocr_version": ver, "command": "ocr scan --repo <isolated fixture copy> --format json --concurrency 4"},
          open(pathlib.Path(out) / "run_meta.json", "w"), indent=2)
PY
python3 "$REPO_ROOT/scripts/session_stats.py" "$OUT" "$OCR_HOME_DIR" || echo "session stats unavailable"
echo "run $LABEL finished rc=$RC"
