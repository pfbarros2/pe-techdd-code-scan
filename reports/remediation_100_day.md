# Sample 100-day remediation plan - LedgerLoop (FICTIONAL)

Derived from the scanner's own findings in `results/run1-nemotron-ultra/score.json` (one line per category). Phase is set by
the category rubric (critical/high -> days 0-30, medium -> 31-60, low -> 61-100). "Ground-truth check" shows how the
underlying findings scored against the planted manifest, so you can see which lines a real engagement would still
need to triage. 29 general code-quality findings are left to the engineering backlog.

| Phase | Category | Rubric severity | Action | Locations (file:line) | Ground-truth check |
|---|---|---|---|---|---|
| Days 0-30 | auth_bypass | critical | Remove debug admin header; enforce tenant scoping on every object lookup; reject unsigned JWTs. | ledgerloop/auth.py:30<br>ledgerloop/auth.py:48<br>ledgerloop/routes/exports.py:21<br>ledgerloop/routes/invoices.py:28<br>ledgerloop/routes/payments.py:18 | near_miss: 1, true_positive: 4 |
| Days 0-30 | sql_injection | critical | Replace string-built SQL with parameterised queries; allowlist ORDER BY columns. | ledgerloop/db.py:44<br>ledgerloop/db.py:57<br>ledgerloop/routes/invoices.py:20<br>ledgerloop/routes/payments.py:11 | duplicate: 1, true_positive: 2, unplanted: 1 |
| Days 0-30 | command_injection | critical | Remove shell=True; pass argument lists and validate names against an allowlist. | ledgerloop/routes/exports.py:21<br>ledgerloop/routes/exports.py:30 | decoy_false_positive: 1, true_positive: 1 |
| Days 0-30 | insecure_deserialization | critical | Replace pickle with signed JSON; use yaml.safe_load. | ledgerloop/services/imports.py:25<br>ledgerloop/services/imports.py:37 | near_miss: 1, true_positive: 2 |
| Days 0-30 | weak_crypto | high | Use a password KDF (argon2/bcrypt), the secrets module for tokens, and AES-GCM with a dedicated key. | ledgerloop/routes/auth_routes.py:26<br>ledgerloop/services/reports.py:36<br>ledgerloop/utils/crypto.py:16<br>ledgerloop/utils/crypto.py:25<br>ledgerloop/utils/crypto.py:38<br>ledgerloop/utils/crypto.py:53 | decoy_false_positive: 2, true_positive: 3, unplanted: 1 |
| Days 0-30 | hardcoded_secret | high | Move secrets to a secret manager; remove defaults; rotate anything that was ever committed. | ledgerloop/config.py:14<br>web/static/js/dashboard.js:18<br>web/static/js/dashboard.js:4 | near_miss: 1, true_positive: 1, unplanted: 1 |
| Days 0-30 | ssrf | high | Restrict outbound webhook targets (https, public IPs only, pinned resolution, no redirects). | ledgerloop/app.py:38<br>ledgerloop/services/webhooks.py:12<br>ledgerloop/services/webhooks.py:19 | duplicate: 2, true_positive: 1 |
| Days 0-30 | xss | high | Escape output server-side; use textContent / DOM APIs instead of innerHTML. | ledgerloop/routes/invoices.py:57<br>web/static/js/dashboard.js:23<br>web/templates/dashboard.html:14 | true_positive: 2, unplanted: 1 |
| Days 0-30 | code_injection | high | Remove eval(); parse server data with JSON.parse. | web/static/js/api.js:29 | true_positive: 1 |
| Days 0-30 | path_traversal | high | Resolve and confine file paths to the export directory (or use opaque file IDs). | ledgerloop/routes/exports.py:13 | true_positive: 1 |
| Days 31-60 | input_validation | medium | Validate amounts and bounds server-side (non-negative, <= amount paid). | ledgerloop/routes/payments.py:28<br>ledgerloop/routes/payments.py:39<br>ledgerloop/services/imports.py:13<br>ledgerloop/services/payments.py:26<br>ledgerloop/services/reports.py:18<br>ledgerloop/services/webhooks.py:33<br>web/static/js/dashboard.js:23 | duplicate: 1, near_miss: 2, unplanted: 4 |
| Days 31-60 | race_condition | medium | Make balance updates atomic (single UPDATE with condition / row lock); guard shared counters. | ledgerloop/routes/exports.py:30<br>ledgerloop/services/payments.py:0<br>ledgerloop/services/payments.py:15<br>ledgerloop/services/reports.py:10<br>ledgerloop/workers/billing.py:15 | true_positive: 2, unplanted: 3 |
| Days 31-60 | sensitive_logging | medium | Stop logging passwords and card numbers; mask PAN; purge existing logs. | ledgerloop/auth.py:91<br>ledgerloop/routes/payments.py:39<br>ledgerloop/services/payments.py:42<br>ledgerloop/workers/billing.py:15 | duplicate: 1, near_miss: 1, true_positive: 2 |
| Days 31-60 | error_handling | medium | Fail closed on gateway errors; log and surface failures. | ledgerloop/config.py:24<br>ledgerloop/services/payments.py:56 | near_miss: 1, true_positive: 1 |
| Days 31-60 | open_redirect | medium | Validate redirect targets against an allowlist of hosts/paths. | ledgerloop/routes/auth_routes.py:44 | true_positive: 1 |
| Days 61-100 | null_handling | low | Handle missing records explicitly (404/validation) instead of crashing. | ledgerloop/services/reports.py:40<br>web/static/js/dashboard.js:28<br>web/templates/dashboard.html:13 | true_positive: 2, unplanted: 1 |
| Days 61-100 | timing_attack | low | Use constant-time comparison (hmac.compare_digest) for secrets. | ledgerloop/auth.py:78<br>ledgerloop/utils/crypto.py:47 | near_miss: 1, true_positive: 1 |

Programme actions alongside the fixes (author's recommendation, not tool output): rotate every secret that has been in
source control; add secret scanning and SAST to CI; require a second reviewer on auth, payments and export code; re-run
the scan at day 100 and compare.
